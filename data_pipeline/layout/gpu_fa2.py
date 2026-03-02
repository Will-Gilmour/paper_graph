"""
GPU-accelerated ForceAtlas2 layout using cuGraph.

Extracted from graph_builder6.py/graph_builder7.py.
"""

from __future__ import annotations
import time
from typing import Dict, Tuple, Optional, TYPE_CHECKING
import numpy as np
import networkx as nx

from data_pipeline.layout.base import LayoutEngine
from data_pipeline.utils.logging import get_logger
from data_pipeline.utils.errors import LayoutError

# Try to import GPU libraries
try:
    import cugraph
    import cudf
    import cupy as cp
    GPU_AVAILABLE = True
except (ImportError, FileNotFoundError, Exception) as e:
    # cuGraph can fail for many reasons: missing, CUDA mismatch, library errors
    GPU_AVAILABLE = False
    if TYPE_CHECKING:
        import cudf  # Only for type checking

logger = get_logger("layout.gpu_fa2")


class GPUForceAtlas2(LayoutEngine):
    """
    GPU-accelerated ForceAtlas2 layout using RAPIDS cuGraph.
    
    Much faster than CPU for large graphs (>10k nodes).
    """
    
    def __init__(
        self,
        max_iter: int = 2000,
        barnes_hut_theta: float = 0.5,
        scaling_ratio: float = 1000.0,
        gravity: float = 1.5,
        edge_weight_influence: float = 1.0,
        jitter_tolerance: float = 0.09,
        chunk_size: int = 1000,
    ):
        """
        Initialize GPU ForceAtlas2 engine.
        
        Args:
            max_iter: Maximum iterations
            barnes_hut_theta: Barnes-Hut approximation parameter
            scaling_ratio: Layout scale
            gravity: Gravity strength
            edge_weight_influence: Edge weight influence
            jitter_tolerance: Convergence tolerance
            chunk_size: Iterations per chunk (for progress)
        """
        self.max_iter = max_iter
        self.barnes_hut_theta = barnes_hut_theta
        self.scaling_ratio = scaling_ratio
        self.gravity = gravity
        self.edge_weight_influence = edge_weight_influence
        self.jitter_tolerance = jitter_tolerance
        self.chunk_size = chunk_size
    
    def is_available(self) -> bool:
        """Check if GPU is available."""
        return GPU_AVAILABLE
    
    def compute_layout(
        self,
        graph: nx.DiGraph,
        seed_positions: Optional[Dict[str, Tuple[float, float]]] = None,
    ) -> Dict[str, Tuple[float, float]]:
        """
        Compute layout using GPU ForceAtlas2.
        
        Args:
            graph: Directed graph
            seed_positions: Optional seed positions
        
        Returns:
            Node positions {node_id: (x, y)}
        
        Raises:
            LayoutError: If GPU not available or computation fails
        """
        if not self.is_available():
            raise LayoutError("GPU libraries (cuGraph/cuDF/cuPy) not available")
        
        logger.info(f"Computing GPU ForceAtlas2 layout ({graph.number_of_nodes()} nodes)")
        
        # Remove isolated nodes temporarily
        isolated_nodes = [n for n in graph.nodes() if graph.degree(n) == 0]
        if isolated_nodes:
            graph = graph.copy()
            graph.remove_nodes_from(isolated_nodes)
            logger.info(f"Removed {len(isolated_nodes)} isolated nodes temporarily")
        
        # Check if we have any edges left after removing isolated nodes
        if graph.number_of_edges() == 0:
            logger.warning("No edges in graph after removing isolated nodes - using simple layout")
            positions = {}
            
            # Get original graph nodes (including isolated)
            orig_graph = nx.Graph()
            orig_graph.add_nodes_from(isolated_nodes if isolated_nodes else graph.nodes())
            
            # Place nodes in a circle or use seed positions
            if seed_positions:
                for node in orig_graph.nodes():
                    if node in seed_positions:
                        positions[node] = seed_positions[node]
                    else:
                        # Place near centroid
                        existing = [seed_positions[d] for d in seed_positions]
                        if existing:
                            existing_arr = np.array(existing, dtype=np.float32)
                            cx, cy = existing_arr.mean(axis=0)
                            jitter = 10.0
                        else:
                            cx, cy, jitter = 0.0, 0.0, 10.0
                        positions[node] = (
                            float(cx + np.random.uniform(-jitter, jitter)),
                            float(cy + np.random.uniform(-jitter, jitter))
                        )
            else:
                # Use circular layout
                nodes = list(orig_graph.nodes())
                for i, node in enumerate(nodes):
                    if len(nodes) == 1:
                        positions[node] = (0.0, 0.0)
                    else:
                        angle = 2 * np.pi * i / len(nodes)
                        radius = 100.0
                        positions[node] = (
                            float(radius * np.cos(angle)),
                            float(radius * np.sin(angle))
                        )
            
            logger.info(f"Placed {len(positions)} nodes without ForceAtlas2")
            return positions
        
        # Create node index mapping
        node_list = list(graph.nodes())
        node_idx = {doi: i for i, doi in enumerate(node_list)}
        
        # Build edge list with weights
        edges_src = []
        edges_dst = []
        edges_weight = []
        
        # Convert to undirected for layout
        undirected = graph.to_undirected()
        
        for u, v in undirected.edges():
            ui = node_idx[u]
            vi = node_idx[v]
            
            # Weight by shared authors
            au = set(graph.nodes[u].get("authors", []))
            av = set(graph.nodes[v].get("authors", []))
            weight = 2.0 if (au and av and (au & av)) else 1.0
            
            edges_src.append(ui)
            edges_dst.append(vi)
            edges_weight.append(weight)
        
        # Create cuDF edge DataFrame
        edge_df = cudf.DataFrame({
            "source": cp.asarray(edges_src, dtype=cp.int32),
            "destination": cp.asarray(edges_dst, dtype=cp.int32),
            "weight": cp.asarray(edges_weight, dtype=cp.float32),
        })
        
        # Create cuGraph
        cg = cugraph.Graph()
        cg.from_cudf_edgelist(
            edge_df,
            source="source",
            destination="destination",
            edge_attr="weight"
        )
        
        # Prepare seed positions (if provided)
        pos_df = self._prepare_seed_positions(node_list, node_idx, seed_positions)
        
        # Run ForceAtlas2 in chunks (returns integer-indexed positions)
        int_positions = self._run_fa2_chunked(cg, pos_df, len(node_list))
        
        # Convert integer indices back to DOI keys
        positions = {node_list[idx]: pos for idx, pos in int_positions.items()}
        
        # Re-add isolated nodes around centroid
        if isolated_nodes and seed_positions:
            positions = self._place_isolated_nodes(positions, isolated_nodes, seed_positions)
        
        logger.info("GPU ForceAtlas2 layout complete")
        return positions
    
    def _prepare_seed_positions(
        self,
        node_list: list,
        node_idx: dict,
        seed_positions: Optional[dict]
    ) -> Optional["cudf.DataFrame"]:
        """Prepare seed positions for GPU."""
        if not seed_positions:
            return None
        
        N = len(node_list)
        pos_host = np.zeros((N, 2), dtype=np.float32)
        
        # Calculate centroid and span from existing positions
        existing = [seed_positions[d] for d in seed_positions if d in node_idx]
        if existing:
            existing_arr = np.array(existing, dtype=np.float32)
            cx, cy = existing_arr.mean(axis=0)
            span = np.ptp(existing_arr, axis=0).max()
            jitter = (span * 0.02) if span > 0 else 0.1
        else:
            cx, cy, jitter = 0.0, 0.0, 0.1
        
        # Fill positions
        for doi, idx in node_idx.items():
            if doi in seed_positions:
                x0, y0 = seed_positions[doi]
                pos_host[idx, 0] = x0
                pos_host[idx, 1] = y0
            else:
                # Place new nodes near centroid
                pos_host[idx, 0] = cx + np.random.uniform(-jitter, jitter)
                pos_host[idx, 1] = cy + np.random.uniform(-jitter, jitter)
        
        # Convert to cuDF DataFrame
        return cudf.DataFrame({
            "vertex": cp.arange(N, dtype=cp.int32),
            "x": cp.asarray(pos_host[:, 0]),
            "y": cp.asarray(pos_host[:, 1]),
        })
    
    def _run_fa2_chunked(
        self,
        cg,  # cugraph.Graph
        pos_df: Optional["cudf.DataFrame"],
        num_nodes: int
    ) -> Dict[str, Tuple[float, float]]:
        """Run ForceAtlas2 in chunks for progress tracking."""
        iterations_done = 0
        current_pos_df = pos_df
        prev_pos_df = None
        
        while iterations_done < self.max_iter:
            this_chunk = min(self.chunk_size, self.max_iter - iterations_done)
            t0 = time.perf_counter()
            
            new_pos_df = cugraph.force_atlas2(
                cg,
                max_iter=this_chunk,
                outbound_attraction_distribution=True,
                lin_log_mode=False,
                prevent_overlapping=False,
                edge_weight_influence=self.edge_weight_influence,
                jitter_tolerance=self.jitter_tolerance,
                barnes_hut_optimize=True,
                barnes_hut_theta=self.barnes_hut_theta,
                scaling_ratio=self.scaling_ratio,
                strong_gravity_mode=False,
                gravity=self.gravity,
                pos_list=current_pos_df,
                verbose=False,
            )
            
            elapsed = time.perf_counter() - t0
            iterations_done += this_chunk
            logger.info(f"GPU FA2: {iterations_done}/{self.max_iter} iterations ({elapsed:.2f}s)")
            
            # Check convergence
            if prev_pos_df is not None:
                dx = new_pos_df["x"].astype(cp.float32) - prev_pos_df["x"].astype(cp.float32)
                dy = new_pos_df["y"].astype(cp.float32) - prev_pos_df["y"].astype(cp.float32)
                disp = cp.sqrt(dx ** 2 + dy ** 2)
                max_disp = float(disp.max().get())
                
                if max_disp < 1e-4:
                    logger.info(f"Converged early at iteration {iterations_done}")
                    break
            
            prev_pos_df = new_pos_df
            current_pos_df = new_pos_df
        
        # Extract positions from GPU
        vertices = current_pos_df["vertex"].values
        xs = current_pos_df["x"].values
        ys = current_pos_df["y"].values
        
        positions = {}
        node_list = list(range(num_nodes))
        for i in range(len(vertices)):
            idx = int(vertices[i].item())
            positions[idx] = (float(xs[i].item()), float(ys[i].item()))
        
        return positions
    
    def _place_isolated_nodes(
        self,
        positions: dict,
        isolated_nodes: list,
        seed_positions: dict
    ) -> dict:
        """Place isolated nodes around the layout centroid."""
        # Calculate centroid
        pts = np.array(list(positions.values()), dtype=np.float64)
        if pts.size:
            cx, cy = pts.mean(axis=0)
            span = np.ptp(pts, axis=0).max()
            jitter = (span * 0.05) if span > 0 else 0.1
        else:
            cx, cy, jitter = 0.0, 0.0, 0.1
        
        # Place isolated nodes
        result = dict(positions)
        for node in isolated_nodes:
            if node in seed_positions:
                result[node] = seed_positions[node]
            else:
                result[node] = (
                    cx + np.random.uniform(-jitter, jitter),
                    cy + np.random.uniform(-jitter, jitter),
                )
        
        return result


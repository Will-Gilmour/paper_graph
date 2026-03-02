"""
CPU ForceAtlas2 layout fallback.

Uses the fa2 Python library (python-louvain compatible).
"""

from typing import Dict, Tuple, Optional
import numpy as np
import networkx as nx

from data_pipeline.layout.base import LayoutEngine
from data_pipeline.utils.logging import get_logger

# fa2 has Python 3.10 compatibility issues
# Using NetworkX spring_layout as fallback instead
FA2_AVAILABLE = False

logger = get_logger("layout.cpu_fa2")


class CPUForceAtlas2(LayoutEngine):
    """
    CPU ForceAtlas2 layout fallback.
    
    Slower than GPU but works without CUDA.
    """
    
    def __init__(
        self,
        iterations: int = 2000,
        barnes_hut_theta: float = 0.5,
        scaling_ratio: float = 1000.0,
        gravity: float = 1.5,
        edge_weight_influence: float = 1.0,
        jitter_tolerance: float = 0.09,
    ):
        self.iterations = iterations
        self.barnes_hut_theta = barnes_hut_theta
        self.scaling_ratio = scaling_ratio
        self.gravity = gravity
        self.edge_weight_influence = edge_weight_influence
        self.jitter_tolerance = jitter_tolerance
    
    def is_available(self) -> bool:
        return FA2_AVAILABLE
    
    def compute_layout(
        self,
        graph: nx.DiGraph,
        seed_positions: Optional[Dict[str, Tuple[float, float]]] = None,
    ) -> Dict[str, Tuple[float, float]]:
        """Compute layout using NetworkX spring layout (fa2 has Python 3.10 issues)."""
        logger.warning("Using NetworkX spring_layout (fa2 incompatible with Python 3.10)")
        return nx.spring_layout(
            graph,
            pos=seed_positions,
            iterations=self.iterations,
            k=None,  # Auto-calculate optimal distance
            scale=self.scaling_ratio
        )
        
        logger.info(f"Computing CPU ForceAtlas2 layout ({graph.number_of_nodes()} nodes)")
        
        # Prepare seed positions
        if seed_positions:
            # Fill missing nodes
            seed_map = dict(seed_positions)
            missing = [n for n in graph if n not in seed_map]
            if missing:
                xy = np.array(list(seed_map.values()))
                cx, cy = xy.mean(axis=0) if xy.size else (0.0, 0.0)
                span = np.ptp(xy, axis=0).max() if xy.size else 1.0
                jitter = span * 0.05
                for n in missing:
                    seed_map[n] = (
                        cx + np.random.uniform(-jitter, jitter),
                        cy + np.random.uniform(-jitter, jitter),
                    )
        else:
            seed_map = None
        
        # Run ForceAtlas2
        fa2 = ForceAtlas2(
            edgeWeightInfluence=self.edge_weight_influence,
            jitterTolerance=self.jitter_tolerance,
            barnesHutTheta=self.barnes_hut_theta,
            scalingRatio=self.scaling_ratio,
            gravity=self.gravity,
            barnesHutOptimize=True,
            outboundAttractionDistribution=False,
        )
        
        positions = fa2.forceatlas2_networkx_layout(
            graph,
            pos=seed_map,
            iterations=self.iterations
        )
        
        logger.info("CPU ForceAtlas2 layout complete")
        return positions


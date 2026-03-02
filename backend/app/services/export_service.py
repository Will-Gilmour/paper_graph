"""
Export service - Business logic for data export operations.

Handles NDJSON generation and paginated exports.
"""
import json
import collections
import os
from typing import Dict, Iterator, Optional, Set, List
from pathlib import Path

from backend.app.config.settings import settings, logger
from backend.app.database import queries
from backend.app.database.connection import get_db_connection
from backend.app.services.scoring_service import scoring_service


class ExportError(Exception):
    """Export-related errors."""
    pass


class ExportService:
    """Service for data export operations."""
    
    def __init__(self):
        """Initialize export service."""
        self.initial_meta: Dict[str, int] = {"nodes_total": 0, "edges_total": 0}
        self._ndjson_base_path = settings.initial_ndjson_path.parent  # Store directory
    
    def _get_active_run_id(self) -> int:
        """Get the ID of the currently active graph."""
        active_id = queries.get_active_run_id()
        return active_id if active_id is not None else 1
    
    def _get_ndjson_path(self, run_id: Optional[int] = None) -> Path:
        """
        Get path to NDJSON file for a specific run_id.
        
        Args:
            run_id: Graph run ID (uses active if None)
            
        Returns:
            Path to the NDJSON file
        """
        if run_id is None:
            run_id = self._get_active_run_id()
        
        return self._ndjson_base_path / f"initial_run_{run_id}.ndjson"
    
    def _load_seed_set(self) -> Set[str]:
        """
        Load seed DOI list from seed_list.json if available.
        
        Returns:
            Set of lowercase seed DOIs
        """
        try:
            seed_path = Path("seed_list.json")
            seeds = json.loads(seed_path.read_text())
            return {s.lower() for s in seeds}
        except FileNotFoundError:
            logger.warning("seed_list.json not found – proceeding without explicit seeds")
            return set()
    
    def build_initial_ndjson(
        self, 
        force_rebuild: bool = False, 
        run_id: Optional[int] = None,
        top_n: Optional[int] = None
    ) -> Dict[str, int]:
        """
        Build initial NDJSON file with highly-cited papers for a specific graph.
        
        Creates a subset of the graph with papers having > 25 citations
        or in the seed list, along with edges between them.
        If top_n is specified, returns top N papers by citation count instead.
        
        Args:
            force_rebuild: If True, rebuild even if file exists
            run_id: Graph run ID (uses active if None)
            top_n: If set, return top N papers by citation count (overrides citation threshold)
            
        Returns:
            Dictionary with nodes_total and edges_total counts
        """
        if run_id is None:
            run_id = self._get_active_run_id()
        
        # Include top_n in file path to cache different versions
        if top_n is not None:
            ndjson_path = self._ndjson_base_path / f"initial_run_{run_id}_top{top_n}.ndjson"
        else:
            ndjson_path = self._get_ndjson_path(run_id)
        
        # Check if already built
        if ndjson_path.exists() and not force_rebuild:
            # Re-compute counts by parsing existing file
            nodes = edges = 0
            try:
                with ndjson_path.open("r", encoding="utf-8") as fh:
                    for line in fh:
                        try:
                            obj_type = json.loads(line).get("type")
                            if obj_type == "node":
                                nodes += 1
                            elif obj_type == "edge":
                                edges += 1
                        except json.JSONDecodeError:
                            continue  # Skip malformed lines
                
                self.initial_meta = {"nodes_total": nodes, "edges_total": edges}
                logger.info(f"Re-using existing run_{run_id} NDJSON (nodes={nodes}, edges={edges}, top_n={top_n})")
                return self.initial_meta
            except Exception as e:
                logger.warning(f"Error reading existing NDJSON: {e}, rebuilding...")
        
        # Build new file
        seed_set = self._load_seed_set()
        
        with get_db_connection() as conn:
            # 1) Fetch nodes meeting criteria
            node_rows = queries.fetch_papers_for_ndjson(
                cited_threshold=25,
                seed_dois=list(seed_set) if seed_set else None,
                top_n=top_n
            )
            initial_dois = {r[0] for r in node_rows}
            logger.info(f"Found {len(initial_dois)} papers for run_{run_id} NDJSON")
            
            # 2) Stream edges and filter to those in initial set
            with conn.cursor(name="edge_stream") as edge_cur:
                edge_cur.itersize = 50_000
                edge_cur.execute("SELECT src, dst FROM edges WHERE run_id = %s", (run_id,))
                
                edges: List[tuple] = []
                for src, dst in edge_cur:
                    if src in initial_dois and dst in initial_dois:
                        edges.append((src, dst))
            
            logger.info(f"Found {len(edges)} edges between initial papers")
            
            # 3) Build NDJSON with nodes and their adjacent edges
            edges_by_node: Dict[str, List[int]] = collections.defaultdict(list)
            edge_objs: List[Dict] = []
            
            for idx, (u, v) in enumerate(edges):
                edge_objs.append({"type": "edge", "source": u, "target": v})
                edges_by_node[u].append(idx)
                edges_by_node[v].append(idx)
            
            # Write to temporary file first for atomic operation
            # Ensure parent directory exists (create if needed)
            ndjson_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = ndjson_path.parent / f"{ndjson_path.stem}.tmp"
            emitted_edge_idxs: Set[int] = set()
            nodes_count = 0
            edges_count = 0
            
            with temp_path.open("w", encoding="utf-8") as fh:
                for doi, title, cluster, cited, refs, x, y, fncr, year in node_rows:
                    # Compute importance score (time-decayed citations)
                    # Default decay factor of 1.0 - can be adjusted client-side
                    importance_score = scoring_service.time_decayed_citations(
                        citations=cited or 0,
                        year=year or 2000,  # Fallback year if missing
                        decay_factor=1.0
                    )
                    
                    # Write node
                    node_obj = {
                        "type": "node",
                        "id": doi,
                        "title": title or "Untitled",
                        "x": float(x) if x is not None else 0.0,
                        "y": float(y) if y is not None else 0.0,
                        "cluster": cluster,
                        "cited_count": cited,
                        "references_count": refs,
                        "fncr": fncr,
                        "year": year,
                        "importance_score": round(importance_score, 2),
                        "is_seed": doi.lower() in seed_set,
                    }
                    fh.write(json.dumps(node_obj, separators=(',', ':')) + "\n")
                    nodes_count += 1
                    
                    # Write edges touching this node (avoiding duplicates)
                    for eidx in edges_by_node[doi]:
                        if eidx not in emitted_edge_idxs:
                            fh.write(json.dumps(edge_objs[eidx], separators=(',', ':')) + "\n")
                            emitted_edge_idxs.add(eidx)
                            edges_count += 1
            
            # Atomically move to final location
            # Ensure target directory exists before rename
            ndjson_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Verify temp file exists before renaming
            if not temp_path.exists():
                raise ExportError(f"Temp file not created: {temp_path}")
            
            # Use os.replace for atomic cross-platform rename
            os.replace(str(temp_path), str(ndjson_path))
            
            self.initial_meta = {"nodes_total": nodes_count, "edges_total": edges_count}
            logger.info(f"Built run_{run_id} NDJSON (nodes={nodes_count}, edges={edges_count})")
            
            return self.initial_meta
    
    def get_initial_meta(self, run_id: Optional[int] = None, top_n: Optional[int] = None) -> Dict[str, int]:
        """
        Get metadata about the initial NDJSON file.
        
        Args:
            run_id: Graph run ID (uses active if None)
            top_n: If set, return metadata for top N version
        
        Returns:
            Dictionary with nodes_total and edges_total
        """
        if run_id is None:
            run_id = self._get_active_run_id()
        
        if top_n is not None:
            ndjson_path = self._ndjson_base_path / f"initial_run_{run_id}_top{top_n}.ndjson"
        else:
            ndjson_path = self._get_ndjson_path(run_id)
        
        # Ensure file is built
        if not ndjson_path.exists():
            self.build_initial_ndjson(run_id=run_id, top_n=top_n)
        
        return self.initial_meta
    
    def get_initial_ndjson_path(self, run_id: Optional[int] = None, top_n: Optional[int] = None) -> Path:
        """
        Get path to initial NDJSON file, building if needed.
        
        Args:
            run_id: Graph run ID (uses active if None)
            top_n: If set, return path for top N version
        
        Returns:
            Path to the NDJSON file
        """
        if run_id is None:
            run_id = self._get_active_run_id()
        
        if top_n is not None:
            ndjson_path = self._ndjson_base_path / f"initial_run_{run_id}_top{top_n}.ndjson"
        else:
            ndjson_path = self._get_ndjson_path(run_id)
        
        if not ndjson_path.exists():
            self.build_initial_ndjson(run_id=run_id, top_n=top_n)
        
        return ndjson_path
    
    def stream_full_ndjson(self, run_id: Optional[int] = None) -> Iterator[str]:
        """
        Stream full graph as NDJSON (all nodes, then all edges).
        
        Args:
            run_id: Graph run ID (uses active if None)
        
        Yields:
            NDJSON-formatted strings
        """
        if run_id is None:
            run_id = self._get_active_run_id()
        
        with get_db_connection() as conn:
            # Stream all nodes
            with conn.cursor(name="nodes_stream") as node_cur:
                node_cur.itersize = 50_000
                node_cur.execute("""
                    SELECT doi, x, y, cluster, cited_count, fncr
                    FROM papers
                    WHERE run_id = %s
                """, (run_id,))
                
                for doi, x, y, cluster, cited, fncr in node_cur:
                    node_obj = {
                        "type": "node",
                        "id": doi,
                        "x": float(x) if x is not None else 0.0,
                        "y": float(y) if y is not None else 0.0,
                        "cluster": cluster,
                        "cited_count": cited,
                        "fncr": fncr,
                    }
                    yield json.dumps(node_obj, separators=(',', ':')) + "\n"
            
            # Stream all edges
            with conn.cursor(name="edges_stream") as edge_cur:
                edge_cur.itersize = 50_000
                edge_cur.execute("SELECT src, dst FROM edges WHERE run_id = %s", (run_id,))
                
                for src, dst in edge_cur:
                    edge_obj = {"type": "edge", "source": src, "target": dst}
                    yield json.dumps(edge_obj, separators=(',', ':')) + "\n"
    
    def get_paginated_export(
        self,
        nodes_offset: int = 0,
        nodes_limit: int = 1000,
        edges_offset: int = 0,
        edges_limit: int = 1000,
        year_min: Optional[int] = None,
        year_max: Optional[int] = None,
        min_citations: Optional[int] = None
    ) -> Dict:
        """
        Get paginated export of nodes and edges with optional filters.
        
        Args:
            nodes_offset: Number of nodes to skip
            nodes_limit: Maximum nodes to return
            edges_offset: Number of edges to skip
            edges_limit: Maximum edges to return
            year_min: Optional minimum publication year
            year_max: Optional maximum publication year
            min_citations: Optional minimum citation count
            
        Returns:
            Dictionary with nodes, edges, and metadata
        """
        # Fetch paginated data with filters
        nodes = queries.fetch_nodes_paginated(
            nodes_offset, nodes_limit, year_min, year_max, min_citations
        )
        edges = queries.fetch_edges_paginated(edges_offset, edges_limit)
        
        # Get total counts (unfiltered for now - could be enhanced)
        nodes_total, edges_total = queries.get_total_counts()
        
        return {
            "nodes_total": len(nodes),  # Return actual filtered count
            "edges_total": edges_total,
            "nodes": nodes,
            "edges": edges,
            "meta": {
                "nodes_offset": nodes_offset,
                "nodes_limit": nodes_limit,
                "edges_offset": edges_offset,
                "edges_limit": edges_limit,
                "filters": {
                    "year_min": year_min,
                    "year_max": year_max,
                    "min_citations": min_citations,
                }
            }
        }


# Global service instance
export_service = ExportService()

# Build initial NDJSON on module load for the active graph
try:
    active_run_id = export_service._get_active_run_id()
    export_service.build_initial_ndjson(run_id=active_run_id)
except Exception as e:
    logger.error(f"Failed to build initial NDJSON on startup: {e}")


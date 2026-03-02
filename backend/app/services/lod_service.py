"""Level of Detail service for progressive node loading."""

from typing import Dict, List
from backend.app.database import queries
from backend.app.config.settings import logger


class LODService:
    """Service for level-of-detail node loading."""
    
    def get_nodes_in_viewport(
        self,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
        min_citations: int = 0,
        limit: int = 1000,
    ) -> Dict:
        """
        Fetch nodes within viewport bounds.
        
        Args:
            x_min, x_max, y_min, y_max: Viewport coordinates
            min_citations: Minimum citation count
            limit: Max nodes to return
            
        Returns:
            Dictionary with nodes and edges
        """
        # Fetch nodes in bounding box
        nodes = queries.fetch_nodes_in_bbox(
            x_min, x_max, y_min, y_max,
            min_citations, limit
        )
        
        # Get DOIs for edge filtering
        dois = {n["doi"] for n in nodes}
        
        # Fetch edges between these nodes
        edges = []
        if dois:
            edge_tuples = queries.fetch_edges_for_dois(list(dois))
            edges = [{"source": src, "target": dst} for src, dst in edge_tuples]
        
        logger.info(f"LOD: returned {len(nodes)} nodes, {len(edges)} edges for viewport ({x_min:.0f},{y_min:.0f})-({x_max:.0f},{y_max:.0f})")
        
        return {
            "nodes": nodes,
            "edges": edges,
            "meta": {
                "viewport": {"x_min": x_min, "x_max": x_max, "y_min": y_min, "y_max": y_max},
                "min_citations": min_citations,
                "count": len(nodes),
            }
        }


# Global service instance
lod_service = LODService()





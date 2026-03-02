"""
Cluster service - Business logic for cluster operations.

Handles fetching and formatting cluster data with proper label enrichment.
"""
from typing import List, Dict, Optional
import json
from pathlib import Path

from backend.app.config.settings import settings, logger
from backend.app.database import queries


class ClusterService:
    """Service for cluster-related operations."""
    
    def __init__(self):
        """Initialize cluster service and load labels."""
        self.parent_labels: Dict[str, str] = {}
        self.sub_labels: Dict[str, str] = {}
        self.cached_run_id: Optional[int] = None
        self._load_labels()
    
    def reload_labels(self):
        """Force reload of labels from database (e.g., after graph switch)."""
        self._load_labels()
    
    def _load_labels(self):
        """Load cluster labels from PostgreSQL database."""
        from backend.app.database.connection import get_db_connection
        
        # Load parent cluster labels from database
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Get active run_id
                    active_run_id = queries.get_active_run_id()
                    if active_run_id is None:
                        logger.warning("No active graph found, labels not loaded")
                        return
                    
                    # Check if we've already loaded this run
                    if self.cached_run_id == active_run_id:
                        logger.debug(f"Labels already cached for run_id={active_run_id}")
                        return
                    
                    self.cached_run_id = active_run_id
                    
                    # Load parent cluster labels
                    cur.execute("""
                        SELECT id, title 
                        FROM clusters 
                        WHERE run_id = %s AND title IS NOT NULL
                    """, (active_run_id,))
                    
                    self.parent_labels = {str(row[0]): row[1] for row in cur.fetchall()}
                    logger.info(f"Loaded {len(self.parent_labels)} parent cluster titles from database")
                    
                    # Load sub-cluster labels
                    cur.execute("""
                        SELECT cluster_id, sub_cluster_id, title 
                        FROM sub_clusters 
                        WHERE run_id = %s AND title IS NOT NULL
                    """, (active_run_id,))
                    
                    self.sub_labels = {f"{row[0]}:{row[1]}": row[2] for row in cur.fetchall()}
                    logger.info(f"Loaded {len(self.sub_labels)} sub-cluster titles from database")
        except Exception as e:
            logger.error(f"Error loading labels from database: {e}")
            # Set empty dicts on error
            self.parent_labels = {}
            self.sub_labels = {}
    
    def get_parent_labels(self) -> Dict[str, str]:
        """
        Get parent cluster labels.
        
        Returns:
            Dictionary mapping cluster IDs to labels
        """
        return self.parent_labels
    
    def get_sub_labels(self) -> Dict[str, str]:
        """
        Get sub-cluster labels.
        
        Returns:
            Dictionary mapping cluster:sub IDs to labels
        """
        return self.sub_labels
    
    def get_all_clusters(self) -> List[Dict]:
        """
        Get all clusters with labels and top sub-clusters.
        
        Returns:
            List of cluster dictionaries with enriched metadata
            
        Raises:
            ValueError: If no clusters found in database
        """
        # Fetch raw cluster data from database
        clusters_dict = queries.fetch_all_clusters()
        
        if not clusters_dict:
            raise ValueError("No clusters in database")
        
        # Format and enrich with labels
        formatted: List[Dict] = []
        for cid, meta in clusters_dict.items():
            # Get title with graceful fallback, treating placeholder as missing
            db_title = meta.get("title")
            if not db_title or db_title == "NO VALID TITLE":
                title = self.parent_labels.get(str(cid), f"Cluster {cid}")
            else:
                title = db_title
            
            # Sort sub-clusters by size and format with labels
            subs = meta.pop("_subs", [])
            subs.sort(key=lambda t: -t[1])  # Sort by size descending
            top_sub = [
                {
                    "label": self.sub_labels.get(f"{cid}:{sid}", f"Sub {sid}"), 
                    "size": n
                }
                for sid, n in subs[:10]  # Top 10 sub-clusters
            ]
            
            # Combine everything
            formatted.append({**meta, "title": title, "top_sub": top_sub})
        
        return formatted
    
    def get_cluster_detail(self, cluster_id: int) -> Optional[Dict]:
        """
        Get detailed information about a specific cluster.
        
        Args:
            cluster_id: The cluster ID to fetch
            
        Returns:
            Dictionary with cluster nodes and edges, or None if not found
        """
        # Fetch nodes
        nodes = queries.fetch_cluster_nodes(cluster_id)
        
        if not nodes:
            return None
        
        # Fetch edges
        edges = queries.fetch_cluster_edges(cluster_id)
        
        # Get cluster label
        label = self.parent_labels.get(str(cluster_id), f"Cluster {cluster_id}")
        
        return {
            "id": cluster_id,
            "label": label,
            "nodes": nodes,
            "edges": edges
        }


# Global service instance
cluster_service = ClusterService()


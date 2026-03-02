"""
Louvain community detection for clustering papers.

Extracted from graph_builder6.py.
"""

from typing import Dict
import networkx as nx

from data_pipeline.utils.logging import get_logger
from data_pipeline.utils.errors import ClusteringError

try:
    import community as community_louvain
    LOUVAIN_AVAILABLE = True
except ImportError:
    LOUVAIN_AVAILABLE = False

logger = get_logger("clustering.louvain")


class LouvainClusterer:
    """
    Louvain community detection for graph clustering.
    
    Groups papers into clusters based on citation patterns.
    """
    
    def __init__(self, resolution: float = 1.0):
        """
        Initialize clusterer.
        
        Args:
            resolution: Resolution parameter (higher = more clusters)
        """
        self.resolution = resolution
    
    def cluster(self, graph: nx.DiGraph) -> Dict[str, int]:
        """
        Cluster graph nodes using Louvain algorithm.
        
        Args:
            graph: Directed graph
        
        Returns:
            Dictionary mapping node IDs to cluster IDs
        
        Raises:
            ClusteringError: If clustering fails
        """
        if not LOUVAIN_AVAILABLE:
            raise ClusteringError("python-louvain not installed")
        
        logger.info(f"Running Louvain clustering (resolution={self.resolution})")
        
        # Convert to undirected for community detection
        undirected = graph.to_undirected()
        
        # Run Louvain
        partition = community_louvain.best_partition(
            undirected,
            resolution=self.resolution
        )
        
        num_clusters = len(set(partition.values()))
        logger.info(f"Found {num_clusters} clusters")
        
        return partition


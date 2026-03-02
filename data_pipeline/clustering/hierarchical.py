"""
Hierarchical sub-clustering within parent clusters.

Extracted from graph_builder6.py compute_subclusters method.
"""

from typing import Dict, Tuple
from collections import defaultdict
import networkx as nx

from data_pipeline.utils.logging import get_logger

try:
    import community as community_louvain
    LOUVAIN_AVAILABLE = True
except ImportError:
    LOUVAIN_AVAILABLE = False

logger = get_logger("clustering.hierarchical")


class HierarchicalClusterer:
    """
    Hierarchical clustering to create sub-clusters within parent clusters.
    """
    
    def __init__(self, resolution: float = 1.0):
        """
        Initialize hierarchical clusterer.
        
        Args:
            resolution: Resolution for sub-clustering
        """
        self.resolution = resolution
    
    def compute_subclusters(
        self,
        graph: nx.DiGraph,
        parent_clusters: Dict[str, int]
    ) -> Dict[str, int]:
        """
        Compute sub-clusters within each parent cluster.
        
        Args:
            graph: Directed graph
            parent_clusters: Parent cluster assignments {node: cluster_id}
        
        Returns:
            Sub-cluster assignments {node: sub_cluster_id}
        """
        logger.info("Computing sub-clusters")
        
        # Group nodes by parent cluster
        clusters_nodes = defaultdict(list)
        for node, cluster_id in parent_clusters.items():
            clusters_nodes[cluster_id].append(node)
        
        # Cluster each parent cluster separately
        sub_clusters = {}
        next_sub_id = 0
        
        for cluster_id, nodes in clusters_nodes.items():
            if len(nodes) < 3:
                # Too small to sub-cluster
                for node in nodes:
                    sub_clusters[node] = next_sub_id
                next_sub_id += 1
                continue
            
            # Extract subgraph
            subgraph = graph.subgraph(nodes)
            
            # Run Louvain on subgraph
            undirected = subgraph.to_undirected()
            partition = community_louvain.best_partition(
                undirected,
                resolution=self.resolution
            )
            
            # Renumber to global sub-cluster IDs
            local_to_global = {}
            for node, local_id in partition.items():
                if local_id not in local_to_global:
                    local_to_global[local_id] = next_sub_id
                    next_sub_id += 1
                sub_clusters[node] = local_to_global[local_id]
        
        num_sub_clusters = len(set(sub_clusters.values()))
        logger.info(f"Found {num_sub_clusters} sub-clusters")
        
        return sub_clusters


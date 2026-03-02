"""Graph data model."""

from dataclasses import dataclass, field
from typing import Optional
import networkx as nx


@dataclass
class PaperGraphData:
    """Container for all graph-related data."""
    
    # Core graph
    graph: nx.DiGraph = field(default_factory=nx.DiGraph)
    
    # Layout positions
    positions: dict[str, tuple[float, float]] = field(default_factory=dict)
    
    # Clustering results
    clusters: dict[str, int] = field(default_factory=dict)  # doi -> cluster_id
    sub_clusters: dict[str, int] = field(default_factory=dict)  # doi -> sub_cluster_id
    
    # Labels
    cluster_labels: dict[int, str] = field(default_factory=dict)  # cluster_id -> label
    sub_cluster_labels: dict[tuple[int, int], str] = field(default_factory=dict)  # (cluster, sub) -> label
    
    # Centroids
    cluster_centroids: dict[int, tuple[float, float]] = field(default_factory=dict)
    sub_cluster_centroids: dict[tuple[int, int], tuple[float, float]] = field(default_factory=dict)
    
    # Embeddings (optional, cached)
    embeddings: Optional[dict[str, list[float]]] = None
    
    def get_paper(self, doi: str) -> Optional[dict]:
        """Get paper attributes by DOI."""
        if doi not in self.graph:
            return None
        return self.graph.nodes[doi]
    
    def get_edges(self) -> list[tuple[str, str]]:
        """Get all edges as list of (source, target) tuples."""
        return list(self.graph.edges())
    
    def num_nodes(self) -> int:
        """Number of nodes in graph."""
        return self.graph.number_of_nodes()
    
    def num_edges(self) -> int:
        """Number of edges in graph."""
        return self.graph.number_of_edges()
    
    def num_clusters(self) -> int:
        """Number of unique clusters."""
        return len(set(self.clusters.values())) if self.clusters else 0
    
    def num_sub_clusters(self) -> int:
        """Number of unique sub-clusters."""
        return len(set(self.sub_clusters.values())) if self.sub_clusters else 0


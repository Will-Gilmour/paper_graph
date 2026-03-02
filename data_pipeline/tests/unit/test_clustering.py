"""Test clustering algorithms."""

import pytest
import networkx as nx

from data_pipeline.clustering.louvain import LouvainClusterer
from data_pipeline.clustering.hierarchical import HierarchicalClusterer


class TestLouvainClusterer:
    """Test Louvain clustering."""
    
    def test_initialization(self):
        """Test clusterer initialization."""
        clusterer = LouvainClusterer(resolution=1.5)
        
        assert clusterer.resolution == 1.5
    
    def test_cluster_small_graph(self, sample_graph):
        """Test clustering a small graph."""
        clusterer = LouvainClusterer(resolution=1.0)
        clusters = clusterer.cluster(sample_graph)
        
        # Should assign cluster IDs to all nodes
        assert len(clusters) == sample_graph.number_of_nodes()
        
        # All nodes should have cluster assignments
        for node in sample_graph.nodes():
            assert node in clusters
            assert isinstance(clusters[node], int)
        
        # Should have at least 1 cluster
        unique_clusters = set(clusters.values())
        assert len(unique_clusters) >= 1
    
    def test_cluster_disconnected_graph(self):
        """Test clustering disconnected graph."""
        G = nx.DiGraph()
        # Two disconnected components
        G.add_edges_from([
            ("a", "b"), ("b", "c"),
            ("x", "y"), ("y", "z"),
        ])
        
        clusterer = LouvainClusterer()
        clusters = clusterer.cluster(G)
        
        # Should still work
        assert len(clusters) == 6


class TestHierarchicalClusterer:
    """Test hierarchical sub-clustering."""
    
    def test_initialization(self):
        """Test clusterer initialization."""
        clusterer = HierarchicalClusterer(resolution=0.8)
        
        assert clusterer.resolution == 0.8
    
    def test_compute_subclusters(self, sample_graph):
        """Test computing sub-clusters."""
        # First do parent clustering
        parent_clusterer = LouvainClusterer()
        parent_clusters = parent_clusterer.cluster(sample_graph)
        
        # Then sub-cluster
        hierarchical = HierarchicalClusterer()
        sub_clusters = hierarchical.compute_subclusters(
            sample_graph,
            parent_clusters
        )
        
        # All nodes should have sub-cluster assignments
        assert len(sub_clusters) == sample_graph.number_of_nodes()
        
        # All nodes should have valid sub-cluster IDs
        for node in sample_graph.nodes():
            assert node in sub_clusters
            assert isinstance(sub_clusters[node], int)
    
    def test_small_cluster_handling(self):
        """Test handling of very small clusters."""
        G = nx.DiGraph()
        G.add_nodes_from(["a", "b", "c"])
        G.add_edge("a", "b")
        
        parent_clusters = {"a": 0, "b": 0, "c": 1}
        
        hierarchical = HierarchicalClusterer()
        sub_clusters = hierarchical.compute_subclusters(G, parent_clusters)
        
        # Should handle small clusters gracefully
        assert len(sub_clusters) == 3


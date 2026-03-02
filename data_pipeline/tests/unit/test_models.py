"""Test data models."""

import pytest
import networkx as nx

from data_pipeline.models.paper import Paper
from data_pipeline.models.graph import PaperGraphData
from data_pipeline.models.cluster import Cluster, SubCluster


class TestPaper:
    """Test Paper model."""
    
    def test_from_crossref_work(self, sample_crossref_work):
        """Test creating Paper from Crossref response."""
        paper = Paper.from_crossref_work(sample_crossref_work)
        
        assert paper.doi == "10.1001/jama.2020.12345"
        assert paper.title == "Sample Medical Research Paper"
        assert len(paper.authors) == 2
        assert "John Doe" in paper.authors
        assert paper.year == 2020
        assert paper.container_title == "JAMA"
        assert paper.references_count == 2
    
    def test_to_dict(self):
        """Test Paper serialization."""
        paper = Paper(
            doi="10.1001/test",
            title="Test Paper",
            authors=["Author One"],
            year=2020,
        )
        
        data = paper.to_dict()
        
        assert isinstance(data, dict)
        assert data["doi"] == "10.1001/test"
        assert data["title"] == "Test Paper"
        assert data["year"] == 2020
    
    def test_from_dict(self):
        """Test Paper deserialization."""
        data = {
            "doi": "10.1001/test",
            "title": "Test Paper",
            "authors": ["Author One"],
            "year": 2020,
            "cited_count": 5,
            "references_count": 10,
        }
        
        paper = Paper.from_dict(data)
        
        assert paper.doi == "10.1001/test"
        assert paper.title == "Test Paper"
        assert paper.cited_count == 5


class TestPaperGraphData:
    """Test PaperGraphData model."""
    
    def test_initialization(self):
        """Test PaperGraphData initialization."""
        graph_data = PaperGraphData()
        
        assert isinstance(graph_data.graph, nx.DiGraph)
        assert graph_data.num_nodes() == 0
        assert graph_data.num_edges() == 0
    
    def test_with_sample_graph(self, sample_graph):
        """Test with actual graph data."""
        graph_data = PaperGraphData()
        graph_data.graph = sample_graph
        
        assert graph_data.num_nodes() == 5
        assert graph_data.num_edges() == 5
    
    def test_get_paper(self, sample_graph):
        """Test getting paper attributes."""
        graph_data = PaperGraphData()
        graph_data.graph = sample_graph
        
        paper = graph_data.get_paper("10.1001/paper1")
        
        assert paper is not None
        assert paper["title"] == "Paper 1"
        assert paper["year"] == 2020
    
    def test_get_edges(self, sample_graph):
        """Test getting edge list."""
        graph_data = PaperGraphData()
        graph_data.graph = sample_graph
        
        edges = graph_data.get_edges()
        
        assert len(edges) == 5
        assert ("10.1001/paper1", "10.1001/paper3") in edges


class TestCluster:
    """Test Cluster model."""
    
    def test_cluster_creation(self):
        """Test creating Cluster."""
        cluster = Cluster(
            id=1,
            label="Test Cluster",
            size=100,
            x=10.5,
            y=20.3,
        )
        
        assert cluster.id == 1
        assert cluster.label == "Test Cluster"
        assert cluster.size == 100
    
    def test_to_dict(self):
        """Test Cluster serialization."""
        cluster = Cluster(
            id=1,
            label="Test Cluster",
            size=100,
            x=10.5,
            y=20.3,
        )
        
        data = cluster.to_dict()
        
        assert data["id"] == 1
        assert data["label"] == "Test Cluster"
        assert data["size"] == 100


class TestSubCluster:
    """Test SubCluster model."""
    
    def test_subcuster_creation(self):
        """Test creating SubCluster."""
        sub = SubCluster(
            parent_id=1,
            sub_id=5,
            label="Sub Test",
            size=20,
            x=1.0,
            y=2.0,
        )
        
        assert sub.parent_id == 1
        assert sub.sub_id == 5
        assert sub.full_id == (1, 5)
    
    def test_to_dict(self):
        """Test SubCluster serialization."""
        sub = SubCluster(
            parent_id=1,
            sub_id=5,
            label="Sub Test",
            size=20,
            x=1.0,
            y=2.0,
        )
        
        data = sub.to_dict()
        
        assert data["parent_id"] == 1
        assert data["sub_id"] == 5


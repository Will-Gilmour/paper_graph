"""Test graph building."""

import pytest
from unittest.mock import Mock, patch
import networkx as nx

from data_pipeline.graph.builder import GraphBuilder
from data_pipeline.graph.crawler import CitationCrawler


class TestGraphBuilder:
    """Test GraphBuilder."""
    
    @pytest.fixture
    def mock_crawler(self):
        """Create a mock crawler."""
        crawler = Mock(spec=CitationCrawler)
        
        # Mock crawl to return a simple graph
        def mock_crawl(seed_doi, max_depth, year_from=None):
            G = nx.DiGraph()
            G.add_node(seed_doi, title="Seed Paper", year=2020, authors=["A"])
            G.add_node("10.1001/ref1", title="Reference 1", year=2019, authors=["B"])
            G.add_edge(seed_doi, "10.1001/ref1")
            return G
        
        crawler.crawl = mock_crawl
        return crawler
    
    def test_initialization(self, mock_crawler):
        """Test builder initialization."""
        builder = GraphBuilder(mock_crawler)
        
        assert builder.crawler == mock_crawler
        assert builder.graph_data.num_nodes() == 0
    
    def test_add_paper(self, mock_crawler):
        """Test adding a paper."""
        builder = GraphBuilder(mock_crawler)
        builder.add_paper("10.1001/test", max_depth=1)
        
        # Should have added nodes from the crawl
        assert builder.graph_data.num_nodes() > 0
        assert "10.1001/test" in builder.graph_data.graph
    
    def test_add_papers_batch(self, mock_crawler):
        """Test adding multiple papers."""
        builder = GraphBuilder(mock_crawler)
        
        dois = ["10.1001/test1", "10.1001/test2"]
        builder.add_papers_batch(dois, max_depth=1)
        
        # Should have added both seeds
        assert builder.graph_data.num_nodes() >= 2
    
    def test_validate_empty_graph(self, mock_crawler):
        """Test validation of empty graph."""
        builder = GraphBuilder(mock_crawler)
        
        from data_pipeline.utils.errors import PipelineError
        with pytest.raises(PipelineError):
            builder.validate()
    
    def test_validate_valid_graph(self, mock_crawler):
        """Test validation of valid graph."""
        builder = GraphBuilder(mock_crawler)
        builder.add_paper("10.1001/test", max_depth=1)
        
        # Should pass validation
        assert builder.validate() is True


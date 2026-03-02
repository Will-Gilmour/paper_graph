"""
Unit tests for LOD (Level of Detail) service
"""
import pytest
from unittest.mock import patch, MagicMock

from backend.app.services.lod_service import LODService


class TestLODService:
    """Test LOD service functionality"""
    
    @patch('backend.app.services.lod_service.queries')
    def test_get_nodes_in_viewport_basic(self, mock_queries):
        """Test basic viewport node fetching"""
        # Mock node data
        mock_queries.fetch_nodes_in_bbox.return_value = [
            {
                "doi": "10.1234/test1",
                "title": "Test Paper 1",
                "x": 10.0,
                "y": 20.0,
                "cluster": 1,
                "cited_count": 50,
                "references_count": 25,
                "year": 2020,
                "fncr": 0.5,
            }
        ]
        
        # Mock edges
        mock_queries.fetch_edges_for_dois.return_value = [
            ("10.1234/test1", "10.1234/test2")
        ]
        
        service = LODService()
        result = service.get_nodes_in_viewport(
            x_min=0.0,
            x_max=100.0,
            y_min=0.0,
            y_max=100.0,
            min_citations=10,
            limit=500
        )
        
        # Verify result structure
        assert "nodes" in result
        assert "edges" in result
        assert "meta" in result
        assert len(result["nodes"]) == 1
        assert len(result["edges"]) == 1
        
        # Verify node data
        assert result["nodes"][0]["doi"] == "10.1234/test1"
        assert result["meta"]["viewport"]["x_min"] == 0.0
        assert result["meta"]["min_citations"] == 10
    
    @patch('backend.app.services.lod_service.queries')
    def test_get_nodes_in_viewport_empty(self, mock_queries):
        """Test viewport fetching with no results"""
        mock_queries.fetch_nodes_in_bbox.return_value = []
        
        service = LODService()
        result = service.get_nodes_in_viewport(
            x_min=0.0,
            x_max=100.0,
            y_min=0.0,
            y_max=100.0,
        )
        
        assert result["nodes"] == []
        assert result["edges"] == []
        assert result["meta"]["count"] == 0
    
    @patch('backend.app.services.lod_service.queries')
    def test_get_nodes_in_viewport_with_edges(self, mock_queries):
        """Test that edges are correctly filtered to nodes in viewport"""
        # Mock two nodes
        mock_queries.fetch_nodes_in_bbox.return_value = [
            {"doi": "10.1/a", "title": "A", "x": 1.0, "y": 1.0, "cluster": 1, "cited_count": 10, "references_count": 5, "year": 2020, "fncr": 0.1},
            {"doi": "10.1/b", "title": "B", "x": 2.0, "y": 2.0, "cluster": 1, "cited_count": 20, "references_count": 10, "year": 2021, "fncr": 0.2},
        ]
        
        # Mock edges (should only include edges between these nodes)
        mock_queries.fetch_edges_for_dois.return_value = [
            ("10.1/a", "10.1/b")
        ]
        
        service = LODService()
        result = service.get_nodes_in_viewport(0.0, 10.0, 0.0, 10.0)
        
        # Verify edges are transformed from tuples to dicts
        assert len(result["edges"]) == 1
        assert result["edges"][0] == {"source": "10.1/a", "target": "10.1/b"}


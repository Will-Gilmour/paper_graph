"""
Unit tests for recommendations service
"""
import pytest
from unittest.mock import patch

from backend.app.services.recommendations_service import RecommendationsService


class TestRecommendationsService:
    """Test recommendations service functionality"""
    
    # ========================================================================
    # SPATIAL RECOMMENDATIONS TESTS
    # ========================================================================
    
    @patch('backend.app.services.recommendations_service.queries')
    def test_spatial_recommendations_centroid_calculation(self, mock_queries):
        """Test that centroid is correctly calculated from collection"""
        # Mock paper positions
        mock_queries.fetch_paper_positions.return_value = [
            {"doi": "10.1/a", "x": 0.0, "y": 0.0},
            {"doi": "10.1/b", "x": 100.0, "y": 100.0},
        ]
        mock_queries.fetch_papers_in_radius.return_value = []
        
        service = RecommendationsService()
        result = service.get_spatial_recommendations(
            dois=["10.1/a", "10.1/b"],
            top_n=10
        )
        
        # Centroid should be (50, 50)
        assert result["centroid"]["x"] == 50.0
        assert result["centroid"]["y"] == 50.0
        assert result["collection_size"] == 2
        assert result["papers_in_graph"] == 2
    
    @patch('backend.app.services.recommendations_service.queries')
    def test_spatial_recommendations_scoring(self, mock_queries):
        """Test spatial recommendation scoring formula"""
        # Mock collection at origin
        mock_queries.fetch_paper_positions.return_value = [
            {"doi": "10.1/center", "x": 0.0, "y": 0.0},
        ]
        
        # Mock candidates at various distances
        mock_queries.fetch_papers_in_radius.return_value = [
            {"doi": "10.1/near", "title": "Near Paper", "x": 3.0, "y": 4.0, "cluster": 1, "cited_count": 100, "year": 2020},
            {"doi": "10.1/far", "title": "Far Paper", "x": 30.0, "y": 40.0, "cluster": 1, "cited_count": 100, "year": 2020},
        ]
        
        service = RecommendationsService()
        result = service.get_spatial_recommendations(
            dois=["10.1/center"],
            top_n=10,
            exclude_collection=False  # Include for testing
        )
        
        # Near paper should have higher score (distance = 5, far = 50)
        assert len(result["recommendations"]) == 2
        near = [r for r in result["recommendations"] if r["doi"] == "10.1/near"][0]
        far = [r for r in result["recommendations"] if r["doi"] == "10.1/far"][0]
        
        assert near["distance"] == 5.0
        assert far["distance"] == 50.0
        assert near["score"] > far["score"]  # Near should score higher
    
    @patch('backend.app.services.recommendations_service.queries')
    def test_spatial_null_year_handling(self, mock_queries):
        """Test that null years are handled gracefully"""
        mock_queries.fetch_paper_positions.return_value = [
            {"doi": "10.1/a", "x": 0.0, "y": 0.0},
        ]
        
        # Paper with null year
        mock_queries.fetch_papers_in_radius.return_value = [
            {"doi": "10.1/b", "title": "No Year", "x": 10.0, "y": 10.0, "cluster": 1, "cited_count": 50, "year": None},
        ]
        
        service = RecommendationsService()
        result = service.get_spatial_recommendations(dois=["10.1/a"], top_n=10, exclude_collection=False)
        
        # Should not crash, should default year to 2000
        assert len(result["recommendations"]) == 1
        assert result["recommendations"][0]["year"] == 2000
    
    @patch('backend.app.services.recommendations_service.queries')
    def test_spatial_filter_collection(self, mock_queries):
        """Test that collection papers are excluded from recommendations"""
        mock_queries.fetch_paper_positions.return_value = [
            {"doi": "10.1/a", "x": 0.0, "y": 0.0},
        ]
        
        mock_queries.fetch_papers_in_radius.return_value = [
            {"doi": "10.1/a", "title": "In Collection", "x": 1.0, "y": 1.0, "cluster": 1, "cited_count": 50, "year": 2020},
            {"doi": "10.1/b", "title": "Not in Collection", "x": 2.0, "y": 2.0, "cluster": 1, "cited_count": 50, "year": 2020},
        ]
        
        service = RecommendationsService()
        result = service.get_spatial_recommendations(
            dois=["10.1/a"],
            top_n=10,
            exclude_collection=True
        )
        
        # Should only return paper B
        assert len(result["recommendations"]) == 1
        assert result["recommendations"][0]["doi"] == "10.1/b"
    
    @patch('backend.app.services.recommendations_service.queries')
    def test_spatial_no_papers_in_graph(self, mock_queries):
        """Test spatial recommendations when papers not in graph"""
        mock_queries.fetch_paper_positions.return_value = []  # No papers found
        
        service = RecommendationsService()
        result = service.get_spatial_recommendations(dois=["10.1/missing"], top_n=10)
        
        assert result["papers_in_graph"] == 0
        assert "error" in result
        assert "None of the selected papers" in result["error"]
    
    # ========================================================================
    # BRIDGE RECOMMENDATIONS TESTS
    # ========================================================================
    
    @patch('backend.app.services.recommendations_service.queries')
    def test_bridge_recommendations_basic(self, mock_queries):
        """Test bridge recommendations with simple case"""
        # Collection has 2 papers
        dois = ["10.1/a", "10.1/b"]
        
        # Mock edges: paper C cites both A and B
        mock_queries.fetch_edges_involving_dois.return_value = [
            ("10.1/c", "10.1/a"),  # C -> A
            ("10.1/c", "10.1/b"),  # C -> B
        ]
        
        # Mock metadata for bridge C
        mock_queries.fetch_papers_by_dois.return_value = [
            {"doi": "10.1/c", "title": "Bridge Paper", "cluster": 1, "cited_count": 100, "year": 2020, "x": 50.0, "y": 50.0}
        ]
        
        service = RecommendationsService()
        result = service.get_bridge_recommendations(dois=dois, top_n=10, min_connections=1)
        
        # Should find paper C as a bridge
        assert len(result["recommendations"]) == 1
        bridge = result["recommendations"][0]
        assert bridge["doi"] == "10.1/c"
        assert bridge["connection_count"] == 2
        assert set(bridge["connected_papers"]) == {"10.1/a", "10.1/b"}
    
    @patch('backend.app.services.recommendations_service.queries')
    def test_bridge_recommendations_scoring(self, mock_queries):
        """Test bridge scoring formula: (connections)^2 * (1 + importance)"""
        dois = ["10.1/a", "10.1/b", "10.1/c"]
        
        # Paper X connects to 2 papers, Paper Y connects to 1
        mock_queries.fetch_edges_involving_dois.return_value = [
            ("10.1/x", "10.1/a"),
            ("10.1/x", "10.1/b"),
            ("10.1/y", "10.1/a"),
        ]
        
        # Both have same citations (100)
        mock_queries.fetch_papers_by_dois.return_value = [
            {"doi": "10.1/x", "title": "X", "cluster": 1, "cited_count": 100, "year": 2020, "x": 1.0, "y": 1.0},
            {"doi": "10.1/y", "title": "Y", "cluster": 1, "cited_count": 100, "year": 2020, "x": 2.0, "y": 2.0},
        ]
        
        service = RecommendationsService()
        result = service.get_bridge_recommendations(dois=dois, top_n=10, min_connections=1)
        
        assert len(result["recommendations"]) == 2
        
        # Paper X should score higher (2^2 * importance vs 1^2 * importance)
        x = [r for r in result["recommendations"] if r["doi"] == "10.1/x"][0]
        y = [r for r in result["recommendations"] if r["doi"] == "10.1/y"][0]
        
        assert x["connection_count"] == 2
        assert y["connection_count"] == 1
        assert x["score"] > y["score"]  # X should rank higher
    
    @patch('backend.app.services.recommendations_service.queries')
    def test_bridge_empty_collection(self, mock_queries):
        """Test bridge recommendations with empty collection"""
        service = RecommendationsService()
        result = service.get_bridge_recommendations(dois=[], top_n=10)
        
        assert result["collection_size"] == 0
        assert "error" in result
        assert result["error"] == "Empty collection"
    
    @patch('backend.app.services.recommendations_service.queries')
    def test_bridge_no_bridges_found(self, mock_queries):
        """Test bridge recommendations when no bridges exist"""
        dois = ["10.1/a", "10.1/b"]
        
        # Only internal edges (no external bridges)
        mock_queries.fetch_edges_involving_dois.return_value = [
            ("10.1/a", "10.1/b"),
        ]
        
        service = RecommendationsService()
        result = service.get_bridge_recommendations(dois=dois, top_n=10, min_connections=1)
        
        # When no bridges found, error response doesn't include total_bridges_found
        assert len(result["recommendations"]) == 0
        assert "error" in result
        assert "No bridge papers found" in result["error"]
    
    @patch('backend.app.services.recommendations_service.queries')
    def test_bridge_bidirectional_edges(self, mock_queries):
        """Test that bridges work with both incoming and outgoing citations"""
        dois = ["10.1/a", "10.1/b"]
        
        # Paper X is cited by A and cites B (bidirectional bridge)
        mock_queries.fetch_edges_involving_dois.return_value = [
            ("10.1/a", "10.1/x"),  # A cites X
            ("10.1/x", "10.1/b"),  # X cites B
        ]
        
        mock_queries.fetch_papers_by_dois.return_value = [
            {"doi": "10.1/x", "title": "X", "cluster": 1, "cited_count": 50, "year": 2020, "x": 1.0, "y": 1.0}
        ]
        
        service = RecommendationsService()
        result = service.get_bridge_recommendations(dois=dois, top_n=10, min_connections=1)
        
        # X should be found as a bridge connecting both
        assert len(result["recommendations"]) == 1
        bridge = result["recommendations"][0]
        assert bridge["doi"] == "10.1/x"
        assert bridge["connection_count"] == 2


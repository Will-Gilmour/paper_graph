"""
Unit tests for search service
"""
import pytest
from unittest.mock import Mock, patch

from backend.app.services.search_service import SearchService


class TestSearchService:
    """Test search service functionality"""
    
    def test_simple_tokens(self):
        """Test tokenization with stop word removal"""
        service = SearchService()
        
        tokens = service._simple_tokens("The quick brown fox and the lazy dog")
        
        assert "quick" in tokens
        assert "brown" in tokens
        assert "fox" in tokens
        assert "lazy" in tokens
        assert "dog" in tokens
        assert "the" not in tokens  # Stop word
        assert "and" not in tokens  # Stop word
    
    @patch('backend.app.services.search_service.queries')
    def test_search_papers_empty_query(self, mock_queries):
        """Test search with empty query"""
        service = SearchService()
        
        result = service.search_papers("")
        
        assert result == {"results": []}
        mock_queries.search_papers_by_title.assert_not_called()
    
    @patch('backend.app.services.search_service.queries')
    def test_search_papers_with_results(self, mock_queries):
        """Test search that finds matching papers"""
        mock_queries.search_papers_by_title.return_value = [
            ("10.1234/test1", "Essential Tremor Research"),
            ("10.1234/test2", "Tremor Analysis Methods"),
        ]
        
        service = SearchService()
        result = service.search_papers("tremor", top_k=10)
        
        assert "results" in result
        assert len(result["results"]) <= 10
        # Results should be sorted by score
        if len(result["results"]) > 1:
            assert result["results"][0]["score"] >= result["results"][1]["score"]
    
    @patch('backend.app.services.search_service.queries')
    def test_search_papers_exact_match(self, mock_queries):
        """Test that exact substring matches get highest score"""
        mock_queries.search_papers_by_title.return_value = [
            ("10.1234/test1", "This contains tremor exactly"),
            ("10.1234/test2", "Unrelated paper about something else"),
        ]
        
        service = SearchService()
        result = service.search_papers("tremor", top_k=10)
        
        # First result should have score of 100 (exact match)
        assert result["results"][0]["score"] == 100
        assert result["results"][0]["doi"] == "10.1234/test1"
    
    @patch('backend.app.services.search_service.queries')
    @patch('backend.app.services.search_service.get_db_connection')
    def test_find_nearby_papers(self, mock_conn, mock_queries):
        """Test finding papers nearby a query paper"""
        # Mock search to find center paper
        mock_queries.search_papers_by_title.return_value = [
            ("10.1234/center", "Center Paper")
        ]
        
        # Mock database connection for spatial query
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            ("10.1234/nearby1", "Nearby Paper 1", 10.0, 20.0, 1.5),
            ("10.1234/nearby2", "Nearby Paper 2", 11.0, 21.0, 2.0),
        ]
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.__enter__ = Mock(return_value=mock_connection)
        mock_connection.__exit__ = Mock(return_value=False)
        
        mock_conn.return_value = mock_connection
        
        service = SearchService()
        result = service.find_nearby_papers("center", k=5)
        
        assert "results" in result
        assert len(result["results"]) <= 5
    
    @patch('backend.app.services.search_service.queries')
    def test_find_nearby_papers_no_match(self, mock_queries):
        """Test finding nearby papers when query doesn't match anything"""
        mock_queries.search_papers_by_title.return_value = []
        
        service = SearchService()
        result = service.find_nearby_papers("nonexistent", k=5)
        
        assert result == {"results": []}


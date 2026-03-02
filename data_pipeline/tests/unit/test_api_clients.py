"""Test API clients."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from data_pipeline.api.crossref import CrossrefClient
from data_pipeline.api.openalex import OpenAlexClient
from data_pipeline.utils.errors import APIError


class TestCrossrefClient:
    """Test Crossref API client."""
    
    def test_initialization(self):
        """Test client initialization."""
        client = CrossrefClient(mailto="test@example.com")
        
        assert client.mailto == "test@example.com"
        assert client.session is not None
    
    @patch('requests.Session.get')
    def test_fetch_work_success(self, mock_get):
        """Test successful work fetch."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"DOI": "10.1001/test", "title": ["Test Paper"]}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        client = CrossrefClient(mailto="test@example.com", cache_dir=None)
        work = client.fetch_work("10.1001/test")
        
        assert work["DOI"] == "10.1001/test"
        assert work["title"] == ["Test Paper"]
    
    def test_get_references(self, sample_crossref_work):
        """Test extracting references from work."""
        client = CrossrefClient(mailto="test@example.com", cache_dir=None)
        
        with patch.object(client, 'fetch_work', return_value=sample_crossref_work):
            refs = client.get_references("10.1001/jama.2020.12345")
            
            assert len(refs) == 2
            assert "10.1001/ref1" in refs
            assert "10.1001/ref2" in refs
    
    @patch('requests.Session.get')
    def test_api_error_handling(self, mock_get):
        """Test API error handling."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        client = CrossrefClient(mailto="test@example.com", cache_dir=None)
        
        with pytest.raises(APIError):
            client.fetch_work("10.1001/nonexistent")


class TestOpenAlexClient:
    """Test OpenAlex API client."""
    
    def test_initialization(self):
        """Test client initialization."""
        client = OpenAlexClient(mailto="test@example.com")
        
        assert client.mailto == "test@example.com"
    
    def test_clean_doi(self):
        """Test DOI cleaning."""
        assert OpenAlexClient._clean_doi("https://doi.org/10.1001/test") == "10.1001/test"
        assert OpenAlexClient._clean_doi("HTTP://DOI.ORG/10.1001/TEST") == "10.1001/test"
        assert OpenAlexClient._clean_doi(None) is None
    
    @patch('requests.Session.get')
    def test_fetch_citers(self, mock_get):
        """Test fetching citing papers."""
        # Mock needs to handle two calls:
        # 1. _get_openalex_id: GET /works/https://doi.org/10.1001/test
        # 2. fetch_citers: GET /works?filter=cites:W123
        
        def mock_response_factory(*args, **kwargs):
            mock_response = Mock()
            mock_response.status_code = 200
            
            url = args[0] if args else kwargs.get('url', '')
            if 'doi.org' in url:
                # _get_openalex_id call
                mock_response.json.return_value = {"id": "https://openalex.org/W123"}
            else:
                # fetch_citers call
                mock_response.json.return_value = {
                    "results": [
                        {"doi": "https://doi.org/10.1001/citer1", "publication_year": 2021},
                        {"doi": "https://doi.org/10.1001/citer2", "publication_year": 2022},
                    ],
                    "meta": {"next_cursor": None}
                }
            return mock_response
        
        mock_get.side_effect = mock_response_factory
        
        client = OpenAlexClient(mailto="test@example.com", cache_dir=None)
        citers = client.fetch_citers("10.1001/test", max_results=10)
        
        assert len(citers) == 2
        assert "10.1001/citer1" in citers
        assert "10.1001/citer2" in citers
    
    @patch('requests.Session.get')
    def test_fetch_citers_with_year_filter(self, mock_get):
        """Test fetching citers with year filter."""
        def mock_response_factory(*args, **kwargs):
            mock_response = Mock()
            mock_response.status_code = 200
            
            url = args[0] if args else kwargs.get('url', '')
            if 'doi.org' in url:
                # _get_openalex_id call
                mock_response.json.return_value = {"id": "https://openalex.org/W456"}
            else:
                # fetch_citers call
                mock_response.json.return_value = {
                    "results": [
                        {"doi": "https://doi.org/10.1001/old", "publication_year": 2010},
                        {"doi": "https://doi.org/10.1001/new", "publication_year": 2020},
                    ],
                    "meta": {"next_cursor": None}
                }
            return mock_response
        
        mock_get.side_effect = mock_response_factory
        
        client = OpenAlexClient(mailto="test@example.com", cache_dir=None)
        citers = client.fetch_citers("10.1001/test", max_results=10, year_from=2015)
        
        # Should only include papers from 2015 onwards
        assert len(citers) == 1
        assert "10.1001/new" in citers


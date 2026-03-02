"""Crossref API client for fetching paper metadata."""

from typing import Dict, Any, Optional, List

from data_pipeline.api.base import BaseAPIClient
from data_pipeline.utils.logging import get_logger
from data_pipeline.utils.errors import APIError


logger = get_logger("api.crossref")


class CrossrefClient(BaseAPIClient):
    """
    Client for Crossref API.
    
    Provides access to paper metadata and citations.
    """
    
    API_URL = "https://api.crossref.org/works"
    
    def _get_user_agent(self) -> str:
        """Get user agent for Crossref."""
        return f"PaperGraph/2.0 (+mailto:{self.mailto})"
    
    def fetch_work(self, doi: str) -> Dict[str, Any]:
        """
        Fetch work metadata by DOI.
        
        Args:
            doi: Paper DOI (will be lowercased)
        
        Returns:
            Work metadata dict
        
        Raises:
            APIError: If DOI not found or API error
        """
        doi_key = doi.lower()
        
        # Check cache first
        cached = self._get_from_cache(doi_key)
        if cached:
            logger.debug(f"Cache hit for DOI: {doi_key}")
            return cached
        
        # Fetch from API
        logger.debug(f"Fetching DOI from Crossref: {doi_key}")
        url = f"{self.API_URL}/{doi_key}"
        
        try:
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 404:
                raise APIError(f"DOI not found: {doi_key}")
            
            response.raise_for_status()
            work = response.json().get("message", {})
            
            # Cache the result
            self._put_in_cache(doi_key, work)
            
            # Rate limit
            self._rate_limit()
            
            return work
            
        except Exception as e:
            if isinstance(e, APIError):
                raise
            raise APIError(f"Error fetching DOI {doi_key}: {e}")
    
    def search(self, query: str, rows: int = 10) -> List[Dict[str, Any]]:
        """
        Search for works by query.
        
        Args:
            query: Search query
            rows: Number of results to return
        
        Returns:
            List of work metadata dicts
        """
        logger.debug(f"Searching Crossref: {query}")
        
        try:
            response = self.session.get(
                self.API_URL,
                params={
                    "query.bibliographic": query,
                    "rows": rows
                },
                timeout=30
            )
            response.raise_for_status()
            
            items = response.json().get("message", {}).get("items", [])
            
            # Rate limit
            self._rate_limit()
            
            return items
            
        except Exception as e:
            raise APIError(f"Error searching Crossref: {e}")
    
    def get_references(self, doi: str) -> List[str]:
        """
        Get reference DOIs from a work.
        
        Args:
            doi: Paper DOI
        
        Returns:
            List of referenced DOIs (lowercased)
        """
        work = self.fetch_work(doi)
        references = work.get("reference", [])
        return [ref["DOI"].lower() for ref in references if ref.get("DOI")]


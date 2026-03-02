"""OpenAlex API client for citation data."""

from typing import List, Optional

from data_pipeline.api.base import BaseAPIClient
from data_pipeline.utils.logging import get_logger
from data_pipeline.utils.errors import APIError


logger = get_logger("api.openalex")


class OpenAlexClient(BaseAPIClient):
    """
    Client for OpenAlex API.
    
    Provides access to citation data (citing papers).
    """
    
    API_URL = "https://api.openalex.org/works"
    
    def _get_user_agent(self) -> str:
        """Get user agent for OpenAlex."""
        return f"PaperGraph/2.0 (+mailto:{self.mailto})"
    
    @staticmethod
    def _clean_doi(raw: Optional[str]) -> Optional[str]:
        """
        Clean DOI from OpenAlex format.
        
        OpenAlex returns DOIs as URLs: https://doi.org/10.xxxx/yyyy
        We want just: 10.xxxx/yyyy
        """
        if not raw:
            return None
        raw = raw.lower()
        return raw.replace("https://doi.org/", "").replace("http://doi.org/", "").strip()
    
    def _get_openalex_id(self, doi: str) -> Optional[str]:
        """
        Convert DOI to OpenAlex W ID.
        
        Args:
            doi: Paper DOI
            
        Returns:
            OpenAlex W ID (e.g., 'W4403001572') or None if not found
        """
        doi_url = f"https://doi.org/{doi.lower()}"
        
        try:
            response = self.session.get(f"{self.API_URL}/{doi_url}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                openalex_url = data.get("id", "")  # e.g., "https://openalex.org/W4403001572"
                # Extract just the W ID
                if openalex_url and "/W" in openalex_url:
                    w_id = openalex_url.split("/")[-1]  # "W4403001572"
                    logger.debug(f"Resolved {doi} → {w_id}")
                    return w_id
            return None
        except Exception as e:
            logger.debug(f"Failed to resolve DOI to OpenAlex ID: {e}")
            return None
    
    def fetch_citers(
        self,
        doi: str,
        max_results: int = 200,
        year_from: Optional[int] = None
    ) -> List[str]:
        """
        Fetch DOIs of papers that cite the given DOI.
        
        Args:
            doi: Paper DOI to find citers for
            max_results: Maximum number of citers to return
            year_from: Only return citers from this year onwards (optional)
        
        Returns:
            List of citing paper DOIs (lowercased)
        """
        doi_key = doi.lower()
        
        # Check cache
        cache_key = f"citers:{doi_key}:{max_results}:{year_from or 'all'}"
        cached = self._get_from_cache(cache_key)
        if cached:
            logger.debug(f"Cache hit for citers: {doi_key}")
            return cached
        
        logger.debug(f"Fetching citers from OpenAlex: {doi_key}")
        
        # First, convert DOI to OpenAlex W ID (required for cites filter)
        w_id = self._get_openalex_id(doi_key)
        if not w_id:
            logger.warning(f"Could not resolve DOI {doi_key} to OpenAlex ID - skipping citers")
            return []
        
        citers: List[str] = []
        cursor = "*"
        rows_left = max_results
        
        try:
            while rows_left > 0 and cursor:
                params = {
                    "filter": f"cites:{w_id}",  # Use W ID, not DOI!
                    "per-page": min(200, rows_left),
                    "sort": "publication_date:desc",
                    "cursor": cursor,
                }
                if self.mailto:
                    params["mailto"] = self.mailto
                
                response = self.session.get(self.API_URL, params=params, timeout=30)
                
                # Provide more context for common errors
                if response.status_code == 403:
                    raise APIError(
                        f"OpenAlex returned 403 Forbidden for {doi_key}. "
                        f"This usually means: (1) The DOI is not in OpenAlex's database, "
                        f"(2) The DOI format is incorrect, or (3) Your email needs verification. "
                        f"URL: {response.url}"
                    )
                elif response.status_code == 429:
                    raise APIError(
                        f"OpenAlex rate limit exceeded. Please slow down requests or use a polite pool."
                    )
                
                response.raise_for_status()
                
                payload = response.json()
                
                # Extract DOIs
                for item in payload.get("results", []):
                    # Check year filter
                    year = item.get("publication_year")
                    if year_from and year and year < year_from:
                        continue
                    
                    citer_doi = self._clean_doi(item.get("doi"))
                    if citer_doi:
                        citers.append(citer_doi)
                        rows_left -= 1
                        if rows_left == 0:
                            break
                
                # Get next cursor
                cursor = payload.get("meta", {}).get("next_cursor")
                
                # Rate limit
                self._rate_limit()
            
            # Cache the result
            self._put_in_cache(cache_key, citers)
            
            logger.debug(f"Found {len(citers)} citers for {doi_key}")
            return citers
            
        except Exception as e:
            raise APIError(f"Error fetching citers for {doi_key}: {e}")


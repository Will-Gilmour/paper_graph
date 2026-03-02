"""
Search service - Business logic for paper search operations.

Provides fuzzy search with multiple fallback strategies.
"""
import re
from typing import List, Dict, Tuple, Optional
from rapidfuzz import fuzz

from backend.app.config.settings import logger
from backend.app.database import queries
from backend.app.database.connection import get_db_connection


# Stop words to ignore in search tokenization
STOP_WORDS = {
    'and', 'the', 'of', 'for', 'in', 'on', 'with', 'a', 'an', 'to', 'by', 'via', 'at', 'is'
}


class SearchService:
    """Service for search operations."""
    
    @staticmethod
    def _simple_tokens(text: str) -> List[str]:
        """
        Tokenize text into simple words, removing stop words.
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of lowercase tokens
        """
        return [
            w for w in re.split(r"[^\w]+", text.lower()) 
            if w and w not in STOP_WORDS
        ]
    
    def _find_candidates(self, query: str, field: str = "auto", limit: int = 200) -> List[Tuple[str, str]]:
        """
        Find candidate papers using SQL filters.
        
        Tries multiple strategies:
        1. DOI pattern matching (if query looks like DOI)
        2. Title substring match
        3. Trigram similarity (if pg_trgm available)
        4. Random sample (last resort)
        
        Args:
            query: Search query
            field: Field to search ("doi", "title", or "auto")
            limit: Maximum candidates to return
            
        Returns:
            List of (doi, title) tuples
        """
        # Strategy 1: DOI search
        if field == "doi" or (field == "auto" and query.startswith("10.")):
            return queries.search_papers_by_title(query, limit)  # Uses ILIKE on DOI too
        
        # Strategy 1b: Author search
        if field == "author":
            return queries.search_papers_by_author(query, limit)
        
        # Strategy 2: Title substring match
        if field == "title":
            candidates = queries.search_papers_by_title(query, limit)
            if candidates:
                return candidates
        
        # Strategy 3: Auto - try title first
        candidates = queries.search_papers_by_title(query, limit)
        if candidates:
            return candidates
        
        # Strategy 3: Trigram similarity (if available)
        if queries.check_pg_trgm_enabled():
            try:
                candidates = queries.search_papers_trigram(query, limit)
                if candidates:
                    return candidates
            except Exception as e:
                logger.warning(f"Trigram search failed: {e}")
        
        # Strategy 4: Random sample as last resort
        return queries.search_papers_random_sample(limit)
    
    def search_papers(
        self, 
        query: str = None,
        field: str = "auto", 
        top_k: int = 20,
        cluster_id: Optional[int] = None,
        year_min: Optional[int] = None,
        year_max: Optional[int] = None,
        min_citations: Optional[int] = None,
        title_query: Optional[str] = None,
        author_query: Optional[str] = None,
        cluster_ids: Optional[List[int]] = None
    ) -> Dict:
        """
        Search for papers using fuzzy matching with optional filters.
        
        Args:
            query: Search query string
            field: Field to search ("doi", "title", or "auto")
            top_k: Number of top results to return
            cluster_id: Optional filter by cluster ID
            year_min: Optional minimum publication year
            year_max: Optional maximum publication year
            min_citations: Optional minimum citation count
            
        Returns:
            Dictionary with "results" list of matching papers
        """
        # Use combined search if title_query or author_query provided
        if title_query or author_query or cluster_ids:
            combined_results = queries.search_papers_combined(
                title_query, author_query, cluster_ids, year_min, year_max, min_citations, limit=200
            )
            candidates = [(doi, title) for doi, title, _, _, _ in combined_results]
        # Use filtered search if filters but no specific title/author
        elif query and (cluster_id is not None or year_min is not None or year_max is not None or min_citations is not None):
            filtered_results = queries.search_papers_filtered(
                query, cluster_id, year_min, year_max, min_citations, limit=200
            )
            candidates = [(doi, title) for doi, title, _, _, _ in filtered_results]
        # Standard search with query
        elif query:
            candidates = self._find_candidates(query, field, limit=200)
        else:
            return {"results": []}
        
        if not candidates:
            return {"results": []}
        
        # Enhanced fuzzy scoring with multiple strategies
        scores = {}
        
        # Handle combined search (title + author)
        if title_query or author_query:
            # For combined search, just return candidates (already filtered by DB)
            for doi, title in candidates:
                scores[doi] = 95  # High score for DB-filtered results
        elif query:
            q_lc = query.lower()
            q_tokens = set(self._simple_tokens(query))
            
            for doi, title in candidates:
                if not title:
                    continue
                
                title_lc = title.lower()
                
                # Exact substring match gets highest score
                if q_lc in title_lc:
                    scores[doi] = 100
                    continue
                
                # Partial word match (e.g., "ultra" matches "ultrasound")
                q_words = q_lc.split()
                title_words = title_lc.split()
                partial_matches = sum(
                    1 for qw in q_words 
                    if any(qw in tw or tw in qw for tw in title_words)
                )
                if partial_matches > 0:
                    partial_ratio = (partial_matches / len(q_words)) * 100
                    scores[doi] = max(scores.get(doi, 0), 70 + partial_ratio * 0.3)
                
                # Token overlap scoring
                title_tokens = set(self._simple_tokens(title))
                if q_tokens and title_tokens:
                    overlap = len(q_tokens & title_tokens) / len(q_tokens)
                    if overlap > 0.3:  # Lowered from 0.5 for more flexibility
                        scores[doi] = max(scores.get(doi, 0), 60 + overlap * 40)
                
                # Multiple fuzzy matching strategies
                token_sort = fuzz.token_sort_ratio(q_lc, title_lc)
                token_set = fuzz.token_set_ratio(q_lc, title_lc)
                partial = fuzz.partial_ratio(q_lc, title_lc)
                
                # Use best fuzzy score
                best_fuzzy = max(token_sort, token_set, partial)
                scores[doi] = max(scores.get(doi, 0), best_fuzzy * 0.9)  # Scale down slightly
        else:
            # No query, shouldn't happen
            for doi, _ in candidates:
                scores[doi] = 50
        
        # Sort by score and return top K
        sorted_dois = sorted(scores.items(), key=lambda x: -x[1])
        results = [
            {
                "doi": doi,
                "score": score,
                "title": next(t for d, t in candidates if d == doi)
            }
            for doi, score in sorted_dois[:top_k]
        ]
        
        return {"results": results}
    
    def find_nearby_papers(self, query: str, k: int = 20) -> Dict:
        """
        Find papers nearby a query paper in spatial layout.
        
        Args:
            query: DOI or title to search for
            k: Number of nearby papers to return
            
        Returns:
            Dictionary with "results" list of nearby papers
        """
        # First resolve query to a DOI
        search_results = self.search_papers(query, field="auto", top_k=1)
        
        if not search_results["results"]:
            return {"results": []}
        
        center_doi = search_results["results"][0]["doi"]
        
        # Find k nearest neighbors by spatial distance
        run_id = queries.get_active_run_id()
        if run_id is None:
            return {"results": []}
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT doi, title, x, y,
                           (x - (SELECT x FROM papers WHERE run_id = %s AND lower(doi) = %s))^2 + 
                           (y - (SELECT y FROM papers WHERE run_id = %s AND lower(doi) = %s))^2 AS dist
                    FROM papers
                    WHERE run_id = %s AND lower(doi) != %s
                    ORDER BY dist
                    LIMIT %s
                """,
                    (run_id, center_doi.lower(), run_id, center_doi.lower(), run_id, center_doi.lower(), k),
                )
                results = [
                    {
                        "doi": doi,
                        "title": title or "",
                        "x": x,
                        "y": y,
                        "distance": float(dist) ** 0.5  # Square root for actual distance
                    }
                    for doi, title, x, y, dist in cur.fetchall()
                ]
        
        return {"results": results}


# Global service instance
search_service = SearchService()


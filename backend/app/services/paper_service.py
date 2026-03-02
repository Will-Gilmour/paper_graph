"""
Paper service - Business logic for paper/document operations.

Handles fetching paper data with optional Crossref API enrichment.
"""
import json
import sqlite3
import time
import re
import platform
from typing import Dict, List, Optional, Tuple
import requests

from backend.app.config.settings import settings, logger
from backend.app.database import queries


class CrossrefClient:
    """Client for Crossref API with local caching."""
    
    def __init__(self):
        """Initialize Crossref client with cache."""
        self.api_url = settings.crossref_api_url
        self.cache_path = settings.works_cache_path
        self._session: Optional[requests.Session] = None
        self._ensure_cache_db()
    
    def _ensure_cache_db(self):
        """Ensure the SQLite cache database exists."""
        with sqlite3.connect(self.cache_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS works (
                    doi TEXT PRIMARY KEY,
                    json TEXT NOT NULL,
                    ts   REAL NOT NULL
                )"""
            )
            conn.commit()
    
    def _get_session(self) -> requests.Session:
        """Get or create HTTP session with proper user agent."""
        if self._session is None:
            self._session = requests.Session()
            # Create safe user agent (ASCII only)
            ua = f"LitSearch/2.0 ({platform.system()} {platform.release()})"
            ua_safe = re.sub(r"[^\x20-\x7E]", "", ua)  # Remove non-ASCII
            self._session.headers["User-Agent"] = ua_safe
        return self._session
    
    def get_work(self, doi: str) -> Optional[Dict]:
        """
        Get work metadata from Crossref with caching.
        
        Args:
            doi: The DOI to look up
            
        Returns:
            Work metadata dictionary or None if not found
        """
        doi_lc = doi.lower()
        
        # Check cache first
        with sqlite3.connect(self.cache_path) as conn:
            cur = conn.execute("SELECT json FROM works WHERE doi=?", (doi_lc,))
            row = cur.fetchone()
            if row:
                return json.loads(row[0])
        
        # Fetch from API
        try:
            url = f"{self.api_url}/{doi_lc}"
            r = self._get_session().get(url, timeout=30)
            
            if r.status_code == 404:
                return None
            
            r.raise_for_status()
            work = r.json().get("message", {})
            
            # Cache the result
            with sqlite3.connect(self.cache_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO works (doi,json,ts) VALUES (?,?,?)",
                    (doi_lc, json.dumps(work), time.time()),
                )
                conn.commit()
            
            return work
            
        except requests.RequestException as e:
            logger.warning(f"Crossref API error for {doi}: {e}")
            return None


class PaperService:
    """Service for paper-related operations."""
    
    def __init__(self):
        """Initialize paper service with Crossref client."""
        self.crossref = CrossrefClient()
    
    def get_paper_by_doi(self, doi: str, enrich: bool = True) -> Optional[Dict]:
        """
        Get paper details by DOI with optional Crossref enrichment.
        
        Args:
            doi: The DOI to look up
            enrich: Whether to enrich with Crossref data
            
        Returns:
            Paper dictionary with metadata or None if not found
        """
        # Fetch from database
        row = queries.fetch_paper_by_doi(doi)
        
        if row is None:
            return None
        
        # Unpack database row
        (doi_db, title_db, authors_db, year_db, refs_db, 
         cited_db, cluster_id, fncr_db, x_coord, y_coord) = row
        
        # Normalize authors to list
        if isinstance(authors_db, list):
            authors_list = authors_db
        elif authors_db:
            try:
                authors_list = json.loads(authors_db) if isinstance(authors_db, str) else [authors_db]
                if not isinstance(authors_list, list):
                    authors_list = [authors_db]
            except Exception:
                authors_list = [authors_db]
        else:
            authors_list = []
        
        # Start with database data
        paper_data = {
            "doi": doi_db,
            "title": title_db,
            "authors": authors_list,
            "year": year_db,
            "references_count": refs_db,
            "cited_count": cited_db,
            "cluster": cluster_id,
            "fncr_count": fncr_db,
            "x": x_coord,
            "y": y_coord,
            "container_title": None,
            "publisher": None,
            "abstract": None,
        }
        
        # Try to enrich with Crossref if requested
        if enrich:
            try:
                work = self.crossref.get_work(doi_db)
                if work:
                    # Extract Crossref fields
                    container = work.get("container-title", [])
                    paper_data["container_title"] = container[0] if container else None
                    paper_data["publisher"] = work.get("publisher")
                    paper_data["abstract"] = work.get("abstract")
                    
                    # Prefer Crossref title if available
                    if work.get("title") and work["title"]:
                        paper_data["title"] = work["title"][0]
                    
                    # Prefer Crossref year if available
                    if work.get("published-print"):
                        date_parts = work["published-print"].get("date-parts", [[]])[0]
                        if date_parts:
                            paper_data["year"] = date_parts[0]
            except Exception as e:
                logger.warning(f"Failed to enrich {doi_db} with Crossref: {e}")
        
        return paper_data
    
    def get_ego_network(self, center_doi: str, depth: int = 1) -> Dict:
        """
        Get ego network around a center paper.
        
        Args:
            center_doi: The center paper DOI
            depth: Number of hops (1 or 2)
            
        Returns:
            Dictionary with nodes and edges
        """
        # Fetch ego network from database
        doi_list, edge_list = queries.fetch_ego_network(center_doi, depth)
        
        if not doi_list:
            return {"nodes": [], "edges": []}
        
        # Fetch node attributes for all papers in ego network
        nodes = []
        for doi in doi_list:
            row = queries.fetch_paper_by_doi(doi)
            if row:
                (doi_db, title_db, authors_db, year_db, refs_db, 
                 cited_db, cluster_id, fncr_db, x_coord, y_coord) = row
                
                nodes.append({
                    "doi": doi_db,
                    "title": title_db or "",
                    "x": x_coord,
                    "y": y_coord,
                    "year": year_db,
                    "cited_count": cited_db,
                    "cluster": cluster_id,
                    "fncr": fncr_db,
                })
        
        # Format edges
        edges = [{"source": src, "target": dst} for src, dst in edge_list]
        
        return {"nodes": nodes, "edges": edges}


# Global service instance
paper_service = PaperService()


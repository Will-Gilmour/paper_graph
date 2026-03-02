"""
Search-related API routes.

Endpoints for searching papers by title/DOI and finding nearby papers.
"""
from fastapi import APIRouter, Query as ApiQuery
from typing import Dict

from backend.app.services.search_service import search_service

router = APIRouter(prefix="", tags=["search"])


@router.get("/find", summary="Search for papers with combined title/author search and filters")
def search_papers(
    query: str = ApiQuery(None, description="Text or DOI fragment to search (legacy)"),
    field: str = ApiQuery("auto", description="Field to search: 'title', 'doi', or 'auto'"),
    top_k: int = ApiQuery(20, ge=1, le=100, description="Number of results to return"),
    cluster: int = ApiQuery(None, ge=0, description="Filter by cluster ID (optional, legacy)"),
    year_min: int = ApiQuery(None, ge=1900, le=2100, description="Minimum publication year (optional)"),
    year_max: int = ApiQuery(None, ge=1900, le=2100, description="Maximum publication year (optional)"),
    min_citations: int = ApiQuery(None, ge=0, description="Minimum citation count (optional)"),
    title: str = ApiQuery(None, description="Search in title field (optional)"),
    author: str = ApiQuery(None, description="Search in author field (optional)"),
    clusters: str = ApiQuery(None, description="Comma-separated cluster IDs (optional)")
) -> Dict:
    """
    Search for papers using fuzzy matching with multiple fallback strategies and filters.
    
    Search strategies (in order):
    1. DOI pattern matching (if query looks like DOI)
    2. Title substring match
    3. Trigram similarity (if available)
    4. Random sample (last resort)
    
    Then applies fuzzy scoring to rank results.
    
    Args:
        query: Search query string
        field: Field to search ("title", "doi", or "auto")
        top_k: Number of top results to return (1-100)
        cluster: Optional filter by cluster ID
        year_min: Optional minimum publication year
        year_max: Optional maximum publication year
        min_citations: Optional minimum citation count
        
    Returns:
        Dictionary with "results" list containing:
        - doi: Paper DOI
        - score: Match score (0-100)
        - title: Paper title
    """
    # Parse cluster IDs from comma-separated string
    cluster_ids_list = None
    if clusters:
        try:
            cluster_ids_list = [int(cid.strip()) for cid in clusters.split(',') if cid.strip()]
        except ValueError:
            pass
    
    results = search_service.search_papers(
        query, field, top_k, cluster, year_min, year_max, min_citations,
        title, author, cluster_ids_list
    )
    return results


@router.get("/find/nearby", summary="Find papers nearby a query paper")
def find_nearby_papers(
    query: str = ApiQuery(..., description="Text or DOI fragment"),
    k: int = ApiQuery(20, ge=1, le=100, description="Number of neighbours to return")
) -> Dict:
    """
    Find papers spatially near a query paper in the 2D layout.
    
    First resolves the query to a paper, then finds the k nearest
    neighbors based on Euclidean distance in the layout space.
    
    Args:
        query: DOI or title to search for
        k: Number of nearby papers to return (1-100)
        
    Returns:
        Dictionary with "results" list containing:
        - doi: Paper DOI
        - title: Paper title
        - x, y: Layout coordinates
        - distance: Euclidean distance from query paper
    """
    results = search_service.find_nearby_papers(query, k)
    return results


"""
Graph operation API routes.

Endpoints for graph-based computations like reading list generation.
"""
from fastapi import APIRouter, Query as ApiQuery, HTTPException
from typing import List, Dict, Optional

from backend.app.services.reading_list_service import reading_list_service

router = APIRouter(prefix="", tags=["graph"])


@router.get("/reading_list", summary="Generate reading list via spatial + citation filter")
def generate_reading_list(
    center: List[str] = ApiQuery(..., description="Seed DOIs"),
    k_region: int = ApiQuery(1000, ge=1, description="Spatial neighbors per seed"),
    depth_refs: int = ApiQuery(1, ge=0, le=2, description="Citation network depth"),
    year_from: Optional[int] = ApiQuery(None, ge=0, description="Minimum publication year"),
    min_cites: int = ApiQuery(4, ge=0, description="Minimum citation count"),
    weight_distance: float = ApiQuery(0.5, ge=0, le=1, description="Weight for distance vs citations"),
    top_n: int = ApiQuery(100, ge=1, le=1000, description="Number of papers to return"),
) -> Dict:
    """
    Generate a personalized reading list based on seed papers.
    
    Algorithm:
    1. Find spatial neighbors of seed papers in the layout
    2. Optionally expand with citation network (1-hop)
    3. Filter by year and citation count
    4. Score by weighted combination of distance and citations
    5. Return top N results
    
    Lower scores are better (closer + more cited).
    
    Args:
        center: List of seed DOIs (minimum 1)
        k_region: Number of spatial neighbors per seed (default: 1000)
        depth_refs: Citation network depth, 0-2 (default: 1)
        year_from: Filter for papers published after this year (optional)
        min_cites: Minimum citation count threshold (default: 4)
        weight_distance: Weight for distance in scoring, 0-1 (default: 0.5)
                        Higher = prioritize proximity, Lower = prioritize citations
        top_n: Number of papers to return, 1-1000 (default: 100)
        
    Returns:
        Dictionary with "reading_list" containing papers with:
        - doi: Paper DOI
        - title: Paper title
        - year: Publication year
        - citations: Citation count
        - cluster: Cluster ID
        - distance: Distance from centroid
        - score: Combined score (lower is better)
        - fncr: FNCR value
        
    Raises:
        HTTPException: 400 if no seed DOIs provided
        HTTPException: 404 if seed DOIs not found in graph
    """
    try:
        result = reading_list_service.generate_reading_list(
            center_dois=center,
            k_region=k_region,
            depth_refs=depth_refs,
            year_from=year_from,
            min_cites=min_cites,
            weight_distance=weight_distance,
            top_n=top_n
        )
        return result
    except ValueError as e:
        error_msg = str(e)
        if "not in graph" in error_msg:
            raise HTTPException(status_code=404, detail=error_msg)
        else:
            raise HTTPException(status_code=400, detail=error_msg)


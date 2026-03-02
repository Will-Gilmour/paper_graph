"""
Recommendations API routes for Papers of Interest.

Provides spatial and citation-based recommendations.
"""
from fastapi import APIRouter, Query as ApiQuery, Body
from typing import List, Dict

from backend.app.services.recommendations_service import recommendations_service

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post("/spatial", summary="Get spatially nearby papers based on collection centroid")
def get_spatial_recommendations(
    dois: List[str] = Body(..., description="List of DOIs in collection"),
    top_n: int = Body(20, ge=1, le=100, description="Number of recommendations to return"),
    min_distance: float = Body(0.0, ge=0.0, description="Minimum distance from centroid"),
    max_distance: float = Body(None, description="Maximum distance from centroid"),
    min_citations: int = Body(5, ge=0, description="Minimum citation count filter"),
    exclude_collection: bool = Body(True, description="Exclude papers already in collection"),
) -> Dict:
    """
    Find papers near the spatial centroid of your collection.
    
    Args:
        dois: Papers of Interest collection
        top_n: How many recommendations to return
        min_distance: Don't recommend papers too close to centroid
        max_distance: Don't recommend papers too far from centroid
        min_citations: Filter by citation count
        exclude_collection: Whether to exclude papers already in collection
        
    Returns:
        Dictionary with centroid coordinates and recommended papers
    """
    return recommendations_service.get_spatial_recommendations(
        dois=dois,
        top_n=top_n,
        min_distance=min_distance,
        max_distance=max_distance,
        min_citations=min_citations,
        exclude_collection=exclude_collection,
    )


@router.post("/bridges", summary="Find bridge papers connecting your collection")
def get_bridge_recommendations(
    dois: List[str] = Body(..., description="List of DOIs in collection"),
    top_n: int = Body(20, ge=1, le=100, description="Number of recommendations to return"),
    min_connections: int = Body(1, ge=1, description="Minimum papers in collection this must cite/be cited by"),
    max_hops: int = Body(2, ge=1, le=3, description="Maximum citation path length"),
) -> Dict:
    """
    Find papers that connect multiple papers in your collection via citations.
    
    Args:
        dois: Papers of Interest collection
        top_n: How many recommendations to return
        min_connections: Minimum number of collection papers a bridge must connect
        max_hops: Maximum citation path distance (1=direct, 2=one intermediary)
        
    Returns:
        Dictionary with bridge papers and connection counts
    """
    return recommendations_service.get_bridge_recommendations(
        dois=dois,
        top_n=top_n,
        min_connections=min_connections,
        max_hops=max_hops,
    )


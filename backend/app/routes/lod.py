"""
Level of Detail (LOD) API routes.

Provides endpoints for fetching additional nodes based on viewport and zoom level.
"""
from fastapi import APIRouter, Query as ApiQuery
from typing import Dict, List

from backend.app.services.lod_service import lod_service

router = APIRouter(prefix="/lod", tags=["lod"])


@router.get("/nodes", summary="Get nodes in viewport with dynamic citation threshold")
def get_nodes_in_viewport(
    x_min: float = ApiQuery(..., description="Viewport left boundary"),
    x_max: float = ApiQuery(..., description="Viewport right boundary"),
    y_min: float = ApiQuery(..., description="Viewport bottom boundary"),
    y_max: float = ApiQuery(..., description="Viewport top boundary"),
    min_citations: int = ApiQuery(0, ge=0, description="Minimum citation threshold"),
    limit: int = ApiQuery(1000, gt=0, le=5000, description="Max nodes to return"),
) -> Dict:
    """
    Get nodes within a viewport bounding box for level-of-detail loading.
    
    Args:
        x_min, x_max, y_min, y_max: Viewport coordinates
        min_citations: Citation threshold (lower when zoomed in)
        limit: Maximum nodes to return
        
    Returns:
        Dictionary with nodes and edges between them
    """
    return lod_service.get_nodes_in_viewport(
        x_min, x_max, y_min, y_max,
        min_citations, limit
    )






"""
Paper-related API routes.

Endpoints for fetching paper metadata and ego networks.
"""
from fastapi import APIRouter, HTTPException, Query as ApiQuery, Path as ApiPath
from fastapi.responses import JSONResponse
from typing import Dict

from backend.app.services.paper_service import paper_service

router = APIRouter(prefix="", tags=["papers"])


@router.get("/paper/{doi:path}", summary="Get full metadata for one paper")
def get_paper(doi: str = ApiPath(..., description="DOI of the paper")) -> JSONResponse:
    """
    Get detailed paper metadata with optional Crossref enrichment.
    
    Args:
        doi: The DOI to look up (case-insensitive)
        
    Returns:
        Paper metadata including database fields and Crossref enrichment
        
    Raises:
        HTTPException: 404 if DOI not found in graph
    """
    paper = paper_service.get_paper_by_doi(doi, enrich=True)
    
    if paper is None:
        raise HTTPException(status_code=404, detail="DOI not in graph")
    
    # Disable caching to ensure correct details for the active graph
    return JSONResponse(
        content=paper,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@router.get("/ego", summary="Get ego subgraph around a DOI")
def get_ego_network(
    doi: str = ApiQuery(..., description="DOI of the centre node"),
    depth: int = ApiQuery(1, ge=0, description="Hop depth (1 or 2)")
) -> Dict:
    """
    Build ego network around a center paper.
    
    Fetches all papers within `depth` hops of the center paper,
    along with edges between them.
    
    Args:
        doi: Center paper DOI
        depth: Number of hops (1 or 2)
        
    Returns:
        Dictionary with "nodes" and "edges" lists
    """
    try:
        ego_data = paper_service.get_ego_network(doi, depth)
        return ego_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


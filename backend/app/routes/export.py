"""
Export-related API routes.

Endpoints for exporting graph data in various formats.
"""
from fastapi import APIRouter, Query as ApiQuery
from fastapi.responses import FileResponse, StreamingResponse
from typing import Dict, Optional

from backend.app.services.export_service import export_service

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/ndjson/initial/meta", summary="Get counts for initial NDJSON subset")
def get_initial_meta(
    top_n: Optional[int] = ApiQuery(None, ge=1, description="Top N nodes by citation count (optional)")
) -> Dict[str, int]:
    """
    Get metadata about the initial NDJSON file (highly-cited papers).
    
    Args:
        top_n: Optional number of top papers by citation count
    
    Returns:
        Dictionary with nodes_total and edges_total counts
    """
    return export_service.get_initial_meta(top_n=top_n)


@router.get("/initial.ndjson", response_class=FileResponse, summary="Download initial node/edge subset as NDJSON")
def download_initial_ndjson(
    top_n: Optional[int] = ApiQuery(None, ge=1, description="Top N nodes by citation count (optional, overrides default threshold)")
):
    """
    Download the initial NDJSON file containing highly-cited papers.
    
    By default, includes papers with > 25 citations and all edges between them.
    If top_n is specified, returns top N papers by citation count instead.
    Formatted as newline-delimited JSON.
    
    Args:
        top_n: Optional number of top papers by citation count to include
    
    Returns:
        NDJSON file response
    """
    path = export_service.get_initial_ndjson_path(top_n=top_n)
    return FileResponse(
        path=str(path),
        media_type="application/x-ndjson",
        filename="initial.ndjson",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


@router.get("/ndjson", summary="Stream full NDJSON export of all nodes and edges")
def stream_full_ndjson():
    """
    Stream the complete graph as NDJSON (all nodes, then all edges).
    
    This is a streaming response for large datasets. Nodes come first,
    then edges.
    
    Returns:
        Streaming NDJSON response
    """
    return StreamingResponse(
        export_service.stream_full_ndjson(),
        media_type="application/x-ndjson"
    )


@router.get("/json", summary="Get paginated JSON export of nodes and edges with filters")
def export_json(
    nodes_offset: int = ApiQuery(0, ge=0, description="Number of nodes to skip"),
    nodes_limit: int = ApiQuery(1000, gt=0, le=10000, description="Maximum nodes to return"),
    edges_offset: int = ApiQuery(0, ge=0, description="Number of edges to skip"),
    edges_limit: int = ApiQuery(1000, gt=0, le=10000, description="Maximum edges to return"),
    year_min: int = ApiQuery(None, ge=1900, le=2100, description="Minimum publication year (optional)"),
    year_max: int = ApiQuery(None, ge=1900, le=2100, description="Maximum publication year (optional)"),
    min_citations: int = ApiQuery(None, ge=0, description="Minimum citation count (optional)"),
) -> Dict:
    """
    Get paginated export of graph data as JSON with optional filters.
    
    Useful for building the graph incrementally or fetching specific portions.
    
    Args:
        nodes_offset: Number of nodes to skip
        nodes_limit: Maximum nodes to return (1-10000)
        edges_offset: Number of edges to skip
        edges_limit: Maximum edges to return (1-10000)
        year_min: Optional minimum publication year
        year_max: Optional maximum publication year
        min_citations: Optional minimum citation count
        
    Returns:
        Dictionary with:
        - nodes_total: Total number of nodes matching filters
        - edges_total: Total number of edges in database
        - nodes: List of node objects (paginated and filtered)
        - edges: List of edge objects (paginated)
        - meta: Pagination metadata
    """
    return export_service.get_paginated_export(
        nodes_offset, nodes_limit,
        edges_offset, edges_limit,
        year_min, year_max, min_citations
    )


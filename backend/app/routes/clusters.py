"""
Cluster-related API routes.

Endpoints for fetching cluster information and details.
"""
from fastapi import APIRouter, HTTPException, Path as ApiPath
from typing import List, Dict

from backend.app.services.cluster_service import cluster_service

router = APIRouter(prefix="", tags=["clusters"])


@router.get("/clusters", summary="List all clusters with labels & centroids")
def get_clusters() -> List[Dict]:
    """
    Get all clusters with metadata and top sub-clusters.
    
    Returns:
        List of cluster dictionaries sorted by size (descending)
        
    Raises:
        HTTPException: 500 if no clusters found in database
    """
    try:
        clusters = cluster_service.get_all_clusters()
        return clusters
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cluster/{cid}", summary="Get all nodes and edges in one cluster")
def get_cluster_detail(cid: int = ApiPath(..., ge=0, description="Cluster ID")) -> Dict:
    """
    Get detailed information about a specific cluster.
    
    Args:
        cid: Cluster ID (must be >= 0)
        
    Returns:
        Dictionary with cluster id, label, nodes, and edges
        
    Raises:
        HTTPException: 404 if cluster not found
    """
    cluster_data = cluster_service.get_cluster_detail(cid)
    
    if cluster_data is None:
        raise HTTPException(status_code=404, detail=f"Cluster {cid} not found")
    
    return cluster_data


@router.get("/labels/parent", summary="Get parent cluster titles")
def get_parent_labels() -> Dict[str, str]:
    """
    Get mapping of cluster IDs to their display names.
    
    Returns:
        Dictionary mapping cluster IDs (as strings) to labels
    """
    return cluster_service.get_parent_labels()


@router.get("/labels/sub", summary="Get sub-cluster titles")
def get_sub_labels() -> Dict[str, str]:
    """
    Get mapping of sub-cluster IDs to their display names.
    
    Returns:
        Dictionary mapping "cluster:sub" IDs to labels
    """
    return cluster_service.get_sub_labels()


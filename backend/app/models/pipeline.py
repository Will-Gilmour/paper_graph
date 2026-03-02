"""Data models for pipeline management."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class PipelineBuildRequest(BaseModel):
    """Request to build a new graph."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Graph name")
    description: Optional[str] = Field(None, description="Description of this graph")
    
    # Seeds
    seed_dois: List[str] = Field(..., min_items=1, description="Seed DOIs to start crawling")
    
    # Crawling options
    max_depth: int = Field(1, ge=1, le=3, description="Citation crawl depth (1-3)")
    include_citers: bool = Field(True, description="Include papers that cite the seeds")
    max_citers: int = Field(50, ge=0, le=200, description="Max citers per paper")
    
    # Layout options
    use_gpu: bool = Field(True, description="Use GPU for layout (faster)")
    layout_iterations: int = Field(20000, ge=1000, le=50000, description="ForceAtlas2 iterations")
    
    # Clustering options
    clustering_resolution: float = Field(1.0, ge=0.1, le=5.0, description="Louvain resolution")
    sub_clustering_resolution: float = Field(1.0, ge=0.1, le=5.0, description="Sub-cluster resolution")
    
    # Labeling options
    llm_batch_size: int = Field(8, ge=1, le=32, description="LLM batch size")
    
    # API credentials
    mailto: Optional[str] = Field("your-email@example.com", description="Email for Crossref/OpenAlex APIs")
    
    # Output options
    auto_export: bool = Field(True, description="Export to PostgreSQL automatically")
    set_active: bool = Field(False, description="Set as active graph after completion")
    
    # Metadata
    created_by: Optional[str] = Field(None, description="User who created this build")


class PipelineRunStatus(BaseModel):
    """Status of a pipeline run."""
    
    id: int
    name: str
    description: Optional[str]
    status: str  # pending, running, completed, failed, cancelled
    
    seed_dois: List[str]
    
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    output_path: Optional[str]
    error_message: Optional[str]
    
    nodes_count: Optional[int]
    edges_count: Optional[int]
    clusters_count: Optional[int]
    
    is_active: bool
    created_at: datetime
    created_by: Optional[str]
    
    class Config:
        from_attributes = True


class PipelineRunDetail(PipelineRunStatus):
    """Detailed pipeline run information including config."""
    
    config: Dict[str, Any]  # Full configuration JSON


class PipelineRunList(BaseModel):
    """List of pipeline runs."""
    
    runs: List[PipelineRunStatus]
    total: int
    active_run_id: Optional[int]


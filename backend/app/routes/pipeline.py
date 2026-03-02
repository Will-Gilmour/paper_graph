"""API routes for pipeline management."""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional
import os
import httpx

from backend.app.models.pipeline import (
    PipelineBuildRequest,
    PipelineRunStatus,
    PipelineRunDetail,
    PipelineRunList,
)
from backend.app.services.pipeline_service import PipelineService

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

# Initialize service
DB_URL = os.getenv("DATABASE_URL", "postgresql://pg:secret@localhost:5432/litsearch")
PIPELINE_SERVICE_URL = os.getenv("PIPELINE_SERVICE_URL", "http://localhost:8001")
pipeline_service = PipelineService(DB_URL)


async def trigger_pipeline_execution(run_id: int):
    """
    Trigger pipeline execution (local or containerized based on config).
    
    In hybrid mode, this executes the pipeline locally with GPU access.
    """
    import asyncio
    
    execution_mode = os.getenv("PIPELINE_EXECUTION_MODE", "local")
    
    if execution_mode == "local":
        # Execute locally (hybrid mode)
        await execute_pipeline_local(run_id)
    else:
        # Execute in container (microservice mode)
        await execute_pipeline_container(run_id)


async def execute_pipeline_local(run_id: int):
    """Execute pipeline locally with GPU."""
    from backend.app.services.local_pipeline_executor import LocalPipelineExecutor
    import asyncio
    
    try:
        # Get configuration
        run = pipeline_service.get_run_status(run_id)
        if not run:
            raise ValueError(f"Run {run_id} not found")
        
        # Update status to running
        pipeline_service.start_build(run_id)
        
        # Execute in thread pool (blocking operation)
        executor = LocalPipelineExecutor()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            executor.execute_build,
            run_id,
            run.config,
            run.seed_dois
        )
        
        # TODO: Get actual statistics from result
        # For now, mark as completed (stats will be populated later)
        pipeline_service.complete_build(
            run_id=run_id,
            output_path=result["output_dir"],
            nodes_count=0,  # Will be updated when data is loaded
            edges_count=0,
            clusters_count=0,
        )
        
        # Set as active if requested
        if run.config.get("set_active", False):
            pipeline_service.set_active_graph(run_id)
            
    except Exception as e:
        pipeline_service.fail_build(run_id, str(e))
        raise


async def execute_pipeline_container(run_id: int):
    """Execute pipeline in Docker container (microservice mode)."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{PIPELINE_SERVICE_URL}/builds/{run_id}/execute"
            )
            
            if response.status_code != 200:
                raise Exception(f"Pipeline service returned {response.status_code}")
    
    except Exception as e:
        pipeline_service.fail_build(run_id, f"Failed to trigger pipeline service: {e}")
        raise


@router.post("/builds", response_model=dict)
async def create_build(
    request: PipelineBuildRequest,
    background_tasks: BackgroundTasks,
):
    """
    Create and start a new pipeline build.
    
    This creates a record in the database with status='pending'.
    The dedicated pipeline worker will pick it up automatically.
    """
    # Create the build record with status='pending'
    run_id = pipeline_service.create_build(request)
    
    # NOTE: We don't trigger execution here anymore!
    # The dedicated pipeline worker polls the database for pending builds.
    # This keeps the backend lightweight (no PyTorch/GPU dependencies needed).
    
    return {
        "id": run_id,
        "message": "Pipeline build queued - worker will pick it up automatically",
        "status": "pending"
    }


@router.get("/builds", response_model=PipelineRunList)
async def list_builds(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
):
    """List all pipeline builds."""
    return pipeline_service.list_runs(limit=limit, offset=offset, status=status)


@router.get("/builds/{run_id}", response_model=PipelineRunDetail)
async def get_build_status(run_id: int):
    """Get status of a specific pipeline build."""
    run = pipeline_service.get_run_status(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return run


@router.post("/builds/{run_id}/activate", response_model=dict)
async def activate_build(run_id: int):
    """Set a completed build as the active graph."""
    run = pipeline_service.get_run_status(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    
    if run.status != "completed":
        raise HTTPException(
            status_code=400,
            detail="Can only activate completed builds"
        )
    
    pipeline_service.set_active_graph(run_id)
    
    return {"message": "Graph activated", "id": run_id}


@router.get("/active", response_model=Optional[PipelineRunStatus])
async def get_active_graph():
    """Get the currently active graph."""
    return pipeline_service.get_active_run()


@router.post("/builds/{run_id}/cancel", response_model=dict)
async def cancel_build(run_id: int):
    """Cancel a running or pending build."""
    run = pipeline_service.get_run_status(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    
    if run.status not in ["pending", "running"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel a build with status '{run.status}'"
        )
    
    # Mark as cancelled
    pipeline_service.fail_build(run_id, "Cancelled by user")
    
    # Update status to cancelled instead of failed
    import psycopg2
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute(
        "UPDATE pipeline_runs SET status = 'cancelled' WHERE id = %s",
        (run_id,)
    )
    conn.commit()
    cur.close()
    conn.close()
    
    return {"message": "Build cancelled", "id": run_id}


@router.delete("/builds/{run_id}", response_model=dict)
async def delete_build(run_id: int):
    """Delete a pipeline build."""
    run = pipeline_service.get_run_status(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    
    # Don't allow deleting active builds
    active = pipeline_service.get_active_run()
    if active and active.id == run_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete the active graph. Activate a different graph first."
        )
    
    # Allow deleting failed, cancelled, or completed builds
    # Only prevent deleting currently running builds to avoid confusion
    if run.status == "running":
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a build that is currently running. Cancel it first, then delete."
        )
    
    pipeline_service.delete_build(run_id)
    
    return {"message": "Build deleted", "id": run_id}


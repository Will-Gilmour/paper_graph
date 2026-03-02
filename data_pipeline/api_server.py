"""
Data Pipeline API Server

Separate service for executing pipeline builds.
Communicates with main backend via HTTP or database.
"""

import os
import asyncio
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor

from data_pipeline.config import PipelineConfig
from data_pipeline.workflow import PipelineOrchestrator
from data_pipeline.utils.logging import setup_logging, get_logger

# Setup logging
setup_logging(verbose=True)
logger = get_logger("api_server")

# FastAPI app
app = FastAPI(
    title="LitSearch Data Pipeline API",
    description="Microservice for building citation graphs",
    version="2.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://pg:secret@postgres:5432/litsearch")


class PipelineRunner:
    """Runs pipeline builds and updates database status."""
    
    @staticmethod
    async def run_build(run_id: int):
        """Execute a pipeline build."""
        logger.info(f"Starting pipeline build {run_id}")
        
        try:
            # Get configuration from database
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT config, seed_dois FROM pipeline_runs WHERE id = %s
                    """, (run_id,))
                    
                    row = cur.fetchone()
                    if not row:
                        raise ValueError(f"Run {run_id} not found")
                    
                    config_data = row['config']
                    seed_dois = row['seed_dois']
            
            # Update status to running
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE pipeline_runs
                        SET status = 'running', started_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (run_id,))
                    conn.commit()
            
            # Build pipeline config
            output_dir = Path(f"/app/pipeline_outputs/run_{run_id}")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            pipeline_config = PipelineConfig(
                seed_dois=seed_dois,
                max_depth=config_data.get('max_depth', 1),
                output_dir=output_dir,
                verbose=True,
            )
            
            # Apply all settings from config
            pipeline_config.layout.use_gpu = config_data.get('use_gpu', False)
            pipeline_config.layout.fa2_iterations = config_data.get('layout_iterations', 2000)
            pipeline_config.clustering.louvain_resolution = config_data.get('clustering_resolution', 1.0)
            pipeline_config.clustering.sub_resolution = config_data.get('sub_clustering_resolution', 1.0)
            pipeline_config.labeling.batch_size = config_data.get('llm_batch_size', 8)
            pipeline_config.api.max_workers = 8
            pipeline_config.export.database_url = DATABASE_URL
            
            # Run pipeline
            logger.info(f"Running pipeline with config: {pipeline_config.model_dump_json()}")
            orchestrator = PipelineOrchestrator(pipeline_config)
            orchestrator.run_full_pipeline(seed_dois)
            
            # Get statistics
            graph_data = orchestrator._graph_builder.get_graph_data()
            
            # Update database with success
            output_path = str(output_dir / "graph.pkl.gz")
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE pipeline_runs
                        SET status = 'completed',
                            completed_at = CURRENT_TIMESTAMP,
                            output_path = %s,
                            nodes_count = %s,
                            edges_count = %s,
                            clusters_count = %s
                        WHERE id = %s
                    """, (
                        output_path,
                        graph_data.num_nodes(),
                        graph_data.num_edges(),
                        graph_data.num_clusters(),
                        run_id
                    ))
                    
                    # Set as active if requested
                    if config_data.get('set_active', False):
                        cur.execute("UPDATE pipeline_runs SET is_active = FALSE")
                        cur.execute("""
                            UPDATE pipeline_runs SET is_active = TRUE WHERE id = %s
                        """, (run_id,))
                    
                    conn.commit()
            
            logger.info(f"Pipeline build {run_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Pipeline build {run_id} failed: {e}", exc_info=True)
            
            # Update database with failure
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE pipeline_runs
                        SET status = 'failed',
                            completed_at = CURRENT_TIMESTAMP,
                            error_message = %s
                        WHERE id = %s
                    """, (str(e), run_id))
                    conn.commit()


runner = PipelineRunner()


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "service": "LitSearch Data Pipeline",
        "version": "2.0.0",
        "status": "healthy"
    }


@app.get("/health")
def health():
    """Health check."""
    return {"status": "healthy"}


@app.post("/builds/{run_id}/execute")
async def execute_build(run_id: int, background_tasks: BackgroundTasks):
    """
    Execute a pipeline build.
    
    This is called by the main backend when a build is created.
    """
    logger.info(f"Received request to execute build {run_id}")
    
    # Verify run exists
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, status FROM pipeline_runs WHERE id = %s
                """, (run_id,))
                row = cur.fetchone()
                
                if not row:
                    raise HTTPException(status_code=404, detail="Run not found")
                
                if row[1] != 'pending':
                    raise HTTPException(
                        status_code=400,
                        detail=f"Run is already {row[1]}"
                    )
    except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    
    # Start build in background
    background_tasks.add_task(runner.run_build, run_id)
    
    return {
        "id": run_id,
        "status": "started",
        "message": "Pipeline build started"
    }


@app.get("/builds/{run_id}/status")
async def get_build_status(run_id: int):
    """Get status of a pipeline build."""
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, name, status, started_at, completed_at,
                           nodes_count, edges_count, clusters_count,
                           error_message
                    FROM pipeline_runs
                    WHERE id = %s
                """, (run_id,))
                
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Run not found")
                
                return dict(row)
    except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Database error")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

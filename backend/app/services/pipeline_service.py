"""Service for managing pipeline builds."""

import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

from backend.app.models.pipeline import (
    PipelineBuildRequest,
    PipelineRunStatus,
    PipelineRunDetail,
    PipelineRunList,
)


class PipelineService:
    """Service for pipeline build management."""
    
    def __init__(self, db_connection_string: str):
        """Initialize service."""
        self.db_url = db_connection_string
    
    def create_build(self, request: PipelineBuildRequest) -> int:
        """
        Create a new pipeline build.
        
        Args:
            request: Build configuration
        
        Returns:
            Pipeline run ID
        """
        # Convert request to config dict
        config = request.model_dump()
        
        with psycopg2.connect(self.db_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO pipeline_runs (
                        name, description, config, seed_dois,
                        status, created_by
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    request.name,
                    request.description,
                    json.dumps(config),
                    request.seed_dois,
                    'pending',
                    request.created_by,
                ))
                
                run_id = cur.fetchone()[0]
                conn.commit()
        
        return run_id
    
    def start_build(self, run_id: int):
        """
        Start a pipeline build (update status).
        
        This marks the build as running and sets started_at.
        The actual execution happens elsewhere.
        """
        with psycopg2.connect(self.db_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE pipeline_runs
                    SET status = 'running',
                        started_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (run_id,))
                conn.commit()
    
    def complete_build(
        self,
        run_id: int,
        output_path: str,
        nodes_count: int,
        edges_count: int,
        clusters_count: int,
    ):
        """Mark build as completed with statistics."""
        with psycopg2.connect(self.db_url) as conn:
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
                """, (output_path, nodes_count, edges_count, clusters_count, run_id))
                conn.commit()
    
    def fail_build(self, run_id: int, error_message: str):
        """Mark build as failed."""
        with psycopg2.connect(self.db_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE pipeline_runs
                    SET status = 'failed',
                        completed_at = CURRENT_TIMESTAMP,
                        error_message = %s
                    WHERE id = %s
                """, (error_message, run_id))
                conn.commit()
    
    def delete_build(self, run_id: int):
        """Delete a pipeline build (must not be active)."""
        with psycopg2.connect(self.db_url) as conn:
            with conn.cursor() as cur:
                # Check if this is the active graph
                cur.execute(
                    "SELECT is_active FROM pipeline_runs WHERE id = %s",
                    (run_id,)
                )
                result = cur.fetchone()
                
                if not result:
                    raise ValueError(f"Build {run_id} not found")
                
                if result[0]:
                    raise ValueError("Cannot delete the active graph")
                
                # Delete the build
                cur.execute("DELETE FROM pipeline_runs WHERE id = %s", (run_id,))
                conn.commit()
    
    def set_active_graph(self, run_id: int):
        """
        Set a completed build as the active graph.
        
        This deactivates all other graphs and activates this one,
        then rebuilds the NDJSON cache for the new active graph.
        """
        with psycopg2.connect(self.db_url) as conn:
            with conn.cursor() as cur:
                # Deactivate all graphs
                cur.execute("UPDATE pipeline_runs SET is_active = FALSE")
                
                # Activate this one
                cur.execute("""
                    UPDATE pipeline_runs
                    SET is_active = TRUE
                    WHERE id = %s AND status = 'completed'
                """, (run_id,))
                
                conn.commit()
        
        # Rebuild NDJSON cache and reload labels for the newly activated graph
        try:
            from backend.app.services.export_service import export_service
            from backend.app.services.cluster_service import cluster_service
            from backend.app.config.settings import logger
            
            logger.info(f"Rebuilding NDJSON cache for activated graph (run_id={run_id})")
            export_service.build_initial_ndjson(run_id=run_id)
            logger.info(f"NDJSON cache rebuilt successfully for run_id={run_id}")
            
            logger.info(f"Reloading cluster labels for run_id={run_id}")
            cluster_service.reload_labels()
            logger.info(f"Cluster labels reloaded successfully")
        except Exception as e:
            from backend.app.config.settings import logger
            logger.error(f"Failed to rebuild NDJSON cache or reload labels after activating graph {run_id}: {e}")
    
    def get_run_status(self, run_id: int) -> Optional[PipelineRunDetail]:
        """Get detailed status of a pipeline run."""
        with psycopg2.connect(self.db_url) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, name, description, config, seed_dois,
                           status, started_at, completed_at,
                           output_path, error_message,
                           nodes_count, edges_count, clusters_count,
                           is_active, created_at, created_by
                    FROM pipeline_runs
                    WHERE id = %s
                """, (run_id,))
                
                row = cur.fetchone()
                if row:
                    return PipelineRunDetail(**row)
                return None
    
    def list_runs(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None
    ) -> PipelineRunList:
        """List pipeline runs."""
        with psycopg2.connect(self.db_url) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Build query
                where_clause = ""
                params = []
                if status:
                    where_clause = "WHERE status = %s"
                    params.append(status)
                
                # Get runs
                cur.execute(f"""
                    SELECT id, name, description, seed_dois,
                           status, started_at, completed_at,
                           output_path, error_message,
                           nodes_count, edges_count, clusters_count,
                           is_active, created_at, created_by
                    FROM pipeline_runs
                    {where_clause}
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """, params + [limit, offset])
                
                runs = [PipelineRunStatus(**row) for row in cur.fetchall()]
                
                # Get total count
                cur.execute(f"""
                    SELECT COUNT(*) as count FROM pipeline_runs {where_clause}
                """, params)
                total = cur.fetchone()['count']
                
                # Get active run ID
                cur.execute("""
                    SELECT id FROM pipeline_runs WHERE is_active = TRUE
                """)
                active_row = cur.fetchone()
                active_id = active_row['id'] if active_row else None
        
        return PipelineRunList(
            runs=runs,
            total=total,
            active_run_id=active_id
        )
    
    def get_active_run(self) -> Optional[PipelineRunStatus]:
        """Get the currently active graph."""
        with psycopg2.connect(self.db_url) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, name, description, seed_dois,
                           status, started_at, completed_at,
                           output_path, error_message,
                           nodes_count, edges_count, clusters_count,
                           is_active, created_at, created_by
                    FROM pipeline_runs
                    WHERE is_active = TRUE
                """)
                
                row = cur.fetchone()
                if row:
                    return PipelineRunStatus(**row)
                return None


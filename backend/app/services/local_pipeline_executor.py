"""
Local pipeline executor for hybrid Docker setup.

Executes data_pipeline on the host machine (with GPU access)
while the form/tracking runs in Docker.
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, Any

import logging

logger = logging.getLogger("services.local_pipeline_executor")


class LocalPipelineExecutor:
    """Executes pipeline builds on the local machine."""
    
    def __init__(self, python_path: str = "python"):
        """
        Initialize executor.
        
        Args:
            python_path: Path to Python executable on host
        """
        self.python_path = python_path
        self.workspace_root = Path("/workspace") if Path("/workspace").exists() else Path(".")
    
    def execute_build(self, run_id: int, config: Dict[str, Any], seed_dois: list[str]):
        """
        Execute a pipeline build locally.
        
        Args:
            run_id: Build ID
            config: Build configuration
            seed_dois: Seed DOIs
        """
        logger.info(f"Executing build {run_id} locally")
        
        # Create output directory
        output_dir = Path(f"./pipeline_outputs/run_{run_id}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Build command
        cmd = [
            self.python_path,
            "-m", "data_pipeline.cli.main",
            "run-all"
        ]
        
        # Add seeds
        for doi in seed_dois:
            cmd.extend(["--seed-doi", doi])
        
        # Add options
        cmd.extend([
            "--output-dir", str(output_dir),
            "--max-depth", str(config.get("max_depth", 1)),
            "--db-url", os.getenv("DATABASE_URL", "postgresql://pg:secret@localhost:5432/litsearch"),
        ])
        
        if config.get("use_gpu", True):
            cmd.append("--gpu")
        else:
            cmd.append("--no-gpu")
        
        if config.get("verbose", True):
            cmd.append("--verbose")
        
        logger.info(f"Executing command: {' '.join(cmd)}")
        
        # Execute
        try:
            result = subprocess.run(
                cmd,
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=3600 * 6,  # 6 hour timeout
            )
            
            if result.returncode != 0:
                error_msg = f"Pipeline failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"Build {run_id} completed successfully")
            logger.debug(f"Output: {result.stdout}")
            
            return {
                "success": True,
                "output_dir": str(output_dir),
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
            
        except subprocess.TimeoutExpired:
            raise Exception("Pipeline execution timed out (6 hours)")
        except Exception as e:
            raise Exception(f"Pipeline execution failed: {e}")


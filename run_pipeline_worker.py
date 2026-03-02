"""
Local Pipeline Worker
Processes pending pipeline builds with GPU access

Run this script on your local machine to execute pipeline builds:
    python run_pipeline_worker.py

This script:
1. Polls the database for pending builds
2. Executes them locally with GPU access
3. Updates the database with results
"""

import sys
import time
import psycopg2
import json
from datetime import datetime
from pathlib import Path

# Add data_pipeline to path
sys.path.insert(0, str(Path(__file__).parent))

from data_pipeline.workflow.orchestrator import PipelineOrchestrator
from data_pipeline.config.settings import PipelineConfig

import os
import socket

# Auto-detect environment: WSL/host uses localhost, Docker containers use postgres
def detect_db_host():
    """Detect the correct database host based on environment."""
    # Check if DB_HOST is explicitly set
    if "DB_HOST" in os.environ:
        return os.environ["DB_HOST"]
    
    # Try to resolve 'postgres' - if it works, we're in Docker network
    try:
        socket.gethostbyname("postgres")
        return "postgres"  # Running in Docker network
    except socket.gaierror:
        return "localhost"  # Running on host/WSL

DB_HOST = detect_db_host()
DB_USER = os.getenv("DB_USER", "pg")
DB_PASSWORD = os.getenv("DB_PASSWORD", "secret")
DB_NAME = os.getenv("DB_NAME", "litsearch")
DB_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"
)

print(f"🔌 Database host auto-detected: {DB_HOST}")
print(f"🔗 Connection string: postgresql://{DB_USER}:***@{DB_HOST}:5432/{DB_NAME}")
print()

def get_pending_builds():
    """Get all pending builds from database."""
    try:
        conn = psycopg2.connect(DB_URL)
        return _fetch_builds(conn)
    except psycopg2.OperationalError as e:
        print(f"❌ Database connection failed: {e}")
        print()
        print("🔧 Troubleshooting:")
        print(f"   - Check Docker containers are running: docker ps")
        print(f"   - Test connection: telnet {DB_HOST} 5432")
        if DB_HOST == "postgres":
            print(f"   - Try setting: export DB_HOST=localhost")
        raise

def _fetch_builds(conn):
    """Fetch pending builds from database."""
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, name, config, seed_dois, created_at 
        FROM pipeline_runs 
        WHERE status = 'pending' 
        ORDER BY created_at ASC
    """)
    
    builds = []
    for row in cur.fetchall():
        builds.append({
            'id': row[0],
            'name': row[1],
            'config': json.loads(row[2]) if isinstance(row[2], str) else row[2],
            'seed_dois': row[3] if row[3] else [],
            'created_at': row[4]
        })
    
    cur.close()
    conn.close()
    return builds

def update_build_status(run_id, status, error_message=None):
    """Update build status in database."""
    print(f"📝 Updating build {run_id} status to: {status}")
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    try:
        if status == 'running':
            cur.execute("""
                UPDATE pipeline_runs
                SET status = 'running', started_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (run_id,))
        elif status == 'completed':
            cur.execute("""
                UPDATE pipeline_runs
                SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (run_id,))
        elif status == 'failed':
            cur.execute("""
                UPDATE pipeline_runs
                SET status = 'failed',
                    completed_at = CURRENT_TIMESTAMP,
                    error_message = %s
                WHERE id = %s
            """, (error_message, run_id))
        
        conn.commit()
    finally:
        cur.close()
        conn.close()


def update_build_stats(run_id, output_path, nodes_count, edges_count, clusters_count):
    """Update build statistics after completion."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    try:
        cur.execute("""
            UPDATE pipeline_runs
            SET output_path = %s,
                nodes_count = %s,
                edges_count = %s,
                clusters_count = %s
            WHERE id = %s
        """, (output_path, nodes_count, edges_count, clusters_count, run_id))
        conn.commit()
    finally:
        cur.close()
        conn.close()


def check_if_cancelled(run_id):
    """Check if build has been cancelled."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("SELECT status FROM pipeline_runs WHERE id = %s", (run_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    
    if result and result[0] == 'cancelled':
        return True
    return False


def execute_build(build):
    """Execute a pipeline build."""
    run_id = build['id']
    config_dict = build['config']
    
    print(f"\n{'='*60}")
    print(f"🚀 Starting Build: {build['name']} (ID: {run_id})")
    print(f"{'='*60}\n")
    
    # Check if already cancelled before starting
    if check_if_cancelled(run_id):
        print("⚠️  Build was cancelled before execution started")
        return
    
    # Update status to running
    update_build_status(run_id, 'running')
    print("✅ Status updated to 'running'")
    
    try:
        # Create pipeline config with proper nested structure
        from data_pipeline.config.settings import (
            APIConfig, LayoutConfig, ClusteringConfig, 
            EmbeddingConfig, LabelingConfig, ExportConfig
        )
        
        config = PipelineConfig(
            seed_dois=build['seed_dois'],
            max_depth=config_dict.get('max_depth', 2),
            api=APIConfig(
                mailto=config_dict.get('mailto', os.getenv("PIPELINE_API_MAILTO", "your-email@example.com")),
            ),
            layout=LayoutConfig(
                use_gpu=config_dict.get('use_gpu', True),
                fa2_iterations=config_dict.get('layout_iterations', 20000),
            ),
            clustering=ClusteringConfig(
                louvain_resolution=config_dict.get('clustering_resolution', 1.0),
                sub_resolution=config_dict.get('sub_clustering_resolution', 1.0),
            ),
            embedding=EmbeddingConfig(),
            labeling=LabelingConfig(
                batch_size=config_dict.get('llm_batch_size', 8),
            ),
            export=ExportConfig(),
        )
        
        print(f"\n📋 Configuration:")
        print(f"   Seeds: {len(build['seed_dois'])} DOIs")
        print(f"   Max Depth: {config.max_depth}")
        print(f"   Include Citers: {config_dict.get('include_citers', True)}")
        print(f"   Max Citers: {config_dict.get('max_citers', 50)}")
        print(f"   API Email: {config.api.mailto}")
        print(f"   GPU: {config.layout.use_gpu}")
        print(f"   Layout Iterations: {config.layout.fa2_iterations}")
        print(f"   Clustering Resolution: {config.clustering.louvain_resolution}\n")
        
        # Check GPU availability (only if GPU is enabled)
        if config.layout.use_gpu:
            print(f"🎮 GPU Status:")
            try:
                import torch
                if torch.cuda.is_available():
                    print(f"   ✅ PyTorch CUDA: Available")
                    print(f"   GPU: {torch.cuda.get_device_name(0)}")
                    print(f"   CUDA Version: {torch.version.cuda}")
                else:
                    print(f"   ⚠️  PyTorch CUDA: Not available (will use CPU)")
            except ImportError:
                print(f"   ❌ PyTorch: Not installed")
            
            try:
                import cugraph
                print(f"   ✅ cuGraph: Available (GPU-accelerated graph layouts)")
            except ImportError:
                print(f"   ℹ️  cuGraph: Not available (CPU fallback for layouts)")
            
            print()
        
        # Create output directory
        output_dir = Path(f"pipeline_outputs/run_{run_id}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Run the pipeline
        print("🔧 Initializing pipeline orchestrator...")
        orchestrator = PipelineOrchestrator(config, run_id=run_id)
        
        # Check if cancelled before heavy processing
        if check_if_cancelled(run_id):
            print("\n⚠️  Build cancelled by user - stopping before pipeline execution")
            return
        
        print("📊 Executing pipeline workflow...\n")
        
        # Run full pipeline and get the graph data back
        graph_data = orchestrator.run_full_pipeline(build['seed_dois'])
        
        # Check if cancelled after processing (before marking complete)
        if check_if_cancelled(run_id):
            print("\n⚠️  Build cancelled after execution - not marking as completed")
            return
        
        print(f"\n✅ Pipeline completed successfully!")
        
        # Extract actual counts from the graph data
        nodes_count = graph_data.num_nodes()
        edges_count = graph_data.num_edges()
        clusters_count = graph_data.num_clusters()
        
        print(f"\n📊 Final Statistics:")
        print(f"   Nodes: {nodes_count}")
        print(f"   Edges: {edges_count}")
        print(f"   Clusters: {clusters_count}")
        
        # Update database with actual results
        update_build_stats(
            run_id,
            str(output_dir),
            nodes_count,
            edges_count,
            clusters_count
        )
        
        # Export happens automatically in orchestrator.run_full_pipeline()
        # Metadata is now updated in pipeline_runs table
        
        # Mark as completed
        update_build_status(run_id, 'completed')
        print(f"\n🎉 Build {run_id} completed successfully!\n")
        
    except Exception as e:
        print(f"\n❌ Error executing build: {e}\n")
        import traceback
        traceback.print_exc()
        update_build_status(run_id, 'failed', str(e))


def main():
    """Main worker loop."""
    print("\n" + "="*60)
    print("🤖 Pipeline Worker Started")
    print("="*60)
    print(f"\nDatabase: {DB_HOST}:5432")
    print("Polling interval: 10 seconds")
    print("\nWatching for pending builds...")
    print("Press Ctrl+C to stop")
    print("\n")
    
    last_check_had_builds = False
    
    try:
        while True:
            builds = get_pending_builds()
            
            if builds:
                if not last_check_had_builds:
                    print(f"📦 Found {len(builds)} pending build(s)\n")
                last_check_had_builds = True
                
                for build in builds:
                    execute_build(build)
                
                print("\n✅ All pending builds processed\n")
                last_check_had_builds = False
            else:
                if last_check_had_builds:
                    print("💤 No more pending builds\n")
                last_check_had_builds = False
            
            # Wait before checking again
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\n\n👋 Worker stopped by user")
    except Exception as e:
        print(f"\n❌ Worker error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

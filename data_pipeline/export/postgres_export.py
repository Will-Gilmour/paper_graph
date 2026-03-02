"""
PostgreSQL exporter.

Extracted from load_pickle_to_pg.py.
"""

from typing import List, Tuple
import psycopg2
from psycopg2.extras import execute_values

from data_pipeline.models.graph import PaperGraphData
from data_pipeline.models.cluster import Cluster
from data_pipeline.utils.logging import get_logger
from data_pipeline.utils.progress import progress_bar
from data_pipeline.utils.errors import ExportError

logger = get_logger("export.postgres")


class PostgreSQLExporter:
    """
    Exports graph data to PostgreSQL.
    
    Handles papers, edges, and clusters tables.
    """
    
    def __init__(
        self,
        database_url: str,
        run_id: int,
        batch_size_papers: int = 10_000,
        batch_size_edges: int = 10_000,
    ):
        """
        Initialize exporter.
        
        Args:
            database_url: PostgreSQL connection URL
            run_id: Pipeline run ID to associate with this data
            batch_size_papers: Batch size for paper inserts
            batch_size_edges: Batch size for edge inserts
        """
        self.database_url = database_url
        self.run_id = run_id
        self.batch_size_papers = batch_size_papers
        self.batch_size_edges = batch_size_edges
        
        # Ensure partitions exist for this run_id
        self._ensure_partitions_exist()
    
    def _ensure_partitions_exist(self):
        """Create partitions for this run_id if they don't exist."""
        logger.info(f"Ensuring partitions exist for run_id={self.run_id}")
        try:
            conn = psycopg2.connect(self.database_url)
            with conn.cursor() as cur:
                # Create partitions for each table
                for table in ['papers', 'edges', 'clusters', 'sub_clusters']:
                    partition_name = f"{table}_run_{self.run_id}"
                    cur.execute(f"""
                        CREATE TABLE IF NOT EXISTS {partition_name} 
                        PARTITION OF {table} FOR VALUES IN ({self.run_id})
                    """)
                conn.commit()
                logger.info(f"Partitions ready for run_id={self.run_id}")
            conn.close()
        except Exception as e:
            logger.error(f"Failed to create partitions for run_id={self.run_id}: {e}")
            raise ExportError(f"Partition creation failed: {e}")
    
    def export(self, graph_data: PaperGraphData):
        """
        Export graph data to PostgreSQL with run_id partitioning.
        
        Args:
            graph_data: Complete graph data
        """
        logger.info("Connecting to PostgreSQL")
        conn = psycopg2.connect(self.database_url)
        
        try:
            with conn.cursor() as cur:
                self._export_papers(cur, graph_data)
                self._export_edges(cur, graph_data)
                self._export_clusters(cur, graph_data)
                self._export_sub_clusters(cur, graph_data)
            
            conn.commit()
            logger.info("Export complete")
            
        except Exception as e:
            conn.rollback()
            raise ExportError(f"Export failed: {e}")
        finally:
            conn.close()
    
    def _export_papers(self, cur, graph_data: PaperGraphData):
        """Export papers table."""
        logger.info("Exporting papers")
        
        # Debug: Check if positions exist
        if graph_data.positions:
            logger.info(f"✓ Found {len(graph_data.positions)} positions to export")
            sample_doi = list(graph_data.positions.keys())[0]
            sample_pos = graph_data.positions[sample_doi]
            logger.info(f"  Sample position: {sample_doi} -> {sample_pos}")
        else:
            logger.warning("⚠️  No positions found in graph_data.positions!")
        
        # Build rows
        paper_rows = []
        null_issues = []
        
        for doi in graph_data.graph.nodes():
            attrs = graph_data.graph.nodes[doi]
            pos = graph_data.positions.get(doi, (None, None))
            
            # Handle None/NULL values for PostgreSQL arrays
            authors = attrs.get("authors")
            if authors is None:
                authors = []
            elif isinstance(authors, list) and None in authors:
                # Filter out None values from the list
                authors = [a for a in authors if a is not None]
            
            # Debug: Check for problematic data
            if authors is None or (isinstance(authors, list) and None in authors):
                null_issues.append(f"DOI {doi}: authors still has NULLs: {authors}")
            
            # Handle NULL positions - provide defaults instead of NULL
            x_pos = pos[0] if pos[0] is not None else 0.0
            y_pos = pos[1] if pos[1] is not None else 0.0
            
            # Handle NULL fncr - calculate from cited_count or default to 0
            fncr = attrs.get("fncr")
            if fncr is None:
                # Simple fallback: use cited_count as score if fncr not available
                fncr = float(attrs.get("cited_count", 0))
            
            row = (
                self.run_id,  # Added: run_id for graph isolation
                doi,
                attrs.get("title") or "Untitled",  # Default for NULL
                authors,  # Now guaranteed to be a valid array
                attrs.get("year"),
                attrs.get("cited_count", 0),
                attrs.get("references_count", 0),
                graph_data.clusters.get(doi),
                graph_data.sub_clusters.get(doi),
                x_pos,  # No more NULL
                y_pos,  # No more NULL
                fncr,   # No more NULL
            )
            paper_rows.append(row)
        
        # Log NULL issues if found
        if null_issues:
            logger.error(f"Found {len(null_issues)} papers with NULL issues:")
            for issue in null_issues[:5]:  # Show first 5
                logger.error(f"  {issue}")
        
        # Debug: Show sample row
        if paper_rows:
            logger.info(f"\n🔍 Sample export row (first paper):")
            sample = paper_rows[0]
            logger.info(f"  DOI: {sample[0]}")
            logger.info(f"  Title: {sample[1]}")
            logger.info(f"  Authors: {sample[2]} (type: {type(sample[2])})")
            logger.info(f"  Year: {sample[3]}")
            logger.info(f"  Cited: {sample[4]}, Refs: {sample[5]}")
            logger.info(f"  Cluster: {sample[6]}, Sub: {sample[7]}")
            logger.info(f"  Position: x={sample[8]}, y={sample[9]}")
            logger.info(f"  Score (fncr): {sample[10]}")
        
        # Insert in batches
        sql = """
            INSERT INTO papers
            (run_id, doi, title, authors, year, cited_count, references_count,
             cluster, sub_cluster, x, y, fncr)
            VALUES %s
            ON CONFLICT (run_id, doi) DO UPDATE SET
                title = EXCLUDED.title,
                authors = EXCLUDED.authors,
                year = EXCLUDED.year,
                cited_count = EXCLUDED.cited_count,
                references_count = EXCLUDED.references_count,
                cluster = EXCLUDED.cluster,
                sub_cluster = EXCLUDED.sub_cluster,
                x = EXCLUDED.x,
                y = EXCLUDED.y,
                fncr = EXCLUDED.fncr
        """
        
        with progress_bar(total=len(paper_rows), desc="Papers", unit="row") as pbar:
            for i in range(0, len(paper_rows), self.batch_size_papers):
                batch = paper_rows[i:i+self.batch_size_papers]
                execute_values(cur, sql, batch, page_size=self.batch_size_papers)
                pbar.update(len(batch))
    
    def _export_edges(self, cur, graph_data: PaperGraphData):
        """Export edges table."""
        logger.info("Exporting edges")
        
        edge_rows = [(self.run_id, u, v) for u, v in graph_data.graph.edges()]
        
        sql = """
            INSERT INTO edges (run_id, src, dst)
            VALUES %s
            ON CONFLICT (run_id, src, dst) DO NOTHING
        """
        
        with progress_bar(total=len(edge_rows), desc="Edges", unit="row") as pbar:
            for i in range(0, len(edge_rows), self.batch_size_edges):
                batch = edge_rows[i:i+self.batch_size_edges]
                execute_values(cur, sql, batch, page_size=self.batch_size_edges)
                pbar.update(len(batch))
    
    def _export_clusters(self, cur, graph_data: PaperGraphData):
        """Export clusters table."""
        logger.info("Exporting clusters")
        
        # Aggregate cluster metadata
        cluster_data = {}
        for doi, cluster_id in graph_data.clusters.items():
            if cluster_id not in cluster_data:
                cluster_data[cluster_id] = {"dois": [], "xs": [], "ys": []}
            
            cluster_data[cluster_id]["dois"].append(doi)
            pos = graph_data.positions.get(doi)
            if pos:
                cluster_data[cluster_id]["xs"].append(pos[0])
                cluster_data[cluster_id]["ys"].append(pos[1])
        
        # Build rows
        cluster_rows = []
        for cluster_id, data in cluster_data.items():
            label = graph_data.cluster_labels.get(cluster_id, f"Cluster {cluster_id}")
            # Replace invalid labels with fallback
            if not label or label == "NO VALID TITLE":
                label = f"Cluster {cluster_id}"
            size = len(data["dois"])
            avg_x = sum(data["xs"]) / len(data["xs"]) if data["xs"] else 0.0
            avg_y = sum(data["ys"]) / len(data["ys"]) if data["ys"] else 0.0
            
            cluster_rows.append((self.run_id, cluster_id, label, size, avg_x, avg_y))
        
        # Insert
        sql = """
            INSERT INTO clusters (run_id, id, title, size, x, y)
            VALUES %s
            ON CONFLICT (run_id, id) DO UPDATE SET
                title = EXCLUDED.title,
                size = EXCLUDED.size,
                x = EXCLUDED.x,
                y = EXCLUDED.y
        """
        
        if cluster_rows:
            execute_values(cur, sql, cluster_rows)
            logger.info(f"Exported {len(cluster_rows)} clusters")
    
    def _export_sub_clusters(self, cur, graph_data: PaperGraphData):
        """Export sub-clusters table."""
        logger.info("Exporting sub-clusters")
        
        # Aggregate sub-cluster metadata
        sub_cluster_data = {}
        for doi, cluster_id in graph_data.clusters.items():
            sub_cluster_id = graph_data.sub_clusters.get(doi)
            if sub_cluster_id is not None:
                key = (cluster_id, sub_cluster_id)
                if key not in sub_cluster_data:
                    sub_cluster_data[key] = {"count": 0}
                sub_cluster_data[key]["count"] += 1
        
        # Build rows
        sub_cluster_rows = []
        for (cluster_id, sub_cluster_id), data in sub_cluster_data.items():
            label = graph_data.sub_cluster_labels.get((cluster_id, sub_cluster_id), f"Sub-cluster {cluster_id}.{sub_cluster_id}")
            # Replace invalid labels with fallback
            if not label or label == "NO VALID TITLE":
                label = f"Sub-cluster {cluster_id}.{sub_cluster_id}"
            
            sub_cluster_rows.append((self.run_id, cluster_id, sub_cluster_id, label))
        
        # Insert
        sql = """
            INSERT INTO sub_clusters (run_id, cluster_id, sub_cluster_id, title)
            VALUES %s
            ON CONFLICT (run_id, cluster_id, sub_cluster_id) DO UPDATE SET
                title = EXCLUDED.title
        """
        
        if sub_cluster_rows:
            execute_values(cur, sql, sub_cluster_rows)
            logger.info(f"Exported {len(sub_cluster_rows)} sub-clusters")


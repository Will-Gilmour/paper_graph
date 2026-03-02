#!/usr/bin/env python3
"""
Load original MRgFUS graph from PKL into partitioned PostgreSQL tables.

Usage:
    python load_original_graph_to_partitioned.py data_pipeline_output/graph.pkl.gz

This loads the graph into run_id=1 partition.
"""

import os
import sys
import gzip
import pickle
import time
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values
from tqdm import tqdm

# Configuration
RUN_ID = 1  # Load into run_id=1 (MRgFUS original graph)
BATCH_SIZE = 10_000

# Database connection
DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://pg:secret@localhost:5432/litsearch"
)


def load_pickle(pkl_path: Path):
    """Load graph data from pickle file."""
    import json
    
    print(f"[1/5] Loading {pkl_path} ...")
    # Try gzip first (handles .gz extension or gzip magic bytes)
    try:
        with gzip.open(pkl_path, "rb") as f:
            data = pickle.load(f)
    except (gzip.BadGzipFile, OSError):
        # Fall back to uncompressed
        with open(pkl_path, "rb") as f:
            data = pickle.load(f)
    
    graph = data["graph"]
    positions = data["pos"]
    
    # Extract cluster assignments from node attributes (not from separate dicts)
    clusters = {doi: graph.nodes[doi].get('cluster') for doi in graph.nodes() if 'cluster' in graph.nodes[doi]}
    sub_clusters = {doi: graph.nodes[doi].get('sub_cluster') for doi in graph.nodes() if 'sub_cluster' in graph.nodes[doi]}
    cluster_labels = data.get("parent_labels", {})
    sub_cluster_labels = data.get("sub_labels", {})
    
    # Try to load from external JSON files if not in PKL
    if not cluster_labels and Path("/tmp/parentlabels.json").exists():
        print("   Loading parent labels from JSON...")
        with open("/tmp/parentlabels.json") as f:
            cluster_labels = json.load(f)
    
    if not sub_cluster_labels and Path("/tmp/sublabels.json").exists():
        print("   Loading sub labels from JSON...")
        with open("/tmp/sublabels.json") as f:
            sub_cluster_labels = json.load(f)
    
    print(f"   > {graph.number_of_nodes():,} nodes")
    print(f"   > {graph.number_of_edges():,} edges")
    print(f"   > {len(clusters):,} papers clustered")
    print(f"   > {len(cluster_labels):,} parent labels")
    print(f"   > {len(sub_cluster_labels):,} sub labels")
    
    return graph, positions, clusters, sub_clusters, cluster_labels, sub_cluster_labels


def export_papers(cur, graph, positions, clusters, sub_clusters):
    """Export papers to PostgreSQL."""
    print("\n[2/5] Exporting papers...")
    
    rows = []
    for doi in tqdm(graph.nodes(), desc="Building rows"):
        attrs = graph.nodes[doi]
        pos = positions.get(doi, (0.0, 0.0))
        
        # Handle authors array
        authors = attrs.get("authors", [])
        if authors is None:
            authors = []
        elif isinstance(authors, list) and None in authors:
            authors = [a for a in authors if a is not None]
        
        row = (
            RUN_ID,
            doi,
            attrs.get("title") or "Untitled",
            authors,
            attrs.get("year"),
            attrs.get("cited_count", 0),
            attrs.get("references_count", 0),
            clusters.get(doi),
            sub_clusters.get(doi),
            float(pos[0]) if pos[0] is not None else 0.0,
            float(pos[1]) if pos[1] is not None else 0.0,
            float(attrs.get("fncr", 0.0)),
        )
        rows.append(row)
    
    print(f"Inserting {len(rows):,} papers...")
    sql = """
        INSERT INTO papers
        (run_id, doi, title, authors, year, cited_count, references_count,
         cluster, sub_cluster, x, y, fncr)
        VALUES %s
    """
    
    for i in tqdm(range(0, len(rows), BATCH_SIZE), desc="Batches"):
        batch = rows[i:i+BATCH_SIZE]
        execute_values(cur, sql, batch, page_size=BATCH_SIZE)


def export_edges(cur, graph):
    """Export edges to PostgreSQL."""
    print("\n[3/5] Exporting edges...")
    
    rows = [(RUN_ID, src, dst) for src, dst in graph.edges()]
    
    print(f"Inserting {len(rows):,} edges...")
    sql = "INSERT INTO edges (run_id, src, dst) VALUES %s"
    
    for i in tqdm(range(0, len(rows), BATCH_SIZE), desc="Batches"):
        batch = rows[i:i+BATCH_SIZE]
        execute_values(cur, sql, batch, page_size=BATCH_SIZE)


def export_clusters(cur, clusters, cluster_labels, positions):
    """Export cluster metadata."""
    print("\n[4/5] Exporting clusters...")
    
    # Aggregate cluster data
    cluster_data = {}
    for doi, cluster_id in clusters.items():
        if cluster_id not in cluster_data:
            cluster_data[cluster_id] = {"dois": [], "xs": [], "ys": []}
        
        cluster_data[cluster_id]["dois"].append(doi)
        pos = positions.get(doi)
        if pos:
            cluster_data[cluster_id]["xs"].append(pos[0])
            cluster_data[cluster_id]["ys"].append(pos[1])
    
    rows = []
    for cluster_id, data in cluster_data.items():
        label = cluster_labels.get(str(cluster_id), f"Cluster {cluster_id}")
        size = len(data["dois"])
        avg_x = sum(data["xs"]) / len(data["xs"]) if data["xs"] else 0.0
        avg_y = sum(data["ys"]) / len(data["ys"]) if data["ys"] else 0.0
        
        rows.append((RUN_ID, cluster_id, label, size, avg_x, avg_y))
    
    print(f"Inserting {len(rows)} clusters...")
    sql = "INSERT INTO clusters (run_id, id, title, size, x, y) VALUES %s"
    execute_values(cur, sql, rows)


def export_sub_clusters(cur, sub_cluster_labels):
    """Export sub-cluster labels."""
    print("\n[5/5] Exporting sub-cluster labels...")
    
    rows = []
    for key, label in sub_cluster_labels.items():
        # Key format is "cluster:sub" (e.g., "10:5")
        if ":" in str(key):
            cluster_id, sub_id = str(key).split(":")
            rows.append((RUN_ID, int(cluster_id), int(sub_id), label))
    
    if rows:
        print(f"Inserting {len(rows)} sub-cluster labels...")
        sql = "INSERT INTO sub_clusters (run_id, cluster_id, sub_cluster_id, title) VALUES %s"
        execute_values(cur, sql, rows)
    else:
        print("No sub-cluster labels to export")


def update_metadata(cur, graph, clusters):
    """Update pipeline_runs metadata."""
    nodes_count = graph.number_of_nodes()
    edges_count = graph.number_of_edges()
    clusters_count = len(set(clusters.values())) if clusters else 0
    
    cur.execute("""
        UPDATE pipeline_runs
        SET nodes_count = %s, edges_count = %s, clusters_count = %s
        WHERE id = %s
    """, (nodes_count, edges_count, clusters_count, RUN_ID))
    
    print(f"\n> Updated metadata: {nodes_count:,} nodes, {edges_count:,} edges, {clusters_count} clusters")


def main():
    if len(sys.argv) < 2:
        print("Usage: python load_original_graph_to_partitioned.py <path/to/graph.pkl.gz>")
        sys.exit(1)
    
    pkl_path = Path(sys.argv[1])
    if not pkl_path.exists():
        print(f"Error: {pkl_path} not found")
        sys.exit(1)
    
    # Load pickle
    graph, positions, clusters, sub_clusters, cluster_labels, sub_cluster_labels = load_pickle(pkl_path)
    
    # Connect to database
    print(f"\nConnecting to database...")
    conn = psycopg2.connect(DB_URL)
    
    try:
        with conn.cursor() as cur:
            # Export all data
            export_papers(cur, graph, positions, clusters, sub_clusters)
            export_edges(cur, graph)
            export_clusters(cur, clusters, cluster_labels, positions)
            export_sub_clusters(cur, sub_cluster_labels)
            update_metadata(cur, graph, clusters)
        
        conn.commit()
        print("\n>> Successfully loaded original graph into run_id=1 partition!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n!! Error: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()



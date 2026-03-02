"""
Database query functions WITH run_id filtering.

This file replaces queries.py with proper graph partitioning support.
All queries are automatically scoped to the active graph (via run_id partitioning).
"""
from typing import List, Dict, Tuple, Optional
import psycopg2.errors

from backend.app.database.connection import get_conn, put_conn, get_db_connection


# ============================================================================
# ACTIVE GRAPH HELPER
# ============================================================================

def get_active_run_id() -> Optional[int]:
    """
    Get the run_id of the currently active graph.
    
    Returns:
        int: The active run_id, or None if no graph is active
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM pipeline_runs WHERE is_active = TRUE LIMIT 1")
            row = cur.fetchone()
            return row[0] if row else None


# ============================================================================
# CLUSTER QUERIES
# ============================================================================

def fetch_all_clusters() -> List[Dict]:
    """
    Fetch all clusters with their metadata and top sub-clusters.
    
    Returns:
        List of cluster dictionaries with id, title, x, y, size, and _subs
    """
    run_id = get_active_run_id()
    if run_id is None:
        return []
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Fetch main cluster data for active graph
            cur.execute("""
                SELECT id, title, x, y, size
                FROM clusters
                WHERE run_id = %s
                ORDER BY size DESC
            """, (run_id,))
            clusters = {
                r[0]: dict(id=r[0], title=r[1] or "", x=r[2], y=r[3], size=r[4])
                for r in cur.fetchall()
            }
            
            # Fetch sub-cluster counts for active graph
            try:
                cur.execute("""
                    SELECT cluster, sub_cluster, count(*) AS n
                    FROM papers
                    WHERE run_id = %s AND sub_cluster IS NOT NULL
                    GROUP BY cluster, sub_cluster
                """, (run_id,))
                for cid, sid, n in cur.fetchall():
                    clusters.setdefault(cid, {}).setdefault("_subs", []).append((sid, n))
            except psycopg2.errors.UndefinedColumn:
                pass
            
            return clusters


def fetch_cluster_nodes(cluster_id: int) -> List[Dict]:
    """
    Fetch all papers/nodes in a specific cluster.
    
    Args:
        cluster_id: The cluster ID to fetch nodes for
        
    Returns:
        List of node dictionaries with doi, title, x, y, fncr
    """
    run_id = get_active_run_id()
    if run_id is None:
        return []
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT doi, title, x, y, fncr
                FROM papers
                WHERE run_id = %s AND cluster = %s
            """,
                (run_id, cluster_id),
            )
            return [
                {"doi": d, "title": t or "", "x": x, "y": y, "fncr": f} 
                for d, t, x, y, f in cur.fetchall()
            ]


def fetch_cluster_edges(cluster_id: int) -> List[Dict]:
    """
    Fetch all edges between papers in a specific cluster.
    
    Args:
        cluster_id: The cluster ID to fetch edges for
        
    Returns:
        List of edge dictionaries with source and target DOIs
    """
    run_id = get_active_run_id()
    if run_id is None:
        return []
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT e.src, e.dst
                FROM edges e
                JOIN papers p1 ON e.run_id = p1.run_id AND e.src = p1.doi
                JOIN papers p2 ON e.run_id = p2.run_id AND e.dst = p2.doi
                WHERE e.run_id = %s AND p1.cluster = %s AND p2.cluster = %s
            """,
                (run_id, cluster_id, cluster_id),
            )
            return [
                {"source": src, "target": dst} for src, dst in cur.fetchall()
            ]


# ============================================================================
# PAPER QUERIES
# ============================================================================

def fetch_paper_by_doi(doi: str) -> Optional[Tuple]:
    """
    Fetch a paper by its DOI.
    
    Args:
        doi: The DOI to look up (case-insensitive)
        
    Returns:
        Tuple of (doi, title, authors, year, refs_count, cited_count, 
                  cluster, fncr, x, y) or None if not found
    """
    run_id = get_active_run_id()
    if run_id is None:
        return None
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT doi, title, authors, year,
                       references_count, cited_count, cluster, fncr, x, y
                FROM papers
                WHERE run_id = %s AND lower(doi) = %s
            """,
                (run_id, doi.lower()),
            )
            return cur.fetchone()


def fetch_papers_for_ndjson(cited_threshold: int = 25, seed_dois: Optional[List[str]] = None) -> List[Tuple]:
    """
    Fetch papers for NDJSON export based on citation threshold or seed list.
    
    Args:
        cited_threshold: Minimum citation count for papers
        seed_dois: Optional list of DOIs to include regardless of citations
        
    Returns:
        List of tuples (doi, cluster, cited_count, refs_count, x, y, fncr, year)
    """
    run_id = get_active_run_id()
    if run_id is None:
        return []
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if seed_dois:
                cur.execute(
                    """
                    SELECT doi, cluster, cited_count, references_count, x, y, fncr, year
                    FROM papers
                    WHERE run_id = %s AND (cited_count > %s OR lower(doi) = ANY(%s))
                """,
                    (run_id, cited_threshold, seed_dois),
                )
            else:
                cur.execute(
                    """
                    SELECT doi, cluster, cited_count, references_count, x, y, fncr, year
                    FROM papers
                    WHERE run_id = %s AND cited_count > %s
                """,
                    (run_id, cited_threshold),
                )
            return cur.fetchall()


def fetch_nodes_paginated(
    offset: int = 0,
    limit: int = 1000,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    min_citations: Optional[int] = None
) -> List[Dict]:
    """
    Fetch paginated node data for export with optional filters.
    
    Args:
        offset: Number of nodes to skip
        limit: Maximum number of nodes to return
        year_min: Optional minimum publication year
        year_max: Optional maximum publication year
        min_citations: Optional minimum citation count
        
    Returns:
        List of node dictionaries
    """
    run_id = get_active_run_id()
    if run_id is None:
        return []
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Build WHERE clause
            where_clauses = ["run_id = %s"]
            params = [run_id]
            
            if year_min is not None:
                where_clauses.append("year >= %s")
                params.append(year_min)
            
            if year_max is not None:
                where_clauses.append("year <= %s")
                params.append(year_max)
            
            if min_citations is not None:
                where_clauses.append("cited_count >= %s")
                params.append(min_citations)
            
            where_sql = " AND ".join(where_clauses)
            params.extend([limit, offset])
            
            cur.execute(
                f"""
                SELECT doi, x, y, cluster, cited_count, references_count, fncr, year
                FROM papers
                WHERE {where_sql}
                ORDER BY doi
                LIMIT %s OFFSET %s
            """,
                tuple(params),
            )
            return [
                {
                    "doi": d,
                    "x": x,
                    "y": y,
                    "cluster": c,
                    "cited_count": cited,
                    "references_count": refs,
                    "fncr": f,
                    "year": yr,
                }
                for d, x, y, c, cited, refs, f, yr in cur.fetchall()
            ]


def fetch_edges_paginated(offset: int = 0, limit: int = 1000) -> List[Dict]:
    """
    Fetch paginated edge data for export.
    
    Args:
        offset: Number of edges to skip
        limit: Maximum number of edges to return
        
    Returns:
        List of edge dictionaries
    """
    run_id = get_active_run_id()
    if run_id is None:
        return []
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT src, dst
                FROM edges
                WHERE run_id = %s
                ORDER BY src, dst
                LIMIT %s OFFSET %s
            """,
                (run_id, limit, offset),
            )
            return [{"source": s, "target": t} for s, t in cur.fetchall()]


# ============================================================================
# EDGE QUERIES
# ============================================================================

def fetch_edges_for_dois(dois: List[str]) -> List[Tuple[str, str]]:
    """
    Fetch all edges between a list of DOIs.
    
    Args:
        dois: List of DOIs to fetch edges for
        
    Returns:
        List of tuples (source, target)
    """
    run_id = get_active_run_id()
    if run_id is None:
        return []
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT src, dst
                FROM edges
                WHERE run_id = %s AND src = ANY(%s) AND dst = ANY(%s)
            """,
                (run_id, dois, dois),
            )
            return cur.fetchall()


# ============================================================================
# SEARCH QUERIES
# ============================================================================

def search_papers_by_title(query: str, limit: int = 200) -> List[Tuple[str, str]]:
    """
    Search for papers by title using ILIKE pattern matching.
    
    Args:
        query: Search query string
        limit: Maximum number of results
        
    Returns:
        List of tuples (doi, title)
    """
    run_id = get_active_run_id()
    if run_id is None:
        return []
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT doi, title
                FROM papers
                WHERE run_id = %s AND title ILIKE %s
                ORDER BY cited_count DESC
                LIMIT %s
            """,
                (run_id, f"%{query.lower()}%", limit),
            )
            return cur.fetchall()


def search_papers_by_author(query: str, limit: int = 200) -> List[Tuple[str, str]]:
    """
    Search for papers by author using ILIKE on the authors array (as text).
    
    Args:
        query: Author name to search for
        limit: Maximum number of results
        
    Returns:
        List of tuples (doi, title)
    """
    run_id = get_active_run_id()
    if run_id is None:
        return []
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT doi, title
                FROM papers
                WHERE run_id = %s AND EXISTS (
                    SELECT 1 FROM unnest(authors) AS author
                    WHERE author ILIKE %s
                )
                ORDER BY cited_count DESC
                LIMIT %s
            """,
                (run_id, f"%{query}%", limit),
            )
            return cur.fetchall()


def search_papers_trigram(query: str, limit: int = 200) -> List[Tuple[str, str]]:
    """
    Search for papers using trigram similarity (requires pg_trgm extension).
    
    Args:
        query: Search query string
        limit: Maximum number of results
        
    Returns:
        List of tuples (doi, title)
    """
    run_id = get_active_run_id()
    if run_id is None:
        return []
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT doi, title
                FROM papers
                WHERE run_id = %s AND (title % %s OR doi % %s)
                ORDER BY similarity(title, %s) DESC
                LIMIT %s
            """,
                (run_id, query.lower(), query.lower(), query.lower(), limit),
            )
            return cur.fetchall()


def search_papers_random_sample(limit: int = 200) -> List[Tuple[str, str]]:
    """
    Get a random sample of papers (fallback for when search fails).
    
    Args:
        limit: Maximum number of results
        
    Returns:
        List of tuples (doi, title)
    """
    run_id = get_active_run_id()
    if run_id is None:
        return []
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT doi, title
                FROM papers
                WHERE run_id = %s
                TABLESAMPLE SYSTEM(1)
                LIMIT %s
            """,
                (run_id, limit),
            )
            return cur.fetchall()


# ============================================================================
# STATISTICS QUERIES
# ============================================================================

def get_total_counts() -> Tuple[int, int]:
    """
    Get total counts of nodes and edges in the database FOR THE ACTIVE GRAPH.
    
    Returns:
        Tuple of (nodes_total, edges_total)
    """
    run_id = get_active_run_id()
    if run_id is None:
        return (0, 0)
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM papers WHERE run_id = %s", (run_id,))
            nodes_total = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM edges WHERE run_id = %s", (run_id,))
            edges_total = cur.fetchone()[0]
            return nodes_total, edges_total


# ============================================================================
# EGO GRAPH QUERIES
# ============================================================================

def fetch_ego_network(center_doi: str, depth: int = 1) -> Tuple[List[str], List[Tuple[str, str]]]:
    """
    Fetch ego network around a center node up to a given depth.
    
    Args:
        center_doi: The center DOI
        depth: Number of hops from center (1 or 2)
        
    Returns:
        Tuple of (doi_list, edge_list)
    """
    run_id = get_active_run_id()
    if run_id is None:
        return ([], [])
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Start with center node
            dois = {center_doi.lower()}
            
            # Depth 1: immediate neighbors
            cur.execute(
                """
                SELECT DISTINCT dst FROM edges WHERE run_id = %s AND LOWER(src) = %s
                UNION
                SELECT DISTINCT src FROM edges WHERE run_id = %s AND LOWER(dst) = %s
            """,
                (run_id, center_doi.lower(), run_id, center_doi.lower()),
            )
            depth1_neighbors = {r[0] for r in cur.fetchall()}
            dois.update(depth1_neighbors)
            
            # Depth 2: neighbors of neighbors (if requested)
            if depth >= 2 and depth1_neighbors:
                cur.execute(
                    """
                    SELECT DISTINCT dst FROM edges WHERE run_id = %s AND src = ANY(%s)
                    UNION
                    SELECT DISTINCT src FROM edges WHERE run_id = %s AND dst = ANY(%s)
                """,
                    (run_id, list(depth1_neighbors), run_id, list(depth1_neighbors)),
                )
                depth2_neighbors = {r[0] for r in cur.fetchall()}
                dois.update(depth2_neighbors)
            
            # Fetch edges
            cur.execute(
                """
                SELECT src, dst
                FROM edges
                WHERE run_id = %s AND src = ANY(%s) AND dst = ANY(%s)
            """,
                (run_id, list(dois), list(dois)),
            )
            edges = cur.fetchall()
            
            return list(dois), edges


# ============================================================================
# UTILITY QUERIES
# ============================================================================

def check_pg_trgm_enabled() -> bool:
    """
    Check if pg_trgm extension is enabled.
    
    Returns:
        True if pg_trgm is enabled, False otherwise
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_extension WHERE extname='pg_trgm'")
            return cur.fetchone() is not None


def search_papers_combined(
    title_query: Optional[str] = None,
    author_query: Optional[str] = None,
    cluster_ids: Optional[List[int]] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    min_citations: Optional[int] = None,
    limit: int = 200
) -> List[Tuple[str, str, int, int, int]]:
    """
    Search for papers with multiple combined criteria (title AND author AND filters).
    
    Args:
        title_query: Search in title
        author_query: Search in authors
        cluster_ids: Filter by multiple cluster IDs
        year_min: Minimum publication year
        year_max: Maximum publication year
        min_citations: Minimum citation count
        limit: Maximum number of results
        
    Returns:
        List of tuples (doi, title, year, cited_count, cluster)
    """
    run_id = get_active_run_id()
    if run_id is None:
        return []
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Build dynamic WHERE clause
            where_clauses = ["run_id = %s"]
            params = [run_id]
            
            if title_query:
                where_clauses.append("title ILIKE %s")
                params.append(f"%{title_query}%")
            
            if author_query:
                where_clauses.append("""
                    EXISTS (
                        SELECT 1 FROM unnest(authors) AS author
                        WHERE author ILIKE %s
                    )
                """)
                params.append(f"%{author_query}%")
            
            if cluster_ids:
                where_clauses.append("cluster = ANY(%s)")
                params.append(cluster_ids)
            
            if year_min is not None:
                where_clauses.append("year >= %s")
                params.append(year_min)
            
            if year_max is not None:
                where_clauses.append("year <= %s")
                params.append(year_max)
            
            if min_citations is not None:
                where_clauses.append("cited_count >= %s")
                params.append(min_citations)
            
            # If no search criteria provided (besides run_id), return empty
            if len(where_clauses) == 1:
                return []
            
            where_sql = " AND ".join(where_clauses)
            params.append(limit)
            
            cur.execute(
                f"""
                SELECT doi, title, year, cited_count, cluster
                FROM papers
                WHERE {where_sql}
                ORDER BY cited_count DESC
                LIMIT %s
            """,
                tuple(params),
            )
            return cur.fetchall()


def search_papers_filtered(
    query: str,
    cluster_id: Optional[int] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    min_citations: Optional[int] = None,
    limit: int = 200
) -> List[Tuple[str, str, int, int, int]]:
    """
    Search for papers with additional filters.
    
    Args:
        query: Search query string
        cluster_id: Filter by cluster ID
        year_min: Minimum publication year
        year_max: Maximum publication year
        min_citations: Minimum citation count
        limit: Maximum number of results
        
    Returns:
        List of tuples (doi, title, year, cited_count, cluster)
    """
    run_id = get_active_run_id()
    if run_id is None:
        return []
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Build dynamic WHERE clause
            where_clauses = ["run_id = %s", "title ILIKE %s"]
            params = [run_id, f"%{query.lower()}%"]
            
            if cluster_id is not None:
                where_clauses.append("cluster = %s")
                params.append(cluster_id)
            
            if year_min is not None:
                where_clauses.append("year >= %s")
                params.append(year_min)
            
            if year_max is not None:
                where_clauses.append("year <= %s")
                params.append(year_max)
            
            if min_citations is not None:
                where_clauses.append("cited_count >= %s")
                params.append(min_citations)
            
            where_sql = " AND ".join(where_clauses)
            params.append(limit)
            
            cur.execute(
                f"""
                SELECT doi, title, year, cited_count, cluster
                FROM papers
                WHERE {where_sql}
                ORDER BY cited_count DESC
                LIMIT %s
            """,
                tuple(params),
            )
            return cur.fetchall()


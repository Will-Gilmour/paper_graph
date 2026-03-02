#!/usr/bin/env python3
"""
Bulk-load a PaperGraph pickle into PostgreSQL (Azure Flexible Server friendly).

USAGE
-----

# 1) One-time: install deps
#    pip install psycopg[binary] tqdm

# 2) Point the script at your DB (⇣ adjust password / host ⇣)
#    PowerShell:
#        $env:DATABASE_URL = "postgresql://user:password@host:5432/litsearch?sslmode=require"
#    Bash:
#        export DATABASE_URL='postgresql://user:password@host:5432/litsearch?sslmode=require'

# 3) Run:
#    python load_pickle_to_pg.py mrgfus_papers4.pkl.gz
"""

from __future__ import annotations

import os, sys, gzip, pickle, time
from pathlib import Path
from typing import List, Tuple

import psycopg2
from psycopg2.extras import execute_values
from tqdm import tqdm

# ------------------------------------------------------------
# Optional but faster: execute_values is psycopg2's bulk helper
try:
    from psycopg2.extras import execute_values        # psycopg2
except ImportError:                                  # very old driver
    execute_values = None

# Batch sizes tuned for Azure PG (you can change them)
BATCH_PAPERS   = 10_000
BATCH_CITATION = 10_000
# ------------------------------------------------------------


def load_pickle(pkl: Path):
    print(f"[1/4] Loading {pkl} …")
    t0 = time.time()
    with gzip.open(pkl, "rb") as f:
        data = pickle.load(f)
    g, pos = data["graph"], data["pos"]
    print(f"      {g.number_of_nodes():,} nodes, {g.number_of_edges():,} edges "
          f"({time.time()-t0:.1f}s)")
    return g, pos


def chunk(seq: list, n: int):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def bulk_insert(cur, sql: str, rows: List[Tuple], page_size: int):
    """Insert rows in one round-trip per batch."""
    if execute_values:
        execute_values(cur, sql, rows, page_size=page_size)
    else:                          # fallback (slower, but works)
        cur.executemany(sql.replace("VALUES %s", "VALUES (" +
                         ",".join(["%s"] * len(rows[0])) + ")"), rows)


def main(pkl_path: Path, db_url: str):
    g, pos = load_pickle(pkl_path)

    print("[2/4] Connecting to Postgres …")
    conn = psycopg2.connect(db_url)
    cur  = conn.cursor()

    # -------- papers -------------------------------------------------
    print("[3/4] Inserting papers")
    paper_rows: List[Tuple] = [
        (
            doi,
            g.nodes[doi].get("title"),
            g.nodes[doi].get("authors", []),      # text[]
            g.nodes[doi].get("year"),
            g.in_degree(doi),
            g.out_degree(doi),
            g.nodes[doi].get("cluster"),
            g.nodes[doi].get("sub_cluster"),
            pos[doi][0],
            pos[doi][1],
            g.nodes[doi].get("fncr"),             # Added FNCR field
        ) for doi in g.nodes
    ]

    sql_papers = """
        INSERT INTO papers
        (doi, title, authors, year,
         cited_count, references_count,
         cluster, sub_cluster, x, y, fncr)
        VALUES %s
        ON CONFLICT (doi) DO NOTHING
    """

    with tqdm(total=len(paper_rows), unit="row") as bar:
        for batch in chunk(paper_rows, BATCH_PAPERS):
            bulk_insert(cur, sql_papers, batch, BATCH_PAPERS)
            bar.update(len(batch))

    # -------- edges ----------------------------------------------
    print("[4/4] Inserting edges")
    cite_rows = [(u, v) for u, v in g.edges()]
    sql_cites = """
        INSERT INTO edges (src, dst)
        VALUES %s
        ON CONFLICT DO NOTHING
    """

    with tqdm(total=len(cite_rows), unit="row") as bar:
        for batch in chunk(cite_rows, BATCH_CITATION):
            bulk_insert(cur, sql_cites, batch, BATCH_CITATION)
            bar.update(len(batch))

    conn.commit()
    cur.close(); conn.close()
    print("✔︎ Finished! Database is populated.")


# ---------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python load_pickle_to_pg.py <pickle.gz>")
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        sys.exit("Error: set the DATABASE_URL env-var first.")
    main(Path(sys.argv[1]), dsn)

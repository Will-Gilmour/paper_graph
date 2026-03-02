"""Label parent clusters only, using existing sub-cluster labels from database.

Usage:
  python scripts/label_parents_only.py --run-id 33 --precision 8bit --seed 42 --temperature 0.0
"""
import argparse
import os
from collections import defaultdict

import psycopg2

from data_pipeline.config.settings import get_config
from data_pipeline.labeling.llm_client import LLMClient
from data_pipeline.labeling.prompts import format_parent_cluster_prompt


def get_active_run_id(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM pipeline_runs WHERE is_active = TRUE")
        row = cur.fetchone()
        return row[0] if row else None


def fetch_sub_labels_from_db(conn, run_id: int):
    """Fetch existing sub-cluster labels from database."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT cluster_id, sub_cluster_id, title
            FROM sub_clusters
            WHERE run_id = %s AND title IS NOT NULL AND title != 'NO VALID TITLE'
            """,
            (run_id,),
        )
        sub_labels = {}
        for cid, sid, title in cur.fetchall():
            sub_labels[(cid, sid)] = title
        return sub_labels


def compute_sub_sizes(conn, run_id: int):
    """Count papers in each sub-cluster."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT cluster, sub_cluster, COUNT(*)
            FROM papers
            WHERE run_id = %s AND sub_cluster IS NOT NULL
            GROUP BY cluster, sub_cluster
            """,
            (run_id,),
        )
        return {(cid, sid): n for cid, sid, n in cur.fetchall()}


def upsert_parent_labels(conn, run_id: int, parent_labels: dict):
    with conn.cursor() as cur:
        for cid, title in parent_labels.items():
            cur.execute(
                """
                INSERT INTO clusters (run_id, id, title)
                VALUES (%s, %s, %s)
                ON CONFLICT (run_id, id) DO UPDATE SET title = EXCLUDED.title
                """,
                (run_id, cid, title),
            )
    conn.commit()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", type=int, default=None, help="Run ID (defaults to active)")
    ap.add_argument("--precision", type=str, default=os.getenv("PIPELINE_LABELING_PRECISION", "8bit"),
                    choices=["8bit", "4bit", "bf16"], help="LLM precision")
    ap.add_argument("--seed", type=int, default=42, help="Random/LLM seed")
    ap.add_argument("--temperature", type=float, default=0.0, help="LLM temperature")
    ap.add_argument("--show-prompts", action="store_true", help="Print prompts")
    args = ap.parse_args()

    cfg = get_config()
    conn = psycopg2.connect(cfg.export.database_url)
    
    try:
        run_id = args.run_id or get_active_run_id(conn)
        if not run_id:
            print("No run_id provided and no active run; aborting")
            return
        print(f"Labeling parent clusters for run: {run_id}")

        # Load sub-cluster labels from database
        sub_labels = fetch_sub_labels_from_db(conn, run_id)
        if not sub_labels:
            print("No sub-cluster labels found in database; aborting")
            return
        print(f"Loaded {len(sub_labels)} sub-cluster labels from database")

        # Get sub-cluster sizes
        sub_sizes = compute_sub_sizes(conn, run_id)

        # Group by parent
        parent_to_sub = defaultdict(list)
        for (cid, sid) in sub_labels.keys():
            parent_to_sub[cid].append((cid, sid))

        # Build parent prompts
        parent_prompts = {}
        for cid, subkeys in parent_to_sub.items():
            topics = []
            for key in subkeys:
                topics.append((sub_labels.get(key, ""), sub_sizes.get(key, 0)))
            topics.sort(key=lambda x: -x[1])
            prompt = format_parent_cluster_prompt(topics[:10])
            parent_prompts[cid] = prompt
            if args.show_prompts and len(parent_prompts) <= 3:
                print(f"\n[Prompt] Parent {cid}\n" + "\n".join(prompt.splitlines()[:25]) + "\n...")

        # Init LLM
        llm = LLMClient(
            model_name=cfg.labeling.model_name,
            hf_token=cfg.labeling.hf_token,
            batch_size=min(4, cfg.labeling.batch_size),
            max_new_tokens=cfg.labeling.max_new_tokens,
            temperature=args.temperature,
            precision=args.precision,
            deterministic=(args.temperature == 0.0),
            seed=args.seed,
        )

        # Generate parent labels
        parent_ids = list(parent_prompts.keys())
        parent_texts = [parent_prompts[cid] for cid in parent_ids]
        print(f"Generating {len(parent_texts)} parent cluster labels...")
        parent_responses = llm.generate(parent_texts)
        
        parent_labels = {}
        for cid, resp in zip(parent_ids, parent_responses):
            _reason, label = llm.parse_parent_cluster_label(resp)
            parent_labels[cid] = label
            if args.show_prompts:
                print(f"Parent {cid}: {label}")

        # Write to DB
        upsert_parent_labels(conn, run_id, parent_labels)
        print(f"✓ Parent labeling complete! {len(parent_labels)} labels written to database")

    finally:
        conn.close()


if __name__ == "__main__":
    main()



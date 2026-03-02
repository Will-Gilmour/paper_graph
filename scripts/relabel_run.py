"""Relabel an existing run in PostgreSQL without crawling or clustering.

This script:
 - Loads papers (doi, title, cluster, sub_cluster, x,y) for a given run_id
 - Builds light-weight core document samples per sub-cluster
 - Runs LLM labeling for sub-clusters and parent clusters
 - Writes labels back to clusters/sub_clusters tables (title fields only)

Usage:
  python scripts/relabel_run.py --run-id 33 --precision 8bit --seed 42 --temperature 0.0 --show-prompts
"""
import argparse
import os
import random
from collections import defaultdict

import psycopg2

from data_pipeline.config.settings import get_config
from data_pipeline.labeling.llm_client import LLMClient
from data_pipeline.labeling.cluster_labeler import ClusterLabeler
from data_pipeline.labeling.prompts import format_sub_cluster_prompt, format_parent_cluster_prompt


def get_active_run_id(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM pipeline_runs WHERE is_active = TRUE")
        row = cur.fetchone()
        return row[0] if row else None


def fetch_papers(conn, run_id: int):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT doi, COALESCE(title,''), cluster, sub_cluster, COALESCE(x,0.0), COALESCE(y,0.0)
            FROM papers
            WHERE run_id = %s AND cluster IS NOT NULL
            """,
            (run_id,),
        )
        return cur.fetchall()


def compute_sub_sizes(papers):
    sizes = defaultdict(int)
    for _doi, _title, cid, sid, _x, _y in papers:
        if sid is not None:
            sizes[(cid, sid)] += 1
    return sizes


def upsert_labels(conn, run_id: int, parent_labels: dict, sub_labels: dict, sub_sizes: dict):
    with conn.cursor() as cur:
        # Parent clusters: update title, leave size/centroid unchanged
        for cid, title in parent_labels.items():
            cur.execute(
                """
                INSERT INTO clusters (run_id, id, title)
                VALUES (%s, %s, %s)
                ON CONFLICT (run_id, id) DO UPDATE SET title = EXCLUDED.title
                """,
                (run_id, cid, title),
            )
        # Sub-clusters: update title
        for (cid, sid), title in sub_labels.items():
            cur.execute(
                """
                INSERT INTO sub_clusters (run_id, cluster_id, sub_cluster_id, title)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (run_id, cluster_id, sub_cluster_id) DO UPDATE SET title = EXCLUDED.title
                """,
                (run_id, cid, sid, title),
            )
    conn.commit()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", type=int, default=None, help="Run ID to relabel (defaults to active)")
    ap.add_argument("--k-per-sub", type=int, default=12, help="Titles sampled per sub-cluster")
    ap.add_argument("--precision", type=str, default=os.getenv("PIPELINE_LABELING_PRECISION", "8bit"),
                    choices=["8bit", "4bit", "bf16"], help="LLM precision override")
    ap.add_argument("--seed", type=int, default=42, help="Random/LLM seed for reproducibility")
    ap.add_argument("--temperature", type=float, default=0.0, help="LLM temperature (0.0 recommended)")
    ap.add_argument("--show-prompts", action="store_true", help="Print sanitized prompt previews")
    args = ap.parse_args()

    cfg = get_config()
    random.seed(args.seed)

    conn = psycopg2.connect(cfg.export.database_url)
    try:
        run_id = args.run_id
        if run_id is None:
            run_id = get_active_run_id(conn)
        if not run_id:
            print("No run_id provided and no active run; aborting")
            return
        print(f"Relabeling run: {run_id}")

        rows = fetch_papers(conn, run_id)
        if not rows:
            print("No papers found for run; aborting")
            return
        print(f"Loaded {len(rows)} papers")

        # Build samples for sub-clusters
        titles_by_sub = defaultdict(list)
        cluster_ids = set()
        for doi, title, cid, sid, _x, _y in rows:
            cluster_ids.add(cid)
            if sid is not None and title:
                titles_by_sub[(cid, sid)].append(title)

        # Sample per sub-cluster
        sub_prompts = {}
        for key, titles in titles_by_sub.items():
            random.shuffle(titles)
            take = titles[: args.k_per_sub]
            keywords = " ".join(take[:3])[:80]
            prompt = format_sub_cluster_prompt(keywords, take)
            sub_prompts[key] = prompt
            if args.show_prompts and len(sub_prompts) <= 3:
                print(f"\n[Prompt] Sub {key}\n" + "\n".join(prompt.splitlines()[:20]) + "\n...")

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

        # Generate sub labels
        sub_keys = list(sub_prompts.keys())
        sub_texts = [sub_prompts[k] for k in sub_keys]
        print(f"Generating {len(sub_texts)} sub-cluster labels...")
        sub_responses = llm.generate(sub_texts)
        sub_labels = {}
        for key, resp in zip(sub_keys, sub_responses):
            sub_labels[key] = llm.parse_sub_cluster_label(resp)
            if args.show_prompts:
                print(f"Sub {key}: {sub_labels[key]}")

        # Parent labels
        sub_sizes = compute_sub_sizes(rows)
        parent_to_sub = defaultdict(list)
        for (cid, sid) in sub_labels.keys():
            parent_to_sub[cid].append((cid, sid))

        parent_prompts = {}
        for cid, subkeys in parent_to_sub.items():
            topics = []
            for key in subkeys:
                topics.append((sub_labels.get(key, ""), sub_sizes.get(key, 0)))
            topics.sort(key=lambda x: -x[1])
            prompt = format_parent_cluster_prompt(topics[:10])
            parent_prompts[cid] = prompt
            if args.show_prompts and len(parent_prompts) <= 3:
                print(f"\n[Prompt] Parent {cid}\n" + "\n".join(prompt.splitlines()[:20]) + "\n...")

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
        upsert_labels(conn, run_id, parent_labels, sub_labels, sub_sizes)
        print("✓ Relabeling complete and written to database")

    finally:
        conn.close()


if __name__ == "__main__":
    main()




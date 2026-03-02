"""Quick smoke test for labeling prompts and parsing.

Reads a small sample from the active run in Postgres and:
 - Builds sub-cluster prompts from ~10 titles per sub-cluster
 - Builds parent prompts from sub-cluster labels + counts
 - Optionally runs the LLM in deterministic mode (seed + temperature=0)
 - Prints parsed labels to stdout

Usage:
  python scripts/labeling_smoke.py --k 3 --dry-run --show-prompts
  python scripts/labeling_smoke.py --k 3 --precision 8bit --seed 42 --temperature 0.0
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


def sample_titles_by_subcluster(conn, run_id: int, k: int, per_sub: int = 10):
    """Return { (cluster_id, sub_id): [titles...] } for k random sub-clusters."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT cluster, sub_cluster, title
            FROM papers
            WHERE run_id = %s AND sub_cluster IS NOT NULL AND title IS NOT NULL
            """,
            (run_id,),
        )
        rows = cur.fetchall()

    by_sub = defaultdict(list)
    for cid, sid, title in rows:
        by_sub[(cid, sid)].append(title)

    keys = list(by_sub.keys())
    random.shuffle(keys)
    keys = keys[:k]

    out = {}
    for key in keys:
        titles = by_sub[key][:per_sub]
        if titles:
            out[key] = titles
    return out


def get_parent_topics(conn, run_id: int, k: int, sub_labels: dict):
    """Return at most k parent clusters with their (label,count) topic tuples."""
    # Count sub sizes
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
        counts = {(cid, sid): n for cid, sid, n in cur.fetchall()}

    # Group sub-keys by parent
    parent_to_subkeys = defaultdict(list)
    for (cid, sid) in sub_labels.keys():
        parent_to_subkeys[cid].append((cid, sid))

    parents = list(parent_to_subkeys.keys())
    random.shuffle(parents)
    parents = parents[:k]

    parent_topics = {}
    for cid in parents:
        topics = []
        for key in parent_to_subkeys[cid]:
            if key in sub_labels:
                topics.append((sub_labels[key], counts.get(key, 0)))
        topics.sort(key=lambda x: -x[1])
        parent_topics[cid] = topics[:10]
    return parent_topics


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=3, help="Number of sub/parent clusters to sample")
    ap.add_argument("--per-sub", type=int, default=10, help="Titles per sub-cluster")
    ap.add_argument("--dry-run", action="store_true", help="Only build prompts, do not call LLM")
    ap.add_argument("--show-prompts", action="store_true", help="Print sanitized prompt previews")
    ap.add_argument("--precision", type=str, default=os.getenv("PIPELINE_LABELING_PRECISION", "8bit"),
                    choices=["8bit", "4bit", "bf16"], help="LLM precision override")
    ap.add_argument("--seed", type=int, default=42, help="Random/LLM seed for reproducibility")
    ap.add_argument("--temperature", type=float, default=0.0, help="LLM temperature (0.0 recommended for determinism)")
    args = ap.parse_args()

    cfg = get_config()
    random.seed(args.seed)

    conn = psycopg2.connect(cfg.export.database_url)
    try:
        run_id = get_active_run_id(conn)
        if not run_id:
            print("No active run; aborting")
            return
        print(f"Active run: {run_id}")

        # --- Sub-cluster prompts ---
        samples = sample_titles_by_subcluster(conn, run_id, k=args.k, per_sub=args.per_sub)
        print(f"Sampled {len(samples)} sub-clusters")

        sub_prompts = {}
        for (cid, sid), titles in samples.items():
            # crude keywords placeholder to keep CLI fast; the production TF-IDF is in ClusterLabeler
            keywords = " ".join(titles[:3])[:80]
            prompt = format_sub_cluster_prompt(keywords, titles[:10])
            sub_prompts[(cid, sid)] = prompt
            if args.show_prompts:
                print(f"\n[Prompt] Sub ({cid},{sid})\n" + "\n".join(prompt.splitlines()[:20]) + "\n...")

        if args.dry_run:
            print("\nDry-run: built sub-cluster prompts only.")
            return

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
        labeler = ClusterLabeler(llm, show_prompts=args.show_prompts)

        # Generate sub labels
        sub_keys = list(sub_prompts.keys())
        sub_texts = [sub_prompts[k] for k in sub_keys]
        sub_responses = llm.generate(sub_texts)
        sub_labels = {}
        for key, resp in zip(sub_keys, sub_responses):
            sub_labels[key] = llm.parse_sub_cluster_label(resp)
            print(f"Sub {key}: {sub_labels[key]}")

        # --- Parent prompts ---
        parent_topics = get_parent_topics(conn, run_id, k=args.k, sub_labels=sub_labels)
        parent_prompts = {}
        for cid, topics in parent_topics.items():
            prompt = format_parent_cluster_prompt(topics)
            parent_prompts[cid] = prompt
            if args.show_prompts:
                print(f"\n[Prompt] Parent {cid}\n" + "\n".join(prompt.splitlines()[:20]) + "\n...")

        parent_ids = list(parent_prompts.keys())
        parent_texts = [parent_prompts[cid] for cid in parent_ids]
        parent_responses = llm.generate(parent_texts)
        for cid, resp in zip(parent_ids, parent_responses):
            reason, label = llm.parse_parent_cluster_label(resp)
            print(f"Parent {cid}: {label}  —  reason: {reason}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()




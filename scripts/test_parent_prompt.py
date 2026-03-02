"""Test parent cluster prompt generation and parsing."""
import psycopg2
from collections import defaultdict

from data_pipeline.config.settings import get_config
from data_pipeline.labeling.prompts import format_parent_cluster_prompt
from data_pipeline.labeling.llm_client import LLMClient

def main():
    cfg = get_config()
    conn = psycopg2.connect(cfg.export.database_url)
    run_id = 33
    
    # Load sub-labels
    with conn.cursor() as cur:
        cur.execute(
            "SELECT cluster_id, sub_cluster_id, title FROM sub_clusters WHERE run_id = %s",
            (run_id,),
        )
        sub_labels = {(cid, sid): title for cid, sid, title in cur.fetchall()}
        
        # Get sizes
        cur.execute(
            "SELECT cluster, sub_cluster, COUNT(*) FROM papers WHERE run_id = %s AND sub_cluster IS NOT NULL GROUP BY cluster, sub_cluster",
            (run_id,),
        )
        sub_sizes = {(cid, sid): n for cid, sid, n in cur.fetchall()}
    
    conn.close()
    
    # Build prompt for cluster 0
    topics = [(sub_labels.get((0, sid), ""), sub_sizes.get((0, sid), 0)) for sid in range(20) if (0, sid) in sub_labels]
    topics.sort(key=lambda x: -x[1])
    topics = topics[:10]
    
    print("\n=== Cluster 0 Topics ===")
    for label, count in topics:
        print(f"  • {label}  (n={count})")
    
    prompt = format_parent_cluster_prompt(topics)
    print("\n=== Generated Prompt ===")
    print(prompt[:500])
    print("...")
    
    # Test LLM generation
    llm = LLMClient(
        model_name=cfg.labeling.model_name,
        hf_token=cfg.labeling.hf_token,
        batch_size=1,
        max_new_tokens=120,
        temperature=0.0,
        precision="8bit",
        deterministic=True,
        seed=42,
    )
    
    print("\n=== Generating label ===")
    responses = llm.generate([prompt])
    raw = responses[0]
    
    print("\n=== Raw LLM Response ===")
    print(raw)
    
    print("\n=== Parsed ===")
    reason, label = llm.parse_parent_cluster_label(raw)
    print(f"Reason: {reason}")
    print(f"Label: {label}")

if __name__ == "__main__":
    main()






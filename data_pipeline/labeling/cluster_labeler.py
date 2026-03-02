"""
Main cluster labeler coordinating sub-cluster and parent cluster labeling.

Extracted from cluster_labeler.py.
"""

from typing import Dict, Tuple, List
from collections import defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
import networkx as nx

from data_pipeline.labeling.llm_client import LLMClient
from data_pipeline.labeling.prompts import format_sub_cluster_prompt, format_parent_cluster_prompt
from data_pipeline.utils.logging import get_logger
from data_pipeline.utils.progress import progress_bar

logger = get_logger("labeling.cluster_labeler")


class ClusterLabeler:
    """
    Generates human-readable labels for clusters using LLMs.
    
    Handles both sub-cluster and parent cluster labeling.
    """
    
    def __init__(
        self,
        llm_client: LLMClient,
        top_heavy: int = 10,
        show_prompts: bool = False,
    ):
        """
        Initialize labeler.
        
        Args:
            llm_client: LLM client for generation
            top_heavy: Number of top sub-clusters to emphasize in parent labels
        """
        self.llm = llm_client
        self.top_heavy = top_heavy
        self.show_prompts = show_prompts
        self.tfidf = TfidfVectorizer(
            ngram_range=(1, 2),
            stop_words="english",
            min_df=1,
            max_features=5000
        )
    
    def label_sub_clusters(
        self,
        graph: nx.DiGraph,
        core_docs: Dict[Tuple[int, int], List[str]],
    ) -> Dict[Tuple[int, int], str]:
        """
        Generate labels for sub-clusters.
        
        Args:
            graph: NetworkX graph with paper nodes
            core_docs: {(cluster_id, sub_id): [core_dois]}
        
        Returns:
            {(cluster_id, sub_id): label}
        """
        logger.info(f"Labeling {len(core_docs)} sub-clusters")
        
        # Build prompts
        prompts = []
        keys = []
        skipped = 0
        
        logger.info("Building prompts from core documents...")
        for (cluster_id, sub_id), dois in core_docs.items():
            # Extract titles and abstracts
            texts = []
            for doi in dois:
                if doi not in graph:
                    continue
                title = graph.nodes[doi].get("title", "")
                abstract = graph.nodes[doi].get("abstract", "")
                if title:
                    texts.append(f"{title} — {abstract}")
            
            if not texts:
                logger.warning(f"Sub-cluster ({cluster_id}, {sub_id}) has no valid texts - skipping")
                skipped += 1
                continue
            
            # Extract keywords with TF-IDF
            try:
                tf_matrix = self.tfidf.fit_transform(texts)
                features = self.tfidf.get_feature_names_out()
                top_idx = tf_matrix.sum(axis=0).A1.argsort()[-5:][::-1]
                keywords = ", ".join(features[i] for i in top_idx)
            except Exception as e:
                logger.debug(f"TF-IDF failed for sub-cluster ({cluster_id}, {sub_id}): {e}")
                keywords = "biomedical"
            
            # Format titles for prompt
            title_lines = [t.split("—")[0].strip() for t in texts]
            
            prompt = format_sub_cluster_prompt(keywords, title_lines[:10])
            prompts.append(prompt)
            keys.append((cluster_id, sub_id))

            if self.show_prompts and len(prompts) <= 3:
                # Log a sanitized/truncated prompt preview
                preview = "\n".join(prompt.splitlines()[:20])
                logger.info(f"[debug] Sub-cluster prompt preview for ({cluster_id},{sub_id}):\n{preview}\n...")
        
        if skipped > 0:
            logger.warning(f"⚠ Skipped {skipped}/{len(core_docs)} sub-clusters (no valid texts)")
        
        logger.info(f"Built {len(prompts)} prompts")
        
        # Generate labels
        logger.info(f"Generating {len(prompts)} sub-cluster labels with LLM...")
        responses = self.llm.generate(prompts)
        
        # Validate response count
        if len(responses) != len(prompts):
            logger.error(f"Response count mismatch: {len(responses)} responses for {len(prompts)} prompts")
        
        # Parse responses
        labels = {}
        failed_parse = 0
        
        logger.info("Parsing LLM responses...")
        for key, response in zip(keys, responses):
            if not response or not response.strip():
                logger.warning(f"Empty response for sub-cluster {key}")
                label = "Unlabeled Cluster"
                failed_parse += 1
            else:
                label = self.llm.parse_sub_cluster_label(response)
            
            labels[key] = label
            logger.debug(f"Sub-cluster {key}: {label}")
        
        if failed_parse > 0:
            logger.warning(f"⚠ {failed_parse}/{len(prompts)} labels failed to parse")
        else:
            logger.info(f"✓ Successfully parsed all {len(labels)} sub-cluster labels")
        
        # Log top 5 sub-cluster labels as examples
        if labels:
            logger.info("\n📋 Sample sub-cluster labels (top 5):")
            for i, (key, label) in enumerate(list(labels.items())[:5]):
                logger.info(f"  {i+1}. Cluster {key}: '{label}'")
            if len(labels) > 5:
                logger.info(f"  ... and {len(labels) - 5} more")
        
        return labels
    
    def label_parent_clusters(
        self,
        clusters: Dict[str, int],
        sub_clusters: Dict[str, int],
        sub_labels: Dict[Tuple[int, int], str],
    ) -> Dict[int, str]:
        """
        Generate labels for parent clusters.
        
        Args:
            clusters: {doi: cluster_id}
            sub_clusters: {doi: sub_cluster_id}
            sub_labels: {(cluster_id, sub_id): label}
        
        Returns:
            {cluster_id: label}
        """
        logger.info(f"Labeling parent clusters...")
        
        # Group sub-clusters by parent
        parent_subs = defaultdict(list)
        for doi, cluster_id in clusters.items():
            sub_id = sub_clusters.get(doi)
            if sub_id is not None:
                parent_subs[cluster_id].append((cluster_id, sub_id))
        
        # Count sub-cluster sizes
        sub_sizes = defaultdict(int)
        for doi, cluster_id in clusters.items():
            sub_id = sub_clusters.get(doi)
            if sub_id is not None:
                sub_sizes[(cluster_id, sub_id)] += 1
        
        logger.info(f"Found {len(parent_subs)} parent clusters")
        
        # Build prompts
        prompts = []
        cluster_ids = []
        skipped = 0
        
        logger.info("Building prompts from sub-cluster labels...")
        for cluster_id, sub_keys in parent_subs.items():
            # Get sub-cluster labels and sizes
            topics = []
            for key in sub_keys:
                if key in sub_labels:
                    label = sub_labels[key]
                    size = sub_sizes[key]
                    topics.append((label, size))
            
            if not topics:
                logger.warning(f"Parent cluster {cluster_id} has no labeled sub-clusters - skipping")
                skipped += 1
                continue
            
            # Sort by size (descending)
            topics.sort(key=lambda x: -x[1])
            
            # Take top_heavy
            topics = topics[:self.top_heavy]
            
            prompt = format_parent_cluster_prompt(topics)
            prompts.append(prompt)
            cluster_ids.append(cluster_id)

            if self.show_prompts and len(prompts) <= 3:
                preview = "\n".join(prompt.splitlines()[:20])
                logger.info(f"[debug] Parent prompt preview for cluster {cluster_id}:\n{preview}\n...")
        
        if skipped > 0:
            logger.warning(f"⚠ Skipped {skipped}/{len(parent_subs)} parent clusters (no labeled sub-clusters)")
        
        logger.info(f"Built {len(prompts)} prompts")
        
        # Generate labels
        logger.info(f"Generating {len(prompts)} parent cluster labels with LLM...")
        responses = self.llm.generate(prompts)
        
        # Validate response count
        if len(responses) != len(prompts):
            logger.error(f"Response count mismatch: {len(responses)} responses for {len(prompts)} prompts")
        
        # Parse responses
        labels = {}
        failed_parse = 0
        
        logger.info("Parsing LLM responses...")
        for cluster_id, response in zip(cluster_ids, responses):
            if not response or not response.strip():
                logger.warning(f"Empty response for parent cluster {cluster_id}")
                label = "Unlabeled Cluster"
                failed_parse += 1
            else:
                _, label = self.llm.parse_parent_cluster_label(response)
            
            labels[cluster_id] = label
            logger.debug(f"Parent cluster {cluster_id}: {label}")
        
        if failed_parse > 0:
            logger.warning(f"⚠ {failed_parse}/{len(prompts)} labels failed to parse")
        else:
            logger.info(f"✓ Successfully parsed all {len(labels)} parent cluster labels")
        
        # Log all parent cluster labels (usually small number)
        if labels:
            logger.info("\n📋 Parent cluster labels:")
            for cluster_id, label in sorted(labels.items()):
                logger.info(f"  Cluster {cluster_id}: '{label}'")
        
        return labels


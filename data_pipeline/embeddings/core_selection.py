"""
Core document selection for cluster labeling.

Selects K most representative papers per cluster.
Extracted from embed_core.py.
"""

from typing import Dict, List, Tuple
from collections import defaultdict
import numpy as np

from data_pipeline.utils.logging import get_logger

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

logger = get_logger("embeddings.core_selection")


class CoreDocumentSelector:
    """
    Selects K most representative documents per cluster.
    
    Uses embedding centroids and nearest neighbor search.
    """
    
    def __init__(self, k_core: int = 50):
        """
        Initialize selector.
        
        Args:
            k_core: Number of core documents per cluster
        """
        self.k_core = k_core
    
    def select_core_documents(
        self,
        embeddings: Dict[str, np.ndarray],
        clusters: Dict[str, int],
        sub_clusters: Dict[str, int] = None,
    ) -> Dict[Tuple[int, int], List[str]]:
        """
        Select core documents for each (cluster, sub_cluster) pair.
        
        Args:
            embeddings: {doi: embedding_vector}
            clusters: {doi: cluster_id}
            sub_clusters: {doi: sub_cluster_id} (optional)
        
        Returns:
            {(cluster_id, sub_cluster_id): [core_dois]}
        """
        logger.info(f"Selecting K={self.k_core} core documents per cluster")
        
        # Group by cluster and sub-cluster
        groups = defaultdict(list)
        for doi in embeddings.keys():
            if doi not in clusters:
                continue
            
            cluster_id = clusters[doi]
            sub_id = sub_clusters.get(doi, 0) if sub_clusters else 0
            groups[(cluster_id, sub_id)].append(doi)
        
        # Select core docs for each group
        core_docs = {}
        for (cluster_id, sub_id), dois in groups.items():
            if len(dois) <= self.k_core:
                core_docs[(cluster_id, sub_id)] = dois
                continue
            
            # Compute centroid
            vecs = np.stack([embeddings[d] for d in dois])
            centroid = vecs.mean(axis=0)
            
            # Select nearest to centroid
            if FAISS_AVAILABLE:
                selected = self._select_with_faiss(vecs, centroid, dois)
            else:
                selected = self._select_with_numpy(vecs, centroid, dois)
            
            core_docs[(cluster_id, sub_id)] = selected
        
        total_selected = sum(len(v) for v in core_docs.values())
        logger.info(f"Selected {total_selected} core documents across {len(core_docs)} groups")
        
        return core_docs
    
    def _select_with_numpy(
        self,
        vecs: np.ndarray,
        centroid: np.ndarray,
        dois: List[str]
    ) -> List[str]:
        """Select using numpy cosine similarity."""
        # Cosine similarity
        sim = vecs @ centroid / (np.linalg.norm(vecs, axis=1) * np.linalg.norm(centroid))
        
        # Top K
        top_indices = sim.argsort()[-self.k_core:][::-1]
        return [dois[i] for i in top_indices]
    
    def _select_with_faiss(
        self,
        vecs: np.ndarray,
        centroid: np.ndarray,
        dois: List[str]
    ) -> List[str]:
        """Select using FAISS (faster for large clusters)."""
        # Normalize
        vecs_norm = vecs.copy().astype(np.float32)
        faiss.normalize_L2(vecs_norm)
        
        centroid_norm = centroid.copy().astype(np.float32).reshape(1, -1)
        faiss.normalize_L2(centroid_norm)
        
        # Build index
        index = faiss.IndexFlatIP(vecs_norm.shape[1])
        index.add(vecs_norm)
        
        # Search
        _, indices = index.search(centroid_norm, min(self.k_core, len(dois)))
        
        return [dois[i] for i in indices[0]]


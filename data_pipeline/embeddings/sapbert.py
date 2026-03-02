"""
SapBERT encoder for generating paper embeddings.

Extracted from lib_clabel.py and embed_core.py.
"""

from typing import List, Dict
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel
from tqdm import tqdm

from data_pipeline.utils.logging import get_logger

logger = get_logger("embeddings.sapbert")


class SapBERTEncoder:
    """
    SapBERT encoder for generating biomedical text embeddings.
    
    Uses CLS token embeddings from SapBERT-PubMedBERT model.
    """
    
    DEFAULT_MODEL = "cambridgeltl/SapBERT-from-PubMedBERT-fulltext"
    CLS_DIM = 768
    
    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        batch_size: int = 64,
        device: str = None,
    ):
        """
        Initialize encoder.
        
        Args:
            model_name: HuggingFace model name
            batch_size: Encoding batch size
            device: Device ('cuda' or 'cpu', auto-detect if None)
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        
        # Load model and tokenizer (lazy)
        self.tokenizer = None
        self.model = None
    
    def _ensure_loaded(self):
        """Lazy load model and tokenizer."""
        if self.model is None:
            logger.info("=" * 60)
            logger.info(f"Loading SapBERT model: {self.model_name}")
            logger.info(f"Device: {self.device}")
            logger.info("=" * 60)
            
            logger.info("Loading tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            logger.info(f"✓ Tokenizer loaded (vocab size: {len(self.tokenizer)})")
            
            logger.info("Loading model (downloading from HuggingFace if not cached)...")
            self.model = AutoModel.from_pretrained(self.model_name)
            logger.info("✓ Model loaded")
            
            logger.info(f"Moving to {self.device}...")
            self.model = self.model.to(self.device)
            self.model.eval()
            
            # Report memory usage
            if torch.cuda.is_available():
                allocated = torch.cuda.memory_allocated() / 1024**3
                reserved = torch.cuda.memory_reserved() / 1024**3
                logger.info(f"✓ Model ready on GPU ({allocated:.1f}GB allocated, {reserved:.1f}GB reserved)")
            else:
                logger.info("✓ Model ready on CPU")
            
            logger.info("=" * 60)
    
    @torch.no_grad()
    def encode(self, texts: List[str]) -> np.ndarray:
        """
        Encode texts to embeddings.
        
        Args:
            texts: List of text strings
        
        Returns:
            Array of shape (len(texts), 768)
        """
        if not texts:
            logger.warning("No texts provided to encode()")
            return np.empty((0, self.CLS_DIM), dtype=np.float32)
        
        self._ensure_loaded()
        
        logger.info(f"Encoding {len(texts)} texts with SapBERT...")
        num_batches = (len(texts) + self.batch_size - 1) // self.batch_size
        logger.info(f"Processing {num_batches} batches (batch_size={self.batch_size})")
        
        embeddings = np.empty((len(texts), self.CLS_DIM), dtype=np.float32)
        
        # Progress bar (disable=None auto-detects TTY)
        # Also log explicitly for Docker logs
        with tqdm(total=len(texts), desc="Encoding", unit="text", disable=None, ncols=80, leave=True) as pbar:
            for i in range(0, len(texts), self.batch_size):
                batch_texts = texts[i:i+self.batch_size]
                batch_num = (i // self.batch_size) + 1
                
                # Log every 10 batches to avoid spam
                if batch_num % 10 == 1 or batch_num == num_batches:
                    logger.info(f"Encoding batch {batch_num}/{num_batches} ({i}/{len(texts)} texts)...")
                
                # Tokenize
                encoded = self.tokenizer(
                    batch_texts,
                    padding=True,
                    truncation=True,
                    return_tensors="pt"
                ).to(self.device)
                
                # Get CLS embeddings
                outputs = self.model(**encoded)
                cls_embeddings = outputs.last_hidden_state[:, 0, :]
                
                # Store
                embeddings[i:i+len(batch_texts)] = cls_embeddings.cpu().numpy()
                pbar.update(len(batch_texts))
        
        logger.info(f"✓ Encoded {len(texts)} texts to shape {embeddings.shape}")
        return embeddings
    
    def encode_papers(
        self,
        graph,
        doi_list: List[str]
    ) -> Dict[str, np.ndarray]:
        """
        Encode paper titles from graph.
        
        Args:
            graph: NetworkX graph with paper nodes
            doi_list: List of DOIs to encode
        
        Returns:
            Dictionary {doi: embedding_vector}
        """
        logger.info(f"Extracting titles from {len(doi_list)} papers...")
        
        # Extract titles
        titles = []
        valid_dois = []
        missing_titles = 0
        
        for doi in doi_list:
            if doi in graph:
                title = graph.nodes[doi].get("title", "")
                if title:
                    titles.append(title)
                    valid_dois.append(doi)
                else:
                    missing_titles += 1
            else:
                logger.warning(f"DOI not in graph: {doi}")
        
        if missing_titles > 0:
            logger.warning(f"⚠ {missing_titles}/{len(doi_list)} papers missing titles")
        
        logger.info(f"Found {len(titles)} valid titles")
        
        # Encode
        embeddings = self.encode(titles)
        
        # Build dict
        result = {doi: embeddings[i] for i, doi in enumerate(valid_dois)}
        logger.info(f"✓ Created {len(result)} embeddings")
        
        return result


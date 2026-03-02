"""LLM client for label generation."""

import json
import ast
import re
from typing import List, Tuple, Optional
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline, BitsAndBytesConfig
from tqdm import tqdm

from data_pipeline.utils.logging import get_logger

logger = get_logger("labeling.llm_client")

# Regex for extracting labels
TAG_RE = re.compile(r"<label>(.*?)</label>", re.S)

# Forbidden words in labels
FORBIDDEN_WORDS = {"biomedical", "taxonomy", "keywords", "miscellaneous", "other", "unknown", "???"}


class LLMClient:
    """
    Client for LLM-based label generation.
    
    Uses Llama 3.1 for generating cluster labels.
    """
    
    def __init__(
        self,
        model_name: str = "meta-llama/Meta-Llama-3.1-8B-Instruct",
        hf_token: str = None,
        batch_size: int = 8,
        max_new_tokens: int = 120,
        temperature: float = 0.12,
        device: str = None,
        load_in_4bit: bool = True,  # Back-compat flag (kept, but overridden by precision if set)
        precision: str = None,      # New: "8bit", "4bit", or "bf16"
        deterministic: bool = False,
        seed: Optional[int] = None,
    ):
        """Initialize LLM client."""
        self.model_name = model_name
        self.hf_token = hf_token
        self.batch_size = batch_size
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        # Precision precedence: explicit precision arg > load_in_4bit flag
        # precision None => infer from load_in_4bit
        if precision is None:
            self.precision = "4bit" if load_in_4bit else "bf16"
        else:
            self.precision = precision.lower()
        self.load_in_4bit = (self.precision == "4bit")
        self.deterministic = deterministic
        self.seed = seed
        
        self.pipeline = None
    
    def _ensure_loaded(self):
        """Lazy load model."""
        if self.pipeline is not None:
            return
        
        # Free up GPU memory before loading LLM
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.info("Cleared GPU cache before loading LLM")
        
        logger.info("=" * 60)
        logger.info(f"Loading LLM: {self.model_name}")
        logger.info(f"Device: {self.device}")
        logger.info(f"Batch size: {self.batch_size}")
        logger.info(f"Quantization/precision: {self.precision}")
        logger.info("=" * 60)
        
        # Set seed if requested (helps reproducibility)
        if self.seed is not None:
            try:
                import random, numpy as np
                random.seed(self.seed)
                np.random.seed(self.seed)
                torch.manual_seed(self.seed)
                if torch.cuda.is_available():
                    torch.cuda.manual_seed_all(self.seed)
                logger.info(f"Seed set to {self.seed}")
            except Exception as e:
                logger.warning(f"Failed to set seed: {e}")

        logger.info("Step 1/3: Loading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            token=self.hf_token,
            use_fast=True,
            padding_side="left",
        )
        logger.info(f"✓ Tokenizer loaded (vocab size: {len(tokenizer)})")
        
        logger.info("Step 2/3: Loading model (this may take a few minutes)...")
        logger.info("  - Downloading from HuggingFace if not cached")
        if self.precision in ("4bit", "8bit"):
            logger.info(f"  - Loading in {self.precision} quantization")
        logger.info("  - Loading to GPU memory")
        
        # Configure quantization
        quantization_config = None
        if self.precision == "4bit":
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
            logger.info("  - Using NF4 4-bit quantization with bfloat16 compute")
        elif self.precision == "8bit":
            quantization_config = BitsAndBytesConfig(load_in_8bit=True)
            logger.info("  - Using 8-bit quantization")
        
        model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            token=self.hf_token,
            quantization_config=quantization_config,
            torch_dtype=(torch.bfloat16 if self.precision == "bf16" else None),
            device_map="auto",
            low_cpu_mem_usage=True,  # Reduce RAM usage during loading
            attn_implementation="flash_attention_2" if self._has_flash_attention() else "sdpa",
        )
        
        # Report memory usage
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated() / 1024**3
            reserved = torch.cuda.memory_reserved() / 1024**3
            logger.info(f"✓ Model loaded to GPU ({allocated:.1f}GB allocated, {reserved:.1f}GB reserved)")
            if self.precision == "4bit":
                logger.info(f"  (4-bit quantization saved ~{15.4 - allocated:.1f}GB vs full precision)")
        else:
            logger.info("✓ Model loaded to CPU")
        
        logger.info("Step 3/3: Creating generation pipeline...")
        self.pipeline = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            device_map="auto",
            batch_size=self.batch_size,
            max_new_tokens=self.max_new_tokens,
            temperature=self.temperature,
            do_sample=not self.deterministic and (self.temperature is not None and self.temperature > 0.0),
            pad_token_id=tokenizer.eos_token_id,
            return_full_text=False,
        )
        
        self.pipeline.tokenizer.pad_token_id = tokenizer.eos_token_id
        logger.info("✓ Pipeline ready!")
        logger.info("=" * 60)
    
    def _has_flash_attention(self) -> bool:
        """Check if flash_attention_2 is available."""
        try:
            import flash_attn
            logger.info("  - Using Flash Attention 2 (faster + less memory)")
            return True
        except ImportError:
            logger.info("  - Using SDPA attention (flash_attn not installed)")
            return False
    
    def generate(self, prompts: List[str]) -> List[str]:
        """Generate text from prompts."""
        if not prompts:
            logger.warning("No prompts provided to generate()")
            return []
        
        self._ensure_loaded()
        
        logger.info(f"Generating {len(prompts)} labels...")
        num_batches = (len(prompts) + self.batch_size - 1) // self.batch_size
        logger.info(f"Processing {num_batches} batches (batch_size={self.batch_size})")
        
        results = []
        failed_count = 0
        
        # Progress bar for batches (disable=None auto-detects if in TTY)
        # Also add explicit logging since tqdm doesn't show in Docker logs
        with tqdm(total=len(prompts), desc="Generating labels", unit="label", 
                  disable=None, ncols=80, leave=True) as pbar:
            for batch_idx in range(0, len(prompts), self.batch_size):
                batch = prompts[batch_idx:batch_idx+self.batch_size]
                batch_num = batch_idx // self.batch_size + 1
                
                # Log progress explicitly for Docker logs
                logger.info(f"Processing batch {batch_num}/{num_batches} ({len(batch)} prompts)...")
                
                try:
                    # Note: Don't override batch_size here - use the one from __init__
                    outputs = self.pipeline(batch)
                    for output in outputs:
                        text = output[0]["generated_text"] if isinstance(output, list) else output["generated_text"]
                        results.append(text)
                    logger.info(f"✓ Batch {batch_num}/{num_batches} complete ({len(results)}/{len(prompts)} total)")
                    pbar.update(len(batch))
                    
                except RuntimeError as e:
                    if "out of memory" in str(e).lower():
                        logger.warning(f"⚠ GPU OOM on batch {batch_num}/{num_batches}, retrying with batch_size=1")
                        torch.cuda.empty_cache()
                        
                        # Retry each prompt individually
                        for prompt_idx, prompt in enumerate(batch):
                            try:
                                logger.debug(f"Retrying prompt {batch_idx + prompt_idx + 1}/{len(prompts)}")
                                output = self.pipeline([prompt])[0]
                                text = output[0]["generated_text"] if isinstance(output, list) else output["generated_text"]
                                results.append(text)
                                pbar.update(1)
                            except Exception as e2:
                                logger.error(f"❌ Failed to generate label {batch_idx + prompt_idx + 1}: {e2}")
                                results.append("")  # Empty fallback
                                failed_count += 1
                                pbar.update(1)
                        logger.info(f"✓ Batch {batch_num}/{num_batches} retried ({len(results)}/{len(prompts)} total)")
                    else:
                        logger.error(f"❌ Generation failed on batch {batch_num}/{num_batches}: {e}")
                        # Add empty results for this batch
                        results.extend([""] * len(batch))
                        failed_count += len(batch)
                        pbar.update(len(batch))
                        logger.warning(f"Skipped batch {batch_num}/{num_batches} ({len(results)}/{len(prompts)} total)")
        
        if failed_count > 0:
            logger.warning(f"⚠ {failed_count}/{len(prompts)} labels failed to generate")
        else:
            logger.info(f"✓ Successfully generated all {len(prompts)} labels")
        
        return results
    
    @staticmethod
    def parse_sub_cluster_label(response: str) -> str:
        """Extract label from sub-cluster response."""
        match = TAG_RE.search(response)
        if match:
            return match.group(1).strip()
        return response.strip()
    
    @staticmethod
    def parse_parent_cluster_label(response: str) -> Tuple[str, str]:
        """
        Extract (reason, label) from parent cluster response.
        
        Returns:
            (reason, label) or ("", "NO VALID TITLE") if parsing fails
        """
        # Extract from <label> tags or use whole response
        blob = response
        match = TAG_RE.search(response)
        if match:
            blob = match.group(1).strip()
        
        # Prepend JSON opening if needed
        if not blob.strip().startswith("{"):
            blob = '{"reason": ' + blob
        
        # Strip markdown fences
        if blob.startswith("```"):
            blob = re.sub(r"^```[a-z]*\n|\n```$", "", blob, flags=re.S).strip()
        
        # NEW: Extract just the JSON object, stopping at first balanced }
        # This handles cases where LLM generates code/comments after JSON
        brace_count = 0
        json_end = -1
        for i, char in enumerate(blob):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_end = i + 1
                    break
        
        if json_end > 0:
            blob = blob[:json_end]
        
        # Parse JSON
        try:
            data = json.loads(blob)
        except json.JSONDecodeError:
            try:
                data = ast.literal_eval(blob)
            except Exception:
                return "", "NO VALID TITLE"
        
        reason = str(data.get("reason", "")).strip()
        label = str(data.get("label", "")).strip()
        
        # Check for forbidden words
        if not label or any(word in label.lower() for word in FORBIDDEN_WORDS):
            return reason, "NO VALID TITLE"
        
        return reason, label


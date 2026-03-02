"""
Centralized configuration for the data pipeline.

All settings are externalized and can be overridden via environment variables.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class APIConfig(BaseModel):
    """API client configuration."""
    
    mailto: str = Field(
        default=os.getenv("PIPELINE_API_MAILTO", "your-email@example.com"),
        description="Email for Crossref/OpenAlex API requests"
    )
    delay_between_requests: float = Field(
        default=0.0,
        description="Delay between API requests (seconds)"
    )
    max_workers: int = Field(
        default=8,
        description="Max concurrent API requests"
    )
    cache_dir: Optional[Path] = Field(
        default=None,
        description="Directory for SQLite API cache"
    )


class LayoutConfig(BaseModel):
    """Graph layout configuration."""
    
    use_gpu: bool = Field(
        default=True,
        description="Use GPU acceleration if available"
    )
    fa2_iterations: int = Field(
        default=2000,
        description="ForceAtlas2 iterations"
    )
    barnes_hut_theta: float = Field(
        default=0.5,
        description="Barnes-Hut approximation parameter"
    )
    scaling_ratio: float = Field(
        default=1000.0,
        description="Layout scaling factor"
    )
    gravity: float = Field(
        default=1.5,
        description="Gravity strength"
    )
    edge_weight_influence: float = Field(
        default=1.0,
        description="Edge weight influence on layout"
    )
    jitter_tolerance: float = Field(
        default=0.09,
        description="Jitter tolerance for convergence"
    )


class ClusteringConfig(BaseModel):
    """Clustering configuration."""
    
    louvain_resolution: float = Field(
        default=1.0,
        description="Louvain resolution parameter"
    )
    sub_resolution: float = Field(
        default=1.0,
        description="Sub-cluster resolution"
    )


class EmbeddingConfig(BaseModel):
    """Embedding configuration."""
    
    model_name: str = Field(
        default="cambridgeltl/SapBERT-from-PubMedBERT-fulltext",
        description="SapBERT model name"
    )
    batch_size: int = Field(
        default=64,
        description="Batch size for encoding"
    )
    k_core: int = Field(
        default=50,
        description="Number of representative papers per cluster"
    )


class LabelingConfig(BaseModel):
    """LLM labeling configuration."""
    
    model_name: str = Field(
        default="meta-llama/Meta-Llama-3.1-8B-Instruct",
        description="LLM model for cluster labeling"
    )
    hf_token: str = Field(
        default=os.getenv("HF_TOKEN", ""),
        description="HuggingFace API token (required for gated models; set via HF_TOKEN env var)"
    )
    batch_size: int = Field(
        default=2,
        description="Batch size for LLM generation (reduced for 4-bit quantization)"
    )
    max_new_tokens: int = Field(
        default=120,
        description="Max tokens to generate"
    )
    temperature: float = Field(
        default=0.12,
        description="Sampling temperature"
    )
    # New: precision switch with env override: one of {"8bit","4bit","bf16"}
    precision: str = Field(
        default=os.getenv("PIPELINE_LABELING_PRECISION", "8bit"),
        description="LLM precision: 8bit, 4bit, or bf16"
    )
    load_in_4bit: bool = Field(
        default=True,
        description="Use 4-bit quantization (saves ~75% VRAM)"
    )


class ExportConfig(BaseModel):
    """Export configuration."""
    
    database_url: str = Field(
        default=os.getenv("DATABASE_URL", "postgresql://pg:secret@postgres:5432/litsearch"),
        description="PostgreSQL connection URL (defaults to Docker service 'postgres')"
    )
    batch_size_papers: int = Field(
        default=10_000,
        description="Batch size for paper inserts"
    )
    batch_size_edges: int = Field(
        default=10_000,
        description="Batch size for edge inserts"
    )


class PipelineConfig(BaseModel):
    """Complete pipeline configuration."""
    
    # Directories
    output_dir: Path = Field(
        default=Path("./data_pipeline_output"),
        description="Output directory for artifacts"
    )
    checkpoint_dir: Optional[Path] = Field(
        default=None,
        description="Checkpoint directory (enables resume)"
    )
    
    # Input
    seed_dois: list[str] = Field(
        default_factory=list,
        description="Seed DOIs to start graph"
    )
    seed_file: Optional[Path] = Field(
        default=None,
        description="JSON file with seed DOIs"
    )
    max_depth: int = Field(
        default=1,
        description="Citation crawl depth"
    )
    
    # Component configs
    api: APIConfig = Field(default_factory=APIConfig)
    layout: LayoutConfig = Field(default_factory=LayoutConfig)
    clustering: ClusteringConfig = Field(default_factory=ClusteringConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    labeling: LabelingConfig = Field(default_factory=LabelingConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)
    
    # Runtime
    verbose: bool = Field(
        default=False,
        description="Verbose logging"
    )
    
    class Config:
        env_prefix = "PIPELINE_"
    
    def save_to_file(self, path: Path):
        """Save config to JSON file."""
        path.write_text(self.model_dump_json(indent=2))
    
    @classmethod
    def load_from_file(cls, path: Path) -> "PipelineConfig":
        """Load config from JSON file."""
        return cls.model_validate_json(path.read_text())


# Singleton instance
_config: Optional[PipelineConfig] = None


def get_config() -> PipelineConfig:
    """Get the global config instance."""
    global _config
    if _config is None:
        _config = PipelineConfig()
    return _config


def set_config(config: PipelineConfig):
    """Set the global config instance."""
    global _config
    _config = config


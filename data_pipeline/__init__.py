"""
LitSearch Data Pipeline

A modular pipeline for building citation graphs, computing layouts,
clustering, labeling with LLMs, and exporting to PostgreSQL.

Core Functions:
1. Collecting papers (nodes) from academic APIs
2. GPU physics processing for 2D layout
3. Clustering algorithms (Louvain)
4. Automated LLM labeling (clusters & sub-clusters)
5. PostgreSQL export
"""

__version__ = "2.0.0"
__author__ = "LitSearch Team"

from data_pipeline.workflow.orchestrator import PipelineOrchestrator
from data_pipeline.config.settings import PipelineConfig

__all__ = ["PipelineOrchestrator", "PipelineConfig"]


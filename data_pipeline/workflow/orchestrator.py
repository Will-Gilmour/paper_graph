"""
Main pipeline orchestrator coordinating all 5 core functions.

This is the heart of the refactored system.
"""

from pathlib import Path
from typing import List, Optional
import json

from data_pipeline.config.settings import PipelineConfig
from data_pipeline.api.crossref import CrossrefClient
from data_pipeline.api.openalex import OpenAlexClient
from data_pipeline.graph.crawler import CitationCrawler
from data_pipeline.graph.builder import GraphBuilder
from data_pipeline.layout.gpu_fa2 import GPUForceAtlas2
from data_pipeline.layout.cpu_fa2 import CPUForceAtlas2
from data_pipeline.clustering.louvain import LouvainClusterer
from data_pipeline.clustering.hierarchical import HierarchicalClusterer
from data_pipeline.embeddings.sapbert import SapBERTEncoder
from data_pipeline.embeddings.core_selection import CoreDocumentSelector
from data_pipeline.labeling.llm_client import LLMClient
from data_pipeline.labeling.cluster_labeler import ClusterLabeler
from data_pipeline.export.postgres_export import PostgreSQLExporter
from data_pipeline.export.pickle_export import PickleExporter
from data_pipeline.models.graph import PaperGraphData
from data_pipeline.utils.logging import setup_logging, get_logger
from data_pipeline.utils.errors import PipelineError

logger = get_logger("workflow.orchestrator")


class PipelineOrchestrator:
    """
    Orchestrates the complete data pipeline.
    
    Coordinates all 5 core functions:
    1. Paper collection (API crawling)
    2. GPU physics layout
    3. Clustering
    4. LLM labeling
    5. PostgreSQL export
    """
    
    def __init__(self, config: PipelineConfig, run_id: Optional[int] = None):
        """
        Initialize orchestrator.
        
        Args:
            config: Pipeline configuration
            run_id: Optional pipeline run ID for database partitioning
        """
        self.config = config
        self.run_id = run_id
        
        # Setup logging
        setup_logging(verbose=config.verbose)
        
        # Create output directory
        config.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components (lazy)
        self._graph_builder: Optional[GraphBuilder] = None
        self._layout_engine = None
        self._clusterer = None
        self._encoder = None
        self._labeler = None
        self._exporter = None
    
    def run_full_pipeline(self, seed_dois: List[str]) -> PaperGraphData:
        """
        Run complete pipeline from seeds to PostgreSQL.
        
        Args:
            seed_dois: List of seed DOIs
            
        Returns:
            PaperGraphData: The complete graph data with all computed properties
        """
        logger.info("=" * 80)
        logger.info("Starting full pipeline")
        logger.info("=" * 80)
        
        # 1. Build graph
        logger.info("\n[1/5] Building citation graph")
        graph_data = self.build_graph(seed_dois)
        
        # 2. Compute layout
        logger.info("\n[2/5] Computing 2D layout")
        self.compute_layout(graph_data)
        
        # 3. Cluster
        logger.info("\n[3/5] Clustering papers")
        self.compute_clusters(graph_data)
        
        # Debug: Show example node data
        logger.info("\n🔍 DEBUG: Sample node data")
        sample_dois = list(graph_data.graph.nodes())[:3]
        for doi in sample_dois:
            node_data = graph_data.graph.nodes[doi]
            logger.info(f"\nNode: {doi}")
            logger.info(f"  Title: {node_data.get('title', 'MISSING')}")
            
            # Handle None abstract gracefully
            abstract = node_data.get('abstract') or 'MISSING'
            if abstract != 'MISSING':
                abstract = abstract[:100] + "..."
            logger.info(f"  Abstract: {abstract}")
            
            logger.info(f"  Year: {node_data.get('year', 'MISSING')}")
            logger.info(f"  Authors: {node_data.get('authors', 'MISSING')}")
            logger.info(f"  Cluster: {graph_data.clusters.get(doi, 'MISSING')}")
            logger.info(f"  Sub-cluster: {graph_data.sub_clusters.get(doi, 'MISSING')}")
        
        # 4. Label clusters
        logger.info("\n[4/5] Generating cluster labels")
        self.label_clusters(graph_data)
        
        # 5. Export
        logger.info("\n[5/5] Exporting to PostgreSQL")
        self.export_to_postgres(graph_data)
        
        logger.info("=" * 80)
        logger.info("Pipeline complete!")
        logger.info(f"  Nodes: {graph_data.num_nodes()}")
        logger.info(f"  Edges: {graph_data.num_edges()}")
        logger.info(f"  Clusters: {graph_data.num_clusters()}")
        logger.info(f"  Sub-clusters: {graph_data.num_sub_clusters()}")
        logger.info("=" * 80)
        
        # Return graph data so worker can extract metadata
        return graph_data
    
    def build_graph(self, seed_dois: List[str]) -> PaperGraphData:
        """Core Function #1: Collect papers and build graph."""
        # Initialize API clients
        crossref = CrossrefClient(
            mailto=self.config.api.mailto,
            delay_between_requests=self.config.api.delay_between_requests,
            cache_dir=self.config.api.cache_dir,
        )
        
        openalex = OpenAlexClient(
            mailto=self.config.api.mailto,
            delay_between_requests=self.config.api.delay_between_requests,
            cache_dir=self.config.api.cache_dir,
        )
        
        # Initialize crawler
        crawler = CitationCrawler(
            crossref_client=crossref,
            openalex_client=openalex,
            max_workers=self.config.api.max_workers,
        )
        
        # Build graph
        self._graph_builder = GraphBuilder(crawler)
        self._graph_builder.add_papers_batch(seed_dois, max_depth=self.config.max_depth)
        
        # Save checkpoint
        checkpoint_path = self.config.output_dir / "graph.pkl.gz"
        self._graph_builder.save_to_pickle(checkpoint_path)
        
        return self._graph_builder.get_graph_data()
    
    def compute_layout(self, graph_data: PaperGraphData):
        """Core Function #2: GPU physics processing for 2D layout."""
        # Choose layout engine
        if self.config.layout.use_gpu:
            self._layout_engine = GPUForceAtlas2(
                max_iter=self.config.layout.fa2_iterations,
                barnes_hut_theta=self.config.layout.barnes_hut_theta,
                scaling_ratio=self.config.layout.scaling_ratio,
                gravity=self.config.layout.gravity,
            )
            
            if not self._layout_engine.is_available():
                logger.warning("GPU not available, falling back to CPU")
                self._layout_engine = CPUForceAtlas2(
                    iterations=self.config.layout.fa2_iterations,
                    barnes_hut_theta=self.config.layout.barnes_hut_theta,
                    scaling_ratio=self.config.layout.scaling_ratio,
                    gravity=self.config.layout.gravity,
                )
        else:
            self._layout_engine = CPUForceAtlas2(
                iterations=self.config.layout.fa2_iterations,
                barnes_hut_theta=self.config.layout.barnes_hut_theta,
                scaling_ratio=self.config.layout.scaling_ratio,
                gravity=self.config.layout.gravity,
            )
        
        # Compute layout
        positions = self._layout_engine.compute_layout(
            graph_data.graph,
            seed_positions=graph_data.positions or None,
        )
        
        graph_data.positions = positions
        
        # Debug: Check positions were computed
        logger.info(f"✓ Computed positions for {len(positions)} nodes")
        if positions:
            sample_doi = list(positions.keys())[0]
            sample_pos = positions[sample_doi]
            logger.info(f"  Sample: {sample_doi} → ({sample_pos[0]:.2f}, {sample_pos[1]:.2f})")
    
    def compute_clusters(self, graph_data: PaperGraphData):
        """Core Function #3: Clustering algorithms."""
        # Parent clustering
        clusterer = LouvainClusterer(resolution=self.config.clustering.louvain_resolution)
        clusters = clusterer.cluster(graph_data.graph)
        graph_data.clusters = clusters
        
        # Sub-clustering
        sub_clusterer = HierarchicalClusterer(resolution=self.config.clustering.sub_resolution)
        sub_clusters = sub_clusterer.compute_subclusters(graph_data.graph, clusters)
        graph_data.sub_clusters = sub_clusters
    
    def label_clusters(self, graph_data: PaperGraphData):
        """Core Function #4: Automated LLM labeling."""
        logger.info("=" * 80)
        logger.info("Starting cluster labeling process")
        logger.info("=" * 80)
        
        # Generate embeddings
        logger.info("\n[Step 1/4] Encoding papers with SapBERT")
        encoder = SapBERTEncoder(
            model_name=self.config.embedding.model_name,
            batch_size=self.config.embedding.batch_size,
        )
        
        doi_list = list(graph_data.graph.nodes())
        logger.info(f"Encoding {len(doi_list)} papers...")
        embeddings = encoder.encode_papers(graph_data.graph, doi_list)
        logger.info(f"✓ Generated {len(embeddings)} embeddings")
        
        # Select core documents
        logger.info("\n[Step 2/4] Selecting core documents")
        selector = CoreDocumentSelector(k_core=self.config.embedding.k_core)
        core_docs = selector.select_core_documents(
            embeddings,
            graph_data.clusters,
            graph_data.sub_clusters,
        )
        logger.info(f"✓ Selected core documents for {len(core_docs)} sub-clusters")
        
        # Initialize LLM
        logger.info("\n[Step 3/4] Labeling sub-clusters with LLM")
        llm = LLMClient(
            model_name=self.config.labeling.model_name,
            hf_token=self.config.labeling.hf_token,
            batch_size=self.config.labeling.batch_size,
            max_new_tokens=self.config.labeling.max_new_tokens,
            temperature=self.config.labeling.temperature,
            load_in_4bit=self.config.labeling.load_in_4bit,
            precision=getattr(self.config.labeling, 'precision', None),
        )
        
        # Label clusters
        labeler = ClusterLabeler(llm)
        
        # Sub-cluster labels
        sub_labels = labeler.label_sub_clusters(graph_data.graph, core_docs)
        graph_data.sub_cluster_labels = sub_labels
        logger.info(f"✓ Generated {len(sub_labels)} sub-cluster labels")
        
        # Parent cluster labels
        logger.info("\n[Step 4/4] Labeling parent clusters with LLM")
        parent_labels = labeler.label_parent_clusters(
            graph_data.clusters,
            graph_data.sub_clusters,
            sub_labels,
        )
        graph_data.cluster_labels = parent_labels
        logger.info(f"✓ Generated {len(parent_labels)} parent cluster labels")
        
        # Save labels to JSON
        labels_file = self.config.output_dir / "cluster_labels.json"
        logger.info(f"\nSaving labels to {labels_file}")
        with open(labels_file, "w") as f:
            json.dump({
                "parent": {str(k): v for k, v in parent_labels.items()},
                "sub": {f"{k[0]},{k[1]}": v for k, v in sub_labels.items()},
            }, f, indent=2)
        logger.info("✓ Labels saved")
        
        logger.info("=" * 80)
        logger.info("Cluster labeling complete!")
        logger.info("=" * 80)
    
    def export_to_postgres(self, graph_data: PaperGraphData):
        """Core Function #5: PostgreSQL export."""
        if self.run_id is None:
            raise PipelineError("run_id must be set for PostgreSQL export (required for graph partitioning)")
        
        exporter = PostgreSQLExporter(
            database_url=self.config.export.database_url,
            run_id=self.run_id,
            batch_size_papers=self.config.export.batch_size_papers,
            batch_size_edges=self.config.export.batch_size_edges,
        )
        
        exporter.export(graph_data)


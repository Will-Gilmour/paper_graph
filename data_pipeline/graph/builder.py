"""
Graph builder that coordinates crawling and graph construction.

Extracts high-level building logic from graph_builder6.py.
"""

from pathlib import Path
from typing import Optional, List
import pickle
import gzip

import networkx as nx

from data_pipeline.graph.crawler import CitationCrawler
from data_pipeline.models.graph import PaperGraphData
from data_pipeline.utils.logging import get_logger
from data_pipeline.utils.errors import PipelineError


logger = get_logger("graph.builder")


class GraphBuilder:
    """
    High-level graph builder.
    
    Coordinates citation crawling to build a directed graph of papers.
    """
    
    def __init__(self, crawler: CitationCrawler):
        """
        Initialize builder.
        
        Args:
            crawler: Citation crawler instance
        """
        self.crawler = crawler
        self.graph_data = PaperGraphData()
    
    def add_paper(
        self,
        citation: str,
        max_depth: int = 1,
        year_from: Optional[int] = None,
    ):
        """
        Add a paper and its citation network to the graph.
        
        Args:
            citation: DOI or bibliographic citation
            max_depth: Crawl depth
            year_from: Only include papers from this year onwards
        """
        logger.info(f"Adding paper: {citation[:80]}...")
        
        # Crawl from this seed
        sub_graph = self.crawler.crawl(citation, max_depth, year_from)
        
        # Merge into main graph
        before_nodes = self.graph_data.graph.number_of_nodes()
        self.graph_data.graph = nx.compose(self.graph_data.graph, sub_graph)
        after_nodes = self.graph_data.graph.number_of_nodes()
        
        added = after_nodes - before_nodes
        logger.info(f"Added {added} new nodes (total: {after_nodes})")
        
        # Update citation counts
        self._update_citation_counts()
    
    def add_papers_batch(
        self,
        citations: List[str],
        max_depth: int = 1,
        year_from: Optional[int] = None,
    ):
        """
        Add multiple papers at once.
        
        Args:
            citations: List of DOIs or bibliographic citations
            max_depth: Crawl depth
            year_from: Year filter
        """
        for citation in citations:
            self.add_paper(citation, max_depth, year_from)
    
    def _update_citation_counts(self):
        """Update cited_count and references_count for all nodes."""
        for node in self.graph_data.graph.nodes():
            attrs = self.graph_data.graph.nodes[node]
            attrs["cited_count"] = self.graph_data.graph.in_degree(node)
            attrs["references_count"] = self.graph_data.graph.out_degree(node)
    
    def get_graph_data(self) -> PaperGraphData:
        """Get the current graph data."""
        return self.graph_data
    
    def save_to_pickle(self, path: Path):
        """
        Save graph to gzipped pickle file.
        
        Args:
            path: Output path (.pkl.gz)
        """
        logger.info(f"Saving graph to {path}")
        
        # Prepare data for pickling
        data = {
            "graph": self.graph_data.graph,
            "pos": self.graph_data.positions,
        }
        
        # Save with gzip
        with gzip.open(path, "wb") as f:
            pickle.dump(data, f)
        
        logger.info(f"Saved {self.graph_data.num_nodes()} nodes, {self.graph_data.num_edges()} edges")
    
    @classmethod
    def load_from_pickle(cls, path: Path, crawler: CitationCrawler) -> "GraphBuilder":
        """
        Load graph from pickle file.
        
        Args:
            path: Input path (.pkl.gz)
            crawler: Crawler instance (for potential future additions)
        
        Returns:
            Loaded GraphBuilder
        """
        logger.info(f"Loading graph from {path}")
        
        with gzip.open(path, "rb") as f:
            data = pickle.load(f)
        
        # Create builder
        builder = cls(crawler)
        builder.graph_data.graph = data["graph"]
        builder.graph_data.positions = data.get("pos", {})
        
        # Update citation counts
        builder._update_citation_counts()
        
        logger.info(f"Loaded {builder.graph_data.num_nodes()} nodes, {builder.graph_data.num_edges()} edges")
        return builder
    
    def validate(self) -> bool:
        """
        Validate the graph structure.
        
        Returns:
            True if valid
        
        Raises:
            PipelineError: If validation fails
        """
        if self.graph_data.num_nodes() == 0:
            raise PipelineError("Graph is empty")
        
        # Check for graphs with no edges (isolated nodes only)
        if self.graph_data.num_edges() == 0:
            logger.error(
                f"🛑 Graph has {self.graph_data.num_nodes()} node(s) but NO EDGES!\n"
                f"   This means ALL seed papers failed to produce connections.\n"
                f"   Common causes:\n"
                f"   - Old papers (pre-2000) missing reference metadata\n"
                f"   - API failures (403, rate limits)\n"
                f"   - Invalid DOIs\n"
                f"   → The graph will use a simple circular layout.\n"
                f"   → Consider using newer papers (post-2010) as seeds."
            )
        
        # Check for isolated components
        if not nx.is_weakly_connected(self.graph_data.graph):
            num_components = nx.number_weakly_connected_components(self.graph_data.graph)
            logger.warning(f"Graph has {num_components} weakly connected components")
            
            # Count isolated nodes (0-degree nodes)
            isolated_count = sum(1 for n in self.graph_data.graph.nodes() if self.graph_data.graph.degree(n) == 0)
            if isolated_count > 0:
                logger.warning(
                    f"Graph has {isolated_count} isolated node(s) with no connections. "
                    f"These are papers that failed during crawling (API errors or missing metadata). "
                    f"This is normal and doesn't affect the main graph structure."
                )
        
        # Check for self-loops
        num_self_loops = nx.number_of_selfloops(self.graph_data.graph)
        if num_self_loops > 0:
            logger.warning(f"Graph has {num_self_loops} self-loops")
        
        return True


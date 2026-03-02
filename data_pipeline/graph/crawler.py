"""
Citation network crawler using BFS.

Extracts the BFS crawling logic from graph_builder6.py.
"""

from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Set, Dict, Any, Optional

import networkx as nx

from data_pipeline.api.crossref import CrossrefClient
from data_pipeline.api.openalex import OpenAlexClient
from data_pipeline.models.paper import Paper
from data_pipeline.utils.logging import get_logger
from data_pipeline.utils.errors import APIError


logger = get_logger("graph.crawler")


class CitationCrawler:
    """
    Crawls citation network using breadth-first search.
    
    Supports bidirectional crawling:
    - Forward: Papers this paper cites (references)
    - Backward: Papers that cite this paper (citers)
    """
    
    def __init__(
        self,
        crossref_client: CrossrefClient,
        openalex_client: Optional[OpenAlexClient] = None,
        max_workers: int = 8,
        include_citers: bool = True,
        max_citers: int = 50,
    ):
        """
        Initialize crawler.
        
        Args:
            crossref_client: Crossref API client
            openalex_client: OpenAlex API client (for citers)
            max_workers: Max concurrent API requests
            include_citers: Whether to fetch citing papers
            max_citers: Max citers per paper
        """
        self.crossref = crossref_client
        self.openalex = openalex_client
        self.max_workers = max_workers
        self.include_citers = include_citers
        self.max_citers = max_citers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    def crawl(
        self,
        seed_doi: str,
        max_depth: int = 1,
        year_from: Optional[int] = None,
    ) -> nx.DiGraph:
        """
        Crawl citation network starting from seed DOI.
        
        Args:
            seed_doi: Starting DOI
            max_depth: Maximum depth to crawl
            year_from: Only include papers from this year onwards
        
        Returns:
            Directed graph with papers as nodes and citations as edges
        """
        logger.info(f"Starting crawl from {seed_doi} (depth={max_depth})")
        
        # Resolve seed DOI
        if seed_doi.startswith("10."):
            doi_key = seed_doi.lower()
            root_work = self.crossref.fetch_work(doi_key)
        else:
            # Treat as bibliographic query
            results = self.crossref.search(seed_doi, rows=1)
            if not results or not results[0].get("DOI"):
                raise APIError(f"Could not resolve citation to DOI: {seed_doi}")
            root_work = results[0]
            doi_key = root_work["DOI"].lower()
        
        # Build graph via BFS
        graph = nx.DiGraph()
        self._bfs(graph, doi_key, root_work, max_depth, year_from)
        
        logger.info(f"Crawl complete: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
        return graph
    
    def _bfs(
        self,
        graph: nx.DiGraph,
        root_doi: str,
        root_work: Dict[str, Any],
        max_depth: int,
        year_from: Optional[int],
    ):
        """
        Breadth-first search through citation network.
        
        Args:
            graph: Graph to build (modified in place)
            root_doi: Starting DOI
            root_work: Crossref metadata for root
            max_depth: Max depth
            year_from: Year filter
        """
        # Queue: (doi, work, depth)
        queue: deque = deque([(root_doi, root_work, 0)])
        seen: Set[str] = {root_doi}
        
        while queue:
            doi, work, depth = queue.popleft()
            
            # Add node to graph
            self._add_node(graph, doi, work)
            
            if depth >= max_depth:
                continue
            
            # Get references (papers this paper cites)
            out_refs = [
                ref["DOI"].lower()
                for ref in work.get("reference", [])
                if ref.get("DOI")
            ]
            
            # Handle missing references
            if not out_refs:
                if depth == 0:
                    # Seed paper with no references is concerning
                    logger.warning(
                        f"⚠️  SEED paper {doi} has no references in Crossref metadata. "
                        f"Will try to fetch citers to build connections."
                    )
                else:
                    # Non-seed paper with no references is less critical
                    logger.debug(f"Paper {doi} (depth={depth}) has no references, will try citers")
            
            # Get citers (papers that cite this paper)
            in_refs = []
            if self.include_citers and self.openalex:
                try:
                    in_refs = self.openalex.fetch_citers(
                        doi,
                        max_results=self.max_citers,
                        year_from=year_from
                    )
                except APIError as e:
                    if depth == 0:
                        # Seed paper citer fetch failed
                        logger.warning(f"⚠️  Failed to fetch citers for SEED paper {doi}: {e}")
                        if not out_refs:
                            # CRITICAL: Seed paper has no references AND citers failed
                            logger.error(
                                f"🛑 CRITICAL: Seed paper {doi} has ZERO connections:\n"
                                f"   - No references in Crossref metadata\n"
                                f"   - Citers fetch failed: {e}\n"
                                f"   This will result in an isolated node.\n"
                                f"   → Please use a different seed paper (preferably post-2010)"
                            )
                    else:
                        # Non-seed paper failure is fine, just skip it
                        logger.debug(f"Failed to fetch citers for {doi} (depth={depth}): {e}")
            
            # Combine with direction tags
            targets = [(d, "out") for d in out_refs] + [(d, "in") for d in in_refs]
            
            # Separate: papers we need to FETCH vs papers we need to QUEUE
            # - Fetch: Any paper NOT in graph (need metadata)
            # - Queue: Only papers NOT in seen (to avoid infinite loops)
            to_fetch = [(d, dirn) for d, dirn in targets if d not in graph]
            to_queue_later = [(d, dirn) for d, dirn in targets if d not in seen]
            seen.update(d for d, _ in to_queue_later)
            
            # Fetch metadata in parallel (only for papers not in graph)
            futures = {
                self.executor.submit(self.crossref.fetch_work, d): (d, dirn)
                for d, dirn in to_fetch
            }
            
            # For papers already in graph, just add edges (no fetch needed)
            for target_doi, direction in targets:
                if target_doi in graph:
                    # Paper already has metadata, just add the edge
                    if direction == "out":
                        graph.add_edge(doi, target_doi)
                    else:
                        graph.add_edge(target_doi, doi)
                    logger.debug(f"Added edge to existing node {target_doi}")
            
            # Process fetched papers (these are NEW to the graph)
            for future in as_completed(futures):
                target_doi, direction = futures[future]
                try:
                    target_work = future.result()
                    
                    # Add node with metadata (it's new to graph)
                    self._add_node(graph, target_doi, target_work)
                    
                    # Add the edge
                    if direction == "out":
                        graph.add_edge(doi, target_doi)
                    else:
                        graph.add_edge(target_doi, doi)
                    
                    # Queue for further crawling if we haven't seen it yet
                    # (to_queue_later was filtered by 'seen' to prevent infinite loops)
                    if (target_doi, direction) in to_queue_later:
                        queue.append((target_doi, target_work, depth + 1))
                    
                except Exception as e:
                    logger.debug(f"Failed to fetch {target_doi}: {e}")
    
    def _add_node(self, graph: nx.DiGraph, doi: str, work: Dict[str, Any]):
        """
        Add node to graph with paper metadata.
        
        Args:
            graph: Graph to add to
            doi: Paper DOI
            work: Crossref metadata
        """
        if doi in graph:
            # Already exists, don't overwrite (preserves metadata from first encounter)
            logger.debug(f"Node {doi} already in graph, skipping")
            return
        
        # Create Paper object
        paper = Paper.from_crossref_work(work)
        
        # Add to graph with attributes
        graph.add_node(
            doi,
            title=paper.title,
            authors=paper.authors,
            year=paper.year,
            container_title=paper.container_title,
            publisher=paper.publisher,
            abstract=paper.abstract,
        )
    
    def shutdown(self):
        """Shutdown the thread pool."""
        self.executor.shutdown(wait=True)


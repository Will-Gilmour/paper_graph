"""Abstract base class for layout engines."""

from abc import ABC, abstractmethod
from typing import Dict, Tuple
import networkx as nx


class LayoutEngine(ABC):
    """
    Abstract base class for graph layout algorithms.
    
    Layout engines compute 2D positions for nodes in a graph.
    """
    
    @abstractmethod
    def compute_layout(
        self,
        graph: nx.DiGraph,
        seed_positions: Dict[str, Tuple[float, float]] = None,
    ) -> Dict[str, Tuple[float, float]]:
        """
        Compute 2D layout positions for graph nodes.
        
        Args:
            graph: Directed graph
            seed_positions: Optional seed positions for incremental layout
        
        Returns:
            Dictionary mapping node IDs to (x, y) positions
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this layout engine is available (e.g., GPU available)."""
        pass


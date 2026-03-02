"""Pickle export for graph data."""

import gzip
import pickle
from pathlib import Path

from data_pipeline.models.graph import PaperGraphData
from data_pipeline.utils.logging import get_logger

logger = get_logger("export.pickle")


class PickleExporter:
    """Exports graph data to gzipped pickle format."""
    
    @staticmethod
    def export(graph_data: PaperGraphData, output_path: Path):
        """
        Export to pickle.
        
        Args:
            graph_data: Graph data
            output_path: Output file path (.pkl.gz)
        """
        logger.info(f"Exporting to pickle: {output_path}")
        
        data = {
            "graph": graph_data.graph,
            "pos": graph_data.positions,
        }
        
        with gzip.open(output_path, "wb") as f:
            pickle.dump(data, f)
        
        logger.info(f"Exported {graph_data.num_nodes()} nodes, {graph_data.num_edges()} edges")
    
    @staticmethod
    def load(input_path: Path) -> PaperGraphData:
        """
        Load from pickle.
        
        Args:
            input_path: Input file path (.pkl.gz)
        
        Returns:
            Loaded graph data
        """
        logger.info(f"Loading from pickle: {input_path}")
        
        with gzip.open(input_path, "rb") as f:
            data = pickle.load(f)
        
        graph_data = PaperGraphData()
        graph_data.graph = data["graph"]
        graph_data.positions = data.get("pos", {})
        
        logger.info(f"Loaded {graph_data.num_nodes()} nodes, {graph_data.num_edges()} edges")
        return graph_data


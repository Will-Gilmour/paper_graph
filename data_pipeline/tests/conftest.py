"""Pytest configuration and shared fixtures."""

import pytest
import networkx as nx
from pathlib import Path


@pytest.fixture
def sample_crossref_work():
    """Sample Crossref API response."""
    return {
        "DOI": "10.1001/jama.2020.12345",
        "title": ["Sample Medical Research Paper"],
        "author": [
            {"given": "John", "family": "Doe"},
            {"given": "Jane", "family": "Smith"}
        ],
        "issued": {"date-parts": [[2020, 5, 15]]},
        "container-title": ["JAMA"],
        "publisher": "American Medical Association",
        "abstract": "This is a sample abstract.",
        "reference": [
            {"DOI": "10.1001/ref1"},
            {"DOI": "10.1001/ref2"},
        ]
    }


@pytest.fixture
def sample_graph():
    """Create a small test graph."""
    G = nx.DiGraph()
    
    # Add nodes with attributes
    nodes = [
        ("10.1001/paper1", {"title": "Paper 1", "year": 2020, "authors": ["A", "B"]}),
        ("10.1001/paper2", {"title": "Paper 2", "year": 2021, "authors": ["C", "D"]}),
        ("10.1001/paper3", {"title": "Paper 3", "year": 2019, "authors": ["E", "F"]}),
        ("10.1001/paper4", {"title": "Paper 4", "year": 2022, "authors": ["G", "H"]}),
        ("10.1001/paper5", {"title": "Paper 5", "year": 2020, "authors": ["I", "J"]}),
    ]
    
    for node, attrs in nodes:
        G.add_node(node, **attrs)
    
    # Add edges (citations)
    edges = [
        ("10.1001/paper1", "10.1001/paper3"),
        ("10.1001/paper2", "10.1001/paper1"),
        ("10.1001/paper2", "10.1001/paper3"),
        ("10.1001/paper4", "10.1001/paper1"),
        ("10.1001/paper5", "10.1001/paper3"),
    ]
    
    G.add_edges_from(edges)
    
    return G


@pytest.fixture
def sample_positions():
    """Sample layout positions."""
    return {
        "10.1001/paper1": (0.0, 0.0),
        "10.1001/paper2": (1.0, 1.0),
        "10.1001/paper3": (2.0, 0.0),
        "10.1001/paper4": (0.0, 2.0),
        "10.1001/paper5": (1.5, 1.5),
    }


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary output directory."""
    output = tmp_path / "output"
    output.mkdir()
    return output


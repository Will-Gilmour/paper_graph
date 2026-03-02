"""Cluster data models."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Cluster:
    """Represents a parent cluster."""
    
    id: int
    label: str
    size: int
    x: float
    y: float
    
    # Optional metadata
    representative_papers: list[str] = None  # DOIs
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "label": self.label,
            "size": self.size,
            "x": self.x,
            "y": self.y,
        }


@dataclass
class SubCluster:
    """Represents a sub-cluster within a parent cluster."""
    
    parent_id: int
    sub_id: int
    label: str
    size: int
    x: float
    y: float
    
    # Optional metadata
    representative_papers: list[str] = None  # DOIs
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "parent_id": self.parent_id,
            "sub_id": self.sub_id,
            "label": self.label,
            "size": self.size,
            "x": self.x,
            "y": self.y,
        }
    
    @property
    def full_id(self) -> tuple[int, int]:
        """Get (parent_id, sub_id) tuple."""
        return (self.parent_id, self.sub_id)


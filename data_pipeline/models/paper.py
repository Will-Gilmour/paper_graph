"""Paper data model."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Paper:
    """Represents a single paper in the citation graph."""
    
    doi: str
    title: str
    authors: list[str] = field(default_factory=list)
    year: Optional[int] = None
    
    # Citation metrics
    cited_count: int = 0
    references_count: int = 0
    fncr: Optional[float] = None  # Field-Normalized Citation Ratio
    
    # Clustering
    cluster: Optional[int] = None
    sub_cluster: Optional[int] = None
    
    # Layout position
    x: Optional[float] = None
    y: Optional[float] = None
    
    # Metadata
    container_title: Optional[str] = None
    publisher: Optional[str] = None
    abstract: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "doi": self.doi,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "cited_count": self.cited_count,
            "references_count": self.references_count,
            "fncr": self.fncr,
            "cluster": self.cluster,
            "sub_cluster": self.sub_cluster,
            "x": self.x,
            "y": self.y,
            "container_title": self.container_title,
            "publisher": self.publisher,
            "abstract": self.abstract,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Paper":
        """Create from dictionary."""
        return cls(**data)
    
    @classmethod
    def from_crossref_work(cls, work: dict) -> "Paper":
        """Create from Crossref API response."""
        # Extract DOI
        doi = work.get("DOI", "").lower()
        
        # Extract title
        titles = work.get("title", [])
        title = titles[0] if titles else ""
        
        # Extract authors
        authors = []
        for author in work.get("author", []):
            given = author.get("given", "").strip()
            family = author.get("family", "").strip()
            full_name = " ".join(p for p in (given, family) if p)
            if full_name:
                authors.append(full_name)
        
        # Extract year
        date_parts = work.get("issued", {}).get("date-parts", [[None]])
        year = date_parts[0][0] if date_parts and date_parts[0] else None
        
        # Extract metadata
        container_titles = work.get("container-title", [])
        container_title = container_titles[0] if container_titles else None
        publisher = work.get("publisher")
        abstract = work.get("abstract")
        
        # References count
        references_count = len(work.get("reference", []))
        
        return cls(
            doi=doi,
            title=title,
            authors=authors,
            year=year,
            references_count=references_count,
            container_title=container_title,
            publisher=publisher,
            abstract=abstract,
        )


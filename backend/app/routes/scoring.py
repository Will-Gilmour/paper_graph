"""
Scoring-related API routes.

Endpoints for computing and testing paper importance scores.
"""
from fastapi import APIRouter, Query as ApiQuery
from typing import Dict, Optional

from backend.app.services.scoring_service import scoring_service

router = APIRouter(prefix="/scoring", tags=["scoring"])


@router.get("/test", summary="Test scoring function with parameters")
def test_scoring(
    citations: int = ApiQuery(..., ge=0, description="Number of citations"),
    year: int = ApiQuery(..., ge=1900, le=2100, description="Publication year"),
    decay_factor: float = ApiQuery(1.0, ge=0.1, le=5.0, description="Time decay factor"),
    current_year: Optional[int] = ApiQuery(None, ge=1900, le=2100, description="Current year (defaults to now)")
) -> Dict:
    """
    Test the time-decayed citation scoring function.
    
    Useful for experimenting with different decay factors before applying to the full dataset.
    
    Args:
        citations: Number of citations
        year: Publication year
        decay_factor: How quickly old papers lose relevance (0.1-5.0)
        current_year: Current year for age calculation (optional)
        
    Returns:
        Dictionary with various scores and metrics
    """
    time_decayed = scoring_service.time_decayed_citations(
        citations, year, current_year, decay_factor
    )
    
    velocity = scoring_service.citation_velocity(
        citations, year, current_year
    )
    
    hybrid = scoring_service.hybrid_score(
        citations, year, current_year, decay_factor
    )
    
    return {
        "input": {
            "citations": citations,
            "year": year,
            "decay_factor": decay_factor,
            "current_year": current_year
        },
        "scores": {
            "time_decayed": round(time_decayed, 2),
            "citation_velocity": round(velocity, 2),
            "hybrid": round(hybrid, 2)
        },
        "metrics": {
            "age": (current_year or 2025) - year,
            "citations_per_year": round(velocity, 2)
        }
    }


@router.get("/compare", summary="Compare multiple papers' scores")
def compare_papers(
    papers: str = ApiQuery(..., description="Comma-separated 'year:citations' pairs (e.g., '2024:100,2010:100,2020:500')"),
    decay_factor: float = ApiQuery(1.0, ge=0.1, le=5.0, description="Time decay factor")
) -> Dict:
    """
    Compare scores for multiple papers.
    
    Useful for understanding how the scoring behaves across different scenarios.
    
    Args:
        papers: Comma-separated "year:citations" pairs
        decay_factor: Time decay factor to use
        
    Returns:
        List of papers with their computed scores
        
    Example:
        /scoring/compare?papers=2024:100,2010:100,2020:500&decay_factor=1.0
    """
    results = []
    
    for paper_str in papers.split(','):
        try:
            year_str, cit_str = paper_str.split(':')
            year = int(year_str)
            citations = int(cit_str)
            
            score = scoring_service.time_decayed_citations(
                citations, year, None, decay_factor
            )
            
            velocity = scoring_service.citation_velocity(citations, year)
            
            results.append({
                "year": year,
                "citations": citations,
                "score": round(score, 2),
                "velocity": round(velocity, 2)
            })
        except (ValueError, IndexError):
            continue
    
    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    
    return {
        "decay_factor": decay_factor,
        "papers": results
    }


"""
Scoring service - Paper importance scoring algorithms

Provides various scoring methods to rank papers by importance/relevance.
"""
import math
from datetime import datetime
from typing import Optional


class ScoringService:
    """Service for computing paper importance scores."""
    
    @staticmethod
    def time_decayed_citations(
        citations: int,
        year: int,
        current_year: Optional[int] = None,
        decay_factor: float = 1.0
    ) -> float:
        """
        Compute time-decayed citation score.
        
        Recent highly-cited papers get highest scores.
        Old papers with few citations become less relevant.
        
        Formula: citations / (1 + age)^decay_factor
        
        Args:
            citations: Number of citations the paper has
            year: Publication year
            current_year: Current year (defaults to now)
            decay_factor: How quickly old papers lose relevance (0.5-2.0)
                         Higher = more aggressive decay
                         1.0 = balanced (recommended default)
                         0.5 = gentle decay (still values old influential papers)
                         2.0 = aggressive decay (strongly favors recent papers)
        
        Returns:
            Float score (higher is more important)
            
        Examples:
            - Paper from 2024 with 100 citations, decay=1.0:
              100 / (1 + 1)^1.0 = 50.0
            
            - Paper from 2010 with 100 citations, decay=1.0:
              100 / (1 + 15)^1.0 = 6.25
            
            - Paper from 2010 with 1000 citations, decay=1.0:
              1000 / (1 + 15)^1.0 = 62.5
        """
        if current_year is None:
            current_year = datetime.now().year
        
        # Calculate age (handle future dates gracefully)
        age = max(0, current_year - year)
        
        # Apply time decay
        denominator = math.pow(1 + age, decay_factor)
        score = citations / denominator
        
        return score
    
    @staticmethod
    def citation_velocity(
        citations: int,
        year: int,
        current_year: Optional[int] = None
    ) -> float:
        """
        Compute citations per year (velocity).
        
        Simple metric: how many citations per year on average.
        
        Args:
            citations: Number of citations
            year: Publication year
            current_year: Current year (defaults to now)
            
        Returns:
            Citations per year
        """
        if current_year is None:
            current_year = datetime.now().year
        
        age = max(1, current_year - year + 1)  # At least 1 year
        return citations / age
    
    @staticmethod
    def hybrid_score(
        citations: int,
        year: int,
        current_year: Optional[int] = None,
        decay_factor: float = 1.0,
        log_boost: bool = True
    ) -> float:
        """
        Hybrid score combining decay with logarithmic boost for total impact.
        
        Balances recency with overall influence.
        
        Formula: (citations / (1 + age)^decay) * (1 + log10(citations + 1))
        
        Args:
            citations: Number of citations
            year: Publication year
            current_year: Current year
            decay_factor: Time decay factor
            log_boost: Whether to apply logarithmic boost for high citations
            
        Returns:
            Hybrid score
        """
        base_score = ScoringService.time_decayed_citations(
            citations, year, current_year, decay_factor
        )
        
        if log_boost:
            # Logarithmic boost: prevents very high citation papers from dominating
            # but still rewards them
            boost = 1 + math.log10(citations + 1)
            return base_score * boost
        
        return base_score
    
    @staticmethod
    def percentile_score(
        citations: int,
        year: int,
        year_percentiles: dict,
        decay_factor: float = 0.5
    ) -> float:
        """
        Score based on percentile within publication year cohort.
        
        More sophisticated: compares papers to their peers.
        
        Args:
            citations: Number of citations
            year: Publication year
            year_percentiles: Dict mapping year -> citation percentiles
            decay_factor: Time decay to apply
            
        Returns:
            Percentile-based score with time decay
        """
        # This would require precomputed percentiles per year
        # Placeholder for future implementation
        return ScoringService.time_decayed_citations(
            citations, year, None, decay_factor
        )
    
    @staticmethod
    def normalize_score(score: float, min_val: float = 0.0, max_val: float = 100.0) -> float:
        """
        Normalize score to a given range for display.
        
        Args:
            score: Raw score
            min_val: Minimum value in dataset
            max_val: Maximum value in dataset
            
        Returns:
            Normalized score (0-100 scale recommended for UI)
        """
        if max_val == min_val:
            return 50.0  # Neutral value if no variance
        
        return ((score - min_val) / (max_val - min_val)) * 100.0


# Global service instance
scoring_service = ScoringService()


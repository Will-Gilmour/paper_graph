"""
Reading list service - Business logic for generating personalized reading lists.

Combines spatial proximity and citation-based filtering.
"""
import math
from typing import List, Dict, Optional, Tuple
import numpy as np

from backend.app.config.settings import logger
from backend.app.database.connection import get_db_connection


class ReadingListService:
    """Service for generating reading lists."""
    
    def generate_reading_list(
        self,
        center_dois: List[str],
        k_region: int = 1000,
        depth_refs: int = 1,
        year_from: Optional[int] = None,
        min_cites: int = 4,
        weight_distance: float = 0.5,
        top_n: int = 100
    ) -> Dict:
        """
        Generate a reading list based on seed papers.
        
        Strategy:
        1. Find spatial neighbors of seed papers
        2. Optionally expand with citation network (1-hop)
        3. Filter by year and citation count
        4. Score by weighted combination of distance and citations
        5. Return top N results
        
        Args:
            center_dois: List of seed DOIs to build reading list from
            k_region: Number of spatial neighbors per seed
            depth_refs: Citation network depth (0 or 1)
            year_from: Minimum publication year (optional)
            min_cites: Minimum citation count
            weight_distance: Weight for distance vs citations (0-1)
            top_n: Number of papers to return
            
        Returns:
            Dictionary with "reading_list" of papers
            
        Raises:
            ValueError: If center DOIs are invalid or not found
        """
        center_lc = [d.lower() for d in center_dois]
        
        if not center_lc:
            raise ValueError("Parameter `center` must contain ≥1 DOI")
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Step 1: Fetch seed coordinates and validate
                cur.execute(
                    """
                    SELECT doi, x, y
                    FROM papers
                    WHERE lower(doi) = ANY(%s)
                """,
                    (center_lc,),
                )
                seeds_xyz = {d: (float(x), float(y)) for d, x, y in cur.fetchall()}
                
                missing = [d for d in center_lc if d not in seeds_xyz]
                if missing:
                    raise ValueError(f"Seed DOI(s) not in graph: {', '.join(missing)}")
                
                # Calculate centroid of seed positions
                pts = np.array(list(seeds_xyz.values()), dtype=np.float64)
                centroid = pts.mean(axis=0)
                cx, cy = float(centroid[0]), float(centroid[1])
                
                # Step 2: Gather spatial neighbors for each seed
                pool: set[str] = set()
                for doi, (sx, sy) in seeds_xyz.items():
                    cur.execute(
                        """
                        SELECT doi
                        FROM papers
                        WHERE doi <> %s
                        ORDER BY ( (x-%s)^2 + (y-%s)^2 )
                        LIMIT %s
                    """,
                        (doi, sx, sy, k_region),
                    )
                    pool.update(r[0] for r in cur.fetchall())
                
                # Step 3: Optionally expand with citation network
                if depth_refs > 0:
                    cur.execute(
                        """
                        SELECT dst FROM edges WHERE src = ANY(%s)
                        UNION
                        SELECT src FROM edges WHERE dst = ANY(%s)
                    """,
                        (center_lc, center_lc),
                    )
                    pool.update(r[0] for r in cur.fetchall())
                
                # Step 4: Remove seed papers from pool
                pool.difference_update(center_lc)
                
                if not pool:
                    return {"reading_list": []}
                
                # Step 5: Fetch candidate metadata with filters
                if year_from is not None:
                    cur.execute(
                        """
                        SELECT doi, title, year, cited_count, cluster, x, y, fncr
                        FROM papers
                        WHERE doi = ANY(%s)
                          AND cited_count >= %s
                          AND year >= %s
                    """,
                        (list(pool), min_cites, year_from),
                    )
                else:
                    cur.execute(
                        """
                        SELECT doi, title, year, cited_count, cluster, x, y, fncr
                        FROM papers
                        WHERE doi = ANY(%s)
                          AND cited_count >= %s
                    """,
                        (list(pool), min_cites),
                    )
                
                cand_rows = cur.fetchall()
        
        # Step 6: Score candidates
        results = []
        for doi, title, yr, cites, cl, x, y, fncr in cand_rows:
            # Skip if no layout coordinates
            if x is None or y is None:
                continue
            
            # Calculate distance from centroid
            dist = math.hypot(float(x) - cx, float(y) - cy)
            
            # Combined score: weighted distance + log citations
            # Lower score is better (closer + more cited)
            score = (
                weight_distance * dist
                - (1.0 - weight_distance) * math.log1p(int(cites))
            )
            
            results.append({
                "doi": doi,
                "title": title or doi,
                "year": yr,
                "citations": cites,
                "cluster": cl,
                "distance": dist,
                "score": score,
                "fncr": fncr,
            })
        
        # Step 7: Sort by score and return top N
        results.sort(key=lambda r: r["score"])
        
        return {"reading_list": results[:top_n]}


# Global service instance
reading_list_service = ReadingListService()


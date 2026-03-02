"""Recommendations service for Papers of Interest."""

import math
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict

from backend.app.database import queries
from backend.app.config.settings import logger


class RecommendationsService:
    """Service for generating paper recommendations based on user collections."""
    
    def get_spatial_recommendations(
        self,
        dois: List[str],
        top_n: int = 20,
        min_distance: float = 0.0,
        max_distance: Optional[float] = None,
        min_citations: int = 5,
        exclude_collection: bool = True,
    ) -> Dict:
        """
        Find papers near the spatial centroid of a collection.
        
        Strategy:
        1. Fetch positions of all papers in collection
        2. Compute centroid (average x, y)
        3. Query nearby papers by Euclidean distance
        4. Filter by citation count and distance constraints
        5. Score by: importance * (1 / (1 + distance))
        """
        if not dois:
            return {
                "centroid": None,
                "recommendations": [],
                "collection_size": 0,
                "error": "Empty collection"
            }
        
        # Get positions of collection papers (filters out papers not in current graph)
        collection_positions = queries.fetch_paper_positions(dois)
        
        if not collection_positions:
            logger.warning(f"Spatial recommendations: {len(dois)} papers requested but none found in current graph")
            return {
                "centroid": None,
                "recommendations": [],
                "collection_size": len(dois),
                "papers_in_graph": 0,
                "error": "None of the selected papers are in the current graph. Switch graphs or clear your collection."
            }
        
        # Compute centroid
        centroid_x = sum(pos['x'] for pos in collection_positions) / len(collection_positions)
        centroid_y = sum(pos['y'] for pos in collection_positions) / len(collection_positions)
        
        logger.info(f"Spatial recommendations: centroid=({centroid_x:.1f}, {centroid_y:.1f}), collection_size={len(collection_positions)}")
        
        # Compute bounding box for search (expand based on collection spread)
        xs = [pos['x'] for pos in collection_positions]
        ys = [pos['y'] for pos in collection_positions]
        spread_x = max(xs) - min(xs) if len(xs) > 1 else 50000
        spread_y = max(ys) - min(ys) if len(ys) > 1 else 50000
        # Use larger search radius: 3x spread or minimum 100k units for small collections
        search_radius = max(spread_x, spread_y, 100000) * 3
        
        logger.info(f"Spatial search: spread=({spread_x:.0f}, {spread_y:.0f}), radius={search_radius:.0f}")
        
        # Fetch candidate papers in bounding box
        candidates = queries.fetch_papers_in_radius(
            center_x=centroid_x,
            center_y=centroid_y,
            radius=search_radius,
            min_citations=min_citations,
            limit=1000
        )
        
        logger.info(f"Spatial search: found {len(candidates)} candidates in radius")
        
        # Compute distances and scores
        recommendations = []
        collection_set = set(dois) if exclude_collection else set()
        
        for paper in candidates:
            if exclude_collection and paper['doi'] in collection_set:
                continue
            
            # Euclidean distance to centroid
            dx = paper['x'] - centroid_x
            dy = paper['y'] - centroid_y
            distance = math.sqrt(dx * dx + dy * dy)
            
            # Apply distance filters
            if distance < min_distance:
                continue
            if max_distance and distance > max_distance:
                continue
            
            # Compute recommendation score: importance / (1 + distance)
            # Importance = citations + year recency bonus
            year = paper.get('year') or 2000  # Handle null years
            year_bonus = max(0, (year - 2000) * 0.5)
            importance = paper.get('cited_count', 0) + year_bonus
            score = importance / (1 + distance)
            
            recommendations.append({
                "doi": paper['doi'],
                "title": paper.get('title', 'Untitled'),
                "distance": round(distance, 2),
                "score": round(score, 4),
                "cited_count": paper.get('cited_count', 0),
                "year": year,
                "cluster": paper.get('cluster'),
                "x": paper['x'],
                "y": paper['y'],
            })
        
        # Sort by score (highest first) and take top N
        recommendations.sort(key=lambda p: p['score'], reverse=True)
        recommendations = recommendations[:top_n]
        
        logger.info(f"Spatial recommendations: returning {len(recommendations)} papers")
        
        return {
            "centroid": {"x": round(centroid_x, 2), "y": round(centroid_y, 2)},
            "collection_size": len(dois),
            "papers_in_graph": len(collection_positions),
            "search_radius": round(search_radius, 2),
            "recommendations": recommendations,
        }
    
    def get_bridge_recommendations(
        self,
        dois: List[str],
        top_n: int = 20,
        min_connections: int = 1,
        max_hops: int = 2,
    ) -> Dict:
        """
        Find papers that act as bridges connecting papers in the collection.
        
        Strategy:
        1. For each paper in collection, get its citations and references
        2. Find papers that cite/are cited by multiple collection papers
        3. Score by: (# of connections)^2 * importance
        """
        if not dois:
            logger.warning(f"Bridge recommendations: empty collection")
            return {
                "recommendations": [],
                "collection_size": 0,
                "error": "Empty collection"
            }
        
        collection_set = set(dois)
        
        logger.info(f"Bridge recommendations: analyzing {len(dois)} papers")
        
        # Get citation network for collection
        citation_map = defaultdict(set)  # paper -> papers in collection it connects to
        
        # Fetch all edges involving collection papers (one end must be in collection)
        edges = queries.fetch_edges_involving_dois(dois)
        logger.info(f"Bridge search: found {len(edges)} edges involving collection")
        
        for source, target in edges:
            # If source is in collection and target is not, target is a potential bridge
            if source in collection_set and target not in collection_set:
                citation_map[target].add(source)
            # If target is in collection and source is not, source is a potential bridge
            if target in collection_set and source not in collection_set:
                citation_map[source].add(target)
        
        # Filter bridges that connect at least min_connections papers
        bridge_candidates = {
            doi: connected_papers 
            for doi, connected_papers in citation_map.items() 
            if len(connected_papers) >= min_connections
        }
        
        logger.info(f"Bridge search: found {len(bridge_candidates)} candidate bridges")
        
        if not bridge_candidates:
            logger.warning(f"Bridge recommendations: no bridges found for {min_connections}+ connections")
            return {
                "recommendations": [],
                "collection_size": len(dois),
                "error": f"No bridge papers found connecting {min_connections}+ collection papers"
            }
        
        # Fetch metadata for bridge candidates
        bridge_dois = list(bridge_candidates.keys())
        papers_metadata = queries.fetch_papers_by_dois(bridge_dois)
        
        # Score and format recommendations
        recommendations = []
        for paper in papers_metadata:
            doi = paper['doi']
            connections = bridge_candidates[doi]
            connection_count = len(connections)
            
            # Score: connections^2 * importance (where importance = citations + year recency)
            citations = paper.get('cited_count', 0)
            year = paper.get('year') or 2000  # Handle null years
            year_bonus = max(0, (year - 2000) * 0.5)  # Recent papers get bonus
            importance = citations + year_bonus
            
            # Emphasize highly connected bridges with exponential connection weight
            score = (connection_count ** 2) * (1 + importance)
            
            recommendations.append({
                "doi": doi,
                "title": paper.get('title', 'Untitled'),
                "connection_count": connection_count,
                "connected_papers": list(connections),
                "score": round(score, 2),
                "cited_count": citations,
                "importance": round(importance, 2),
                "year": year,
                "cluster": paper.get('cluster'),
            })
        
        # Sort by score and take top N
        recommendations.sort(key=lambda p: p['score'], reverse=True)
        recommendations = recommendations[:top_n]
        
        logger.info(f"Bridge recommendations: returning {len(recommendations)} papers")
        
        return {
            "collection_size": len(dois),
            "total_bridges_found": len(bridge_candidates),
            "recommendations": recommendations,
        }


# Global service instance
recommendations_service = RecommendationsService()


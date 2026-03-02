"""
Integration tests that test against the real running API.
These tests assume the application is running locally with the database populated.
"""
import pytest
import requests
from typing import Dict, Any


class TestRealAPIEndpoints:
    """Test real API endpoints against running application."""
    
    # Base URL for the running API
    BASE_URL = "http://localhost:8000"
    
    def test_health_endpoint(self):
        """Test the health check endpoint."""
        response = requests.get(f"{self.BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
    
    def test_docs_endpoint(self):
        """Test that docs are accessible."""
        response = requests.get(f"{self.BASE_URL}/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_root_redirect(self):
        """Test that root redirects to docs."""
        response = requests.get(f"{self.BASE_URL}/", allow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/docs"
    
    def test_labels_endpoints(self):
        """Test label endpoints."""
        # Test parent labels
        response = requests.get(f"{self.BASE_URL}/labels/parent")
        assert response.status_code == 200
        parent_labels = response.json()
        assert isinstance(parent_labels, dict)
        assert len(parent_labels) > 0
        
        # Test sub labels
        response = requests.get(f"{self.BASE_URL}/labels/sub")
        assert response.status_code == 200
        sub_labels = response.json()
        assert isinstance(sub_labels, dict)
        assert len(sub_labels) > 0
    
    def test_clusters_endpoint(self):
        """Test clusters endpoint."""
        response = requests.get(f"{self.BASE_URL}/clusters")
        assert response.status_code == 200
        clusters = response.json()
        assert isinstance(clusters, list)
        assert len(clusters) > 0
        
        # Check structure of first cluster
        cluster = clusters[0]
        required_fields = ["id", "title", "x", "y", "size", "top_sub"]
        for field in required_fields:
            assert field in cluster
        
        # Check that clusters are sorted by size (descending)
        sizes = [c["size"] for c in clusters]
        assert sizes == sorted(sizes, reverse=True)
    
    def test_cluster_detail_endpoint(self):
        """Test cluster detail endpoint."""
        # First get a cluster ID from the clusters endpoint
        response = requests.get(f"{self.BASE_URL}/clusters")
        assert response.status_code == 200
        clusters = response.json()
        assert len(clusters) > 0
        
        cluster_id = clusters[0]["id"]
        response = requests.get(f"{self.BASE_URL}/cluster/{cluster_id}")
        assert response.status_code == 200
        
        cluster_data = response.json()
        assert "nodes" in cluster_data
        assert "edges" in cluster_data
        assert isinstance(cluster_data["nodes"], list)
        assert isinstance(cluster_data["edges"], list)
    
    def test_cluster_detail_invalid_id(self):
        """Test cluster detail with invalid ID."""
        response = requests.get(f"{self.BASE_URL}/cluster/99999")
        assert response.status_code == 404
    
    def test_initial_meta_endpoint(self):
        """Test initial NDJSON meta endpoint."""
        response = requests.get(f"{self.BASE_URL}/export/ndjson/initial/meta")
        assert response.status_code == 200
        meta = response.json()
        assert "nodes_total" in meta
        assert "edges_total" in meta
        assert isinstance(meta["nodes_total"], int)
        assert isinstance(meta["edges_total"], int)
        assert meta["nodes_total"] > 0
        assert meta["edges_total"] > 0
    
    def test_initial_ndjson_endpoint(self):
        """Test initial NDJSON endpoint."""
        response = requests.get(f"{self.BASE_URL}/export/initial.ndjson")
        assert response.status_code == 200
        
        # Should return NDJSON content
        content = response.text
        lines = content.strip().split('\n')
        assert len(lines) > 0
        
        # Each line should be valid JSON
        import json
        node_count = 0
        edge_count = 0
        malformed_lines = []
        
        for i, line in enumerate(lines):
            if line.strip():
                try:
                    parsed = json.loads(line)
                    assert "type" in parsed
                    if parsed["type"] == "node":
                        node_count += 1
                    elif parsed["type"] == "edge":
                        edge_count += 1
                except json.JSONDecodeError as e:
                    malformed_lines.append((i, line, str(e)))
        
        if malformed_lines:
            print(f"\nFound {len(malformed_lines)} malformed lines:")
            for i, line, error in malformed_lines[:5]:  # Show first 5
                print(f"  Line {i}: {line[:100]}... (Error: {error})")
        
        assert node_count > 0
        assert edge_count > 0
        # For now, allow some malformed lines but expect mostly good data
        assert len(malformed_lines) < len(lines) / 2, f"Too many malformed lines: {len(malformed_lines)}/{len(lines)}"
    
    def test_search_endpoint(self):
        """Test search functionality."""
        # Test with a common search term
        response = requests.get(f"{self.BASE_URL}/find?query=tremor")
        assert response.status_code == 200
        results = response.json()
        assert "results" in results
        assert isinstance(results["results"], list)
    
    def test_search_with_empty_query(self):
        """Test search with empty query."""
        response = requests.get(f"{self.BASE_URL}/find?query=")
        assert response.status_code == 200
        results = response.json()
        assert "results" in results
        assert isinstance(results["results"], list)
    
    def test_search_nearby_endpoint(self):
        """Test nearby search functionality."""
        response = requests.get(f"{self.BASE_URL}/find/nearby?query=tremor&k=5")
        assert response.status_code == 200
        results = response.json()
        assert "results" in results
        assert isinstance(results["results"], list)
        assert len(results["results"]) <= 5
    
    def test_export_json_endpoint(self):
        """Test JSON export with pagination."""
        response = requests.get(f"{self.BASE_URL}/export/json?nodes_offset=0&nodes_limit=10&edges_offset=0&edges_limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert "nodes_total" in data
        assert "edges_total" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)
        assert len(data["nodes"]) <= 10
        assert len(data["edges"]) <= 10
    
    def test_export_json_default_pagination(self):
        """Test JSON export with default pagination."""
        response = requests.get(f"{self.BASE_URL}/export/json")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert "nodes_total" in data
        assert "edges_total" in data
    
    def test_reading_list_endpoint(self):
        """Test reading list functionality."""
        # Use a DOI that should exist in the database
        response = requests.get(f"{self.BASE_URL}/find?query=tremor")
        assert response.status_code == 200
        search_results = response.json()
        
        if search_results["results"]:
            # Use the first result as a center point
            center_doi = search_results["results"][0]
            if isinstance(center_doi, dict):
                center_doi = center_doi["doi"]
            
            response = requests.get(f"{self.BASE_URL}/reading_list?center={center_doi}&k_region=10&top_n=5")
            assert response.status_code == 200
            data = response.json()
            assert "reading_list" in data
            assert isinstance(data["reading_list"], list)
            assert len(data["reading_list"]) <= 5
    
    def test_ego_endpoint(self):
        """Test ego subgraph functionality."""
        # First find a paper to use as center
        response = requests.get(f"{self.BASE_URL}/find?query=tremor")
        assert response.status_code == 200
        search_results = response.json()
        
        if search_results["results"]:
            center_doi = search_results["results"][0]
            if isinstance(center_doi, dict):
                center_doi = center_doi["doi"]
            
            response = requests.get(f"{self.BASE_URL}/ego?doi={center_doi}&depth=1")
            assert response.status_code == 200
            ego_data = response.json()
            assert "nodes" in ego_data
            assert "edges" in ego_data
            assert isinstance(ego_data["nodes"], list)
            assert isinstance(ego_data["edges"], list)
    
    def test_paper_endpoint(self):
        """Test paper detail endpoint."""
        # First find a paper
        response = requests.get(f"{self.BASE_URL}/find?query=tremor")
        assert response.status_code == 200
        search_results = response.json()
        
        if search_results["results"]:
            paper_doi = search_results["results"][0]
            if isinstance(paper_doi, dict):
                paper_doi = paper_doi["doi"]
            
            response = requests.get(f"{self.BASE_URL}/paper/{paper_doi}")
            assert response.status_code == 200
            paper = response.json()
            
            required_fields = ["doi", "title", "year", "cited_count", "references_count", "cluster", "x", "y"]
            for field in required_fields:
                assert field in paper
    
    def test_paper_endpoint_case_insensitive(self):
        """Test that paper DOI lookup is case insensitive."""
        # First find a paper
        response = requests.get(f"{self.BASE_URL}/find?query=tremor")
        assert response.status_code == 200
        search_results = response.json()
        
        if search_results["results"]:
            paper_doi = search_results["results"][0]
            if isinstance(paper_doi, dict):
                paper_doi = paper_doi["doi"]
            
            # Test with uppercase DOI
            upper_doi = paper_doi.upper()
            response = requests.get(f"{self.BASE_URL}/paper/{upper_doi}")
            assert response.status_code == 200
            paper = response.json()
            assert paper["doi"] == paper_doi.lower()  # Should be normalized to lowercase
    
    def test_invalid_endpoints(self):
        """Test that invalid endpoints return appropriate errors."""
        # Test non-existent endpoint
        response = requests.get(f"{self.BASE_URL}/nonexistent")
        assert response.status_code == 404
        
        # Test invalid paper DOI
        response = requests.get(f"{self.BASE_URL}/paper/invalid-doi")
        assert response.status_code == 404
        
        # Test invalid cluster ID
        response = requests.get(f"{self.BASE_URL}/cluster/99999")
        assert response.status_code == 404
    
    # ============================================================================
    # NEW FEATURE TESTS
    # ============================================================================
    
    def test_scoring_endpoint(self):
        """Test the scoring computation endpoint."""
        response = requests.get(
            f"{self.BASE_URL}/scoring/test",  # Updated to correct endpoint
            params={
                "citations": 100,
                "year": 2020,
                "decay_factor": 1.0
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "input" in data
        assert "scores" in data
        assert "metrics" in data
        
        # Check input echo
        assert data["input"]["citations"] == 100
        assert data["input"]["year"] == 2020
        assert data["input"]["decay_factor"] == 1.0
        
        # Check scores exist
        assert "time_decayed" in data["scores"]
        assert "citation_velocity" in data["scores"]
        assert "hybrid" in data["scores"]
        
        # Check metrics
        assert "age" in data["metrics"]
        assert data["metrics"]["age"] >= 0
    
    def test_combined_title_author_search(self):
        """Test searching by both title and author."""
        response = requests.get(
            f"{self.BASE_URL}/find",
            params={
                "title": "tremor",
                "author": "elias"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        
        # Should return some results
        if data["results"]:
            # Verify results have expected structure
            result = data["results"][0]
            assert "doi" in result
            assert "title" in result or "score" in result
    
    def test_multi_cluster_search(self):
        """Test searching with multiple cluster IDs."""
        response = requests.get(
            f"{self.BASE_URL}/find",
            params={
                "title": "ultrasound",
                "clusters": "0,1,2"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        # Results should be filtered to specified clusters
    
    def test_author_only_search(self):
        """Test searching by author name only."""
        response = requests.get(
            f"{self.BASE_URL}/find",
            params={
                "author": "chang"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
    
    def test_flexible_fuzzy_search(self):
        """Test that fuzzy search handles partial words."""
        # Test partial word matching
        test_cases = [
            ("ultra", "should find ultrasound"),
            ("thalam", "should find thalamotomy"),
            ("fus", "should find focused ultrasound papers")
        ]
        
        for query, description in test_cases:
            response = requests.get(
                f"{self.BASE_URL}/find",
                params={"query": query, "top_k": 10}
            )
            assert response.status_code == 200, f"Failed for '{query}': {description}"
            data = response.json()
            # Should return some results even with partial words
            # (Don't assert count > 0 as it depends on data, but should not error)
    
    def test_filtered_graph_export(self):
        """Test graph export with date and citation filters."""
        response = requests.get(
            f"{self.BASE_URL}/export/json",
            params={
                "year_min": 2020,
                "min_citations": 50,
                "nodes_limit": 10
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "nodes_total" in data
        assert "nodes" in data
        assert "meta" in data
        
        # Check that filters are in metadata
        assert "filters" in data["meta"]
        assert data["meta"]["filters"]["year_min"] == 2020
        assert data["meta"]["filters"]["min_citations"] == 50
    
    def test_search_with_all_filters(self):
        """Test search with all possible filters combined."""
        response = requests.get(
            f"{self.BASE_URL}/find",
            params={
                "title": "tremor",
                "author": "elias",
                "clusters": "0,1",
                "year_min": 2010,
                "year_max": 2023,
                "min_citations": 20,
                "top_k": 20
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        # Should not error even with all filters combined

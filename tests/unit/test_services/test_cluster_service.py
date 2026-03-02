"""
Unit tests for cluster service
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open
import json

from backend.app.services.cluster_service import ClusterService


class TestClusterService:
    """Test cluster service functionality"""
    
    @patch('backend.app.database.connection.get_db_connection')
    @patch('backend.app.services.cluster_service.queries')
    def test_init_loads_labels(self, mock_queries, mock_db):
        """Test that service loads labels from database on initialization"""
        # Mock get_active_run_id
        mock_queries.get_active_run_id.return_value = 1
        
        # Mock database connection and queries
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        
        # Mock parent clusters query
        mock_cursor.fetchall.side_effect = [
            [(0, "Test Cluster")],  # Parent clusters
            [(0, 1, "Test Sub")]     # Sub-clusters
        ]
        
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = False
        mock_db.return_value.__enter__.return_value = mock_conn
        mock_db.return_value.__exit__.return_value = False
        
        service = ClusterService()
        
        assert service.parent_labels == {"0": "Test Cluster"}
        assert service.sub_labels == {"0:1": "Test Sub"}
    
    def test_get_parent_labels(self):
        """Test getting parent labels"""
        service = ClusterService()
        service.parent_labels = {"0": "Test", "1": "Another"}
        
        labels = service.get_parent_labels()
        
        assert labels == {"0": "Test", "1": "Another"}
    
    def test_get_sub_labels(self):
        """Test getting sub labels"""
        service = ClusterService()
        service.sub_labels = {"0:1": "Sub1", "0:2": "Sub2"}
        
        labels = service.get_sub_labels()
        
        assert labels == {"0:1": "Sub1", "0:2": "Sub2"}
    
    @patch('backend.app.database.connection.get_db_connection')
    @patch('backend.app.services.cluster_service.queries')
    def test_get_all_clusters(self, mock_queries, mock_db):
        """Test getting all clusters"""
        # Mock database response for clusters (with NO VALID TITLE to trigger label usage)
        mock_queries.fetch_all_clusters.return_value = {
            0: {
                "id": 0,
                "title": "NO VALID TITLE",  # This triggers label replacement
                "x": 100.0,
                "y": 200.0,
                "size": 500,
                "_subs": [(1, 50), (2, 30)]
            }
        }
        mock_queries.get_active_run_id.return_value = 1
        
        # Mock label loading from DB
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.side_effect = [
            [(0, "Label Title")],  # Parent clusters
            [(0, 1, "Sub 1"), (0, 2, "Sub 2")]  # Sub-clusters
        ]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = False
        mock_db.return_value.__enter__.return_value = mock_conn
        mock_db.return_value.__exit__.return_value = False
        
        service = ClusterService()
        
        clusters = service.get_all_clusters()
        
        assert len(clusters) == 1
        assert clusters[0]["id"] == 0
        assert clusters[0]["title"] == "Label Title"  # Should use label, not DB title
        assert clusters[0]["size"] == 500
        assert len(clusters[0]["top_sub"]) == 2
        assert clusters[0]["top_sub"][0]["label"] == "Sub 1"
    
    @patch('backend.app.services.cluster_service.queries')
    def test_get_all_clusters_empty(self, mock_queries):
        """Test getting clusters when database is empty"""
        mock_queries.fetch_all_clusters.return_value = {}
        
        service = ClusterService()
        
        with pytest.raises(ValueError, match="No clusters in database"):
            service.get_all_clusters()
    
    @patch('backend.app.services.cluster_service.queries')
    def test_get_cluster_detail_found(self, mock_queries):
        """Test getting cluster detail when cluster exists"""
        mock_queries.fetch_cluster_nodes.return_value = [
            {"doi": "10.1234/test", "title": "Test Paper", "x": 1.0, "y": 2.0, "fncr": 0.5}
        ]
        mock_queries.fetch_cluster_edges.return_value = [
            {"source": "10.1234/a", "target": "10.1234/b"}
        ]
        
        service = ClusterService()
        service.parent_labels = {"5": "Test Cluster"}
        
        result = service.get_cluster_detail(5)
        
        assert result is not None
        assert result["id"] == 5
        assert result["label"] == "Test Cluster"
        assert len(result["nodes"]) == 1
        assert len(result["edges"]) == 1
    
    @patch('backend.app.services.cluster_service.queries')
    def test_get_cluster_detail_not_found(self, mock_queries):
        """Test getting cluster detail when cluster doesn't exist"""
        mock_queries.fetch_cluster_nodes.return_value = []
        
        service = ClusterService()
        
        result = service.get_cluster_detail(999)
        
        assert result is None


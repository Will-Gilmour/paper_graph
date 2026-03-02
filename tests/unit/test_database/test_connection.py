"""
Unit tests for database connection module
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import os

from backend.app.database import connection


class TestDatabaseConnection:
    """Test database connection management"""
    
    def setup_method(self):
        """Reset the connection pool before each test"""
        connection.db_pool._pool = None
    
    @patch('backend.app.database.connection.psycopg2.pool.SimpleConnectionPool')
    @patch('backend.app.database.connection.settings')
    def test_initialize_pool(self, mock_settings, mock_pool_class):
        """Test database pool initialization"""
        mock_settings.database_url = "postgresql://test"
        mock_pool = Mock()
        mock_pool_class.return_value = mock_pool
        
        connection.db_pool.initialize()
        
        mock_pool_class.assert_called_once_with(minconn=1, maxconn=8, dsn="postgresql://test")
        assert connection.db_pool._pool == mock_pool
    
    @patch('backend.app.database.connection.psycopg2.pool.SimpleConnectionPool')
    def test_initialize_pool_only_once(self, mock_pool_class):
        """Test that pool is only initialized once"""
        mock_pool = Mock()
        mock_pool_class.return_value = mock_pool
        
        connection.db_pool._pool = None
        connection.db_pool.initialize()
        connection.db_pool.initialize()  # Second call
        
        # Should only be called once (pool already exists)
        assert mock_pool_class.call_count == 1
    
    @patch.object(connection.db_pool, 'initialize')
    def test_get_conn_initializes_if_needed(self, mock_init):
        """Test that get_conn initializes pool if not exists"""
        connection.db_pool._pool = None
        mock_pool = Mock()
        mock_pool.getconn.return_value = Mock()
        
        def set_pool():
            connection.db_pool._pool = mock_pool
        
        mock_init.side_effect = set_pool
        
        conn = connection.get_conn()
        
        mock_init.assert_called_once()
        assert conn is not None
    
    def test_get_conn_returns_connection(self):
        """Test getting a connection from the pool"""
        mock_pool = Mock()
        mock_conn = Mock()
        mock_pool.getconn.return_value = mock_conn
        connection.db_pool._pool = mock_pool
        
        conn = connection.get_conn()
        
        assert conn == mock_conn
        mock_pool.getconn.assert_called_once()
    
    def test_put_conn_returns_connection(self):
        """Test returning a connection to the pool"""
        mock_pool = Mock()
        mock_conn = Mock()
        connection.db_pool._pool = mock_pool
        
        connection.put_conn(mock_conn)
        
        mock_pool.putconn.assert_called_once_with(mock_conn)
    
    def test_close_pool(self):
        """Test closing the database pool"""
        mock_pool = Mock()
        connection.db_pool._pool = mock_pool
        
        connection.db_pool.close_all()
        
        mock_pool.closeall.assert_called_once()
        assert connection.db_pool._pool is None
    
    def test_close_pool_when_none(self):
        """Test closing pool when it doesn't exist"""
        connection.db_pool._pool = None
        
        # Should not raise an error
        connection.db_pool.close_all()
        
        assert connection.db_pool._pool is None


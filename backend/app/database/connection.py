"""
Database connection management.

Provides connection pooling and context management for PostgreSQL connections.
"""
import psycopg2
import psycopg2.pool
from typing import Optional

from backend.app.config.settings import settings, logger


class DatabaseConnectionPool:
    """Manages PostgreSQL connection pool."""
    
    def __init__(self):
        """Initialize the connection pool."""
        self._pool: Optional[psycopg2.pool.SimpleConnectionPool] = None
    
    def initialize(self):
        """Initialize the connection pool."""
        if self._pool is None:
            logger.info(f"Initializing database connection pool to {settings.database_url}")
            self._pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=8,
                dsn=settings.database_url
            )
            logger.info("Database connection pool initialized")
    
    def get_connection(self):
        """
        Get a connection from the pool.
        
        Returns:
            psycopg2 connection object
            
        Raises:
            RuntimeError: If pool is not initialized
        """
        if self._pool is None:
            self.initialize()
        return self._pool.getconn()
    
    def return_connection(self, conn):
        """
        Return a connection to the pool.
        
        Args:
            conn: psycopg2 connection object to return
        """
        if self._pool is not None:
            self._pool.putconn(conn)
    
    def close_all(self):
        """Close all connections in the pool."""
        if self._pool is not None:
            self._pool.closeall()
            self._pool = None
            logger.info("Database connection pool closed")


# Global connection pool instance
db_pool = DatabaseConnectionPool()


def get_conn():
    """
    Get a database connection from the pool.
    
    Returns:
        psycopg2 connection object
        
    Example:
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM papers LIMIT 1")
                result = cur.fetchone()
        finally:
            put_conn(conn)
    """
    return db_pool.get_connection()


def put_conn(conn):
    """
    Return a database connection to the pool.
    
    Args:
        conn: psycopg2 connection object to return
        
    Example:
        conn = get_conn()
        try:
            # use connection
            pass
        finally:
            put_conn(conn)
    """
    db_pool.return_connection(conn)


class DatabaseConnection:
    """Context manager for database connections."""
    
    def __enter__(self):
        """Get a connection from the pool."""
        self.conn = get_conn()
        return self.conn
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Return connection to pool."""
        put_conn(self.conn)
        return False


def get_db_connection():
    """
    Get a database connection context manager.
    
    Returns:
        DatabaseConnection context manager
        
    Example:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM papers LIMIT 1")
                result = cur.fetchone()
    """
    return DatabaseConnection()


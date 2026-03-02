"""Base API client with caching and rate limiting."""

import time
import json
import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any

import requests
from requests.adapters import HTTPAdapter, Retry

from data_pipeline.utils.logging import get_logger
from data_pipeline.utils.errors import APIError


logger = get_logger("api.base")


class BaseAPIClient(ABC):
    """
    Abstract base class for API clients.
    
    Provides:
    - SQLite caching
    - Rate limiting
    - Retry logic
    - Error handling
    """
    
    def __init__(
        self,
        mailto: str,
        delay_between_requests: float = 0.0,
        cache_dir: Optional[Path] = None,
        max_retries: int = 3,
    ):
        """
        Initialize API client.
        
        Args:
            mailto: Email address for polite API usage
            delay_between_requests: Delay between requests (seconds)
            cache_dir: Directory for SQLite cache
            max_retries: Max retries for failed requests
        """
        self.mailto = mailto
        self.delay = delay_between_requests
        self.max_retries = max_retries
        
        # Set up session with retries
        self.session = self._create_session()
        
        # Set up cache
        self.cache_path: Optional[Path] = None
        if cache_dir:
            cache_dir = Path(cache_dir)
            cache_dir.mkdir(parents=True, exist_ok=True)
            self.cache_path = cache_dir / f"{self.__class__.__name__.lower()}.sqlite3"
            self._ensure_cache_db()
    
    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic."""
        session = requests.Session()
        session.headers.update({"User-Agent": self._get_user_agent()})
        
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=False,
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        return session
    
    @abstractmethod
    def _get_user_agent(self) -> str:
        """Get user agent string for this API."""
        pass
    
    def _ensure_cache_db(self):
        """Create cache database if it doesn't exist."""
        if not self.cache_path:
            return
        
        with sqlite3.connect(self.cache_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    timestamp REAL NOT NULL
                )
            """)
            conn.commit()
    
    def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Get value from cache."""
        if not self.cache_path:
            return None
        
        try:
            with sqlite3.connect(self.cache_path) as conn:
                cur = conn.execute("SELECT value FROM cache WHERE key=?", (key,))
                row = cur.fetchone()
                return json.loads(row[0]) if row else None
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
            return None
    
    def _put_in_cache(self, key: str, value: Dict[str, Any]):
        """Put value in cache."""
        if not self.cache_path:
            return
        
        try:
            with sqlite3.connect(self.cache_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO cache (key, value, timestamp) VALUES (?, ?, ?)",
                    (key, json.dumps(value), time.time())
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"Cache write error: {e}")
    
    def _rate_limit(self):
        """Apply rate limiting delay."""
        if self.delay > 0:
            time.sleep(self.delay)


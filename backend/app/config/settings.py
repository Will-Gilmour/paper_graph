"""
Application configuration settings.

Centralizes all environment variables and application settings.
"""
import os
import logging
from pathlib import Path
from typing import Optional


class Settings:
    """Application settings loaded from environment variables."""
    
    def __init__(self):
        """Initialize settings from environment variables."""
        # Database configuration
        self.database_url: str = os.getenv(
            "DATABASE_URL",
            os.getenv(
                "PG_URI", 
                "postgresql://pg:secret@postgres:5432/litsearch"
            )
        )
        
        # Label files configuration
        self.label_base: str = os.getenv("LABEL_BASE", "mrgfus_papers4.pkl.gz")
        
        # Cache directory configuration
        # In Docker, we're at /app, so .cache should be at /app/.cache
        # In development, we're at backend/app/config, so go up to project root
        if Path("/app").exists():  # Docker environment
            self.cache_dir = Path("/app/.cache")
        else:  # Development
            self.cache_dir = Path(__file__).parent.parent.parent.parent / ".cache"
        self.cache_dir.mkdir(exist_ok=True)
        
        # NDJSON file path
        self.initial_ndjson_path: Path = self.cache_dir / "initial.ndjson"
        
        # Crossref API configuration
        self.crossref_api_url: str = "https://api.crossref.org/works"
        self.works_cache_path: Path = self.cache_dir / "works.sqlite3"
        
        # Logging configuration
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        
        # CORS configuration
        self.cors_origins: list[str] = self._parse_cors_origins()
        
    def _parse_cors_origins(self) -> list[str]:
        """Parse CORS origins from environment variable."""
        origins_str = os.getenv("CORS_ORIGINS", "*")
        if origins_str == "*":
            return ["*"]
        return [origin.strip() for origin in origins_str.split(",")]
    
    def get_parent_labels_path(self) -> Path:
        """Get path to parent labels JSON file."""
        # Look in working directory (Docker: /app, Dev: project root)
        base_path = Path.cwd() / self.label_base
        return Path(f"{base_path}.parentlabels.json")
    
    def get_sub_labels_path(self) -> Path:
        """Get path to sub labels JSON file."""
        # Look in working directory (Docker: /app, Dev: project root)
        base_path = Path.cwd() / self.label_base
        return Path(f"{base_path}.sublabels.json")


# Global settings instance
settings = Settings()


# Configure logging
def setup_logging():
    """Configure application logging."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


# Logger for this module
logger = logging.getLogger("api_postgres")


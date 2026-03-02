"""
Pytest configuration for integration tests.
"""
import pytest
import os


def pytest_configure(config):
    """Configure pytest with custom markers and test environment."""
    # Set DATABASE_URL to localhost for local testing (Docker postgres is on localhost:5432)
    if "DATABASE_URL" not in os.environ:
        os.environ["DATABASE_URL"] = "postgresql://pg:secret@localhost:5432/litsearch"
    
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )

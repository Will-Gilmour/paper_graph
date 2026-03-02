#!/usr/bin/env python3
"""
Integration test runner for real API endpoints.
This script tests against the actual running application.
"""
import requests
import subprocess
import sys
import time
from pathlib import Path


def check_api_health(base_url: str = "http://localhost:8000") -> bool:
    """Check if the API is running and healthy."""
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def wait_for_api(base_url: str = "http://localhost:8000", max_wait: int = 30) -> bool:
    """Wait for the API to become available."""
    print(f"Checking if API is running at {base_url}...")
    
    for i in range(max_wait):
        if check_api_health(base_url):
            print("API is running and healthy!")
            return True
        
        if i == 0:
            print("API not ready, waiting...")
        elif i % 5 == 0:
            print(f"Still waiting... ({i}s)")
        
        time.sleep(1)
    
    print(f"API not available after {max_wait} seconds")
    return False


def run_integration_tests():
    """Run integration tests against the real API."""
    print("Running Integration Tests Against Real API")
    print("=" * 50)
    
    # Check if API is running
    if not wait_for_api():
        print("\nTo start the API, run:")
        print("   docker-compose -f docker-compose.unified.yml up -d backend postgres")
        print("\n   Then wait for the backend to fully start up.")
        return False
    
    # Run the integration tests
    print("\nRunning integration tests...")
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        "tests/integration/test_api/test_real_endpoints.py",
        "-v",
        "--tb=short"
    ])
    
    if result.returncode == 0:
        print("\nAll integration tests passed!")
        print("\nYour API is working correctly.")
    else:
        print("\nSome integration tests failed!")
        print("This indicates issues with the current API that should be fixed before refactoring.")
    
    return result.returncode == 0


def main():
    """Main entry point."""
    # Check if we're in the right directory
    if not Path("docker-compose.unified.yml").exists():
        print("Error: Please run this script from the project root directory")
        sys.exit(1)
    
    success = run_integration_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

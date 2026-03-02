#!/usr/bin/env python3
"""
Test runner script for the paper_graph application.
"""
import subprocess
import sys
import os


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n🧪 {description}")
    print(f"Running: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Success!")
        if result.stdout:
            print(result.stdout)
    else:
        print("❌ Failed!")
        if result.stderr:
            print(result.stderr)
        if result.stdout:
            print(result.stdout)
        return False
    
    return True


def main():
    """Main test runner."""
    print("🚀 Running paper_graph Tests")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists("docker-compose.unified.yml"):
        print("❌ Error: Please run this script from the project root directory")
        sys.exit(1)
    
    # Install test dependencies
    if not run_command(
        [sys.executable, "-m", "pip", "install", "-r", "requirements-test.txt"],
        "Installing test dependencies"
    ):
        print("❌ Failed to install test dependencies")
        sys.exit(1)
    
    # Run tests
    test_commands = [
        (
            [sys.executable, "tests/run_integration_tests.py"],
            "Running integration tests"
        ),
    ]
    
    failed_tests = []
    
    for cmd, description in test_commands:
        if not run_command(cmd, description):
            failed_tests.append(description)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    
    if failed_tests:
        print(f"❌ {len(failed_tests)} test suites failed:")
        for test in failed_tests:
            print(f"   - {test}")
        sys.exit(1)
    else:
        print("✅ All test suites passed!")
        print("\n🎉 Ready for refactoring with confidence!")


if __name__ == "__main__":
    main()

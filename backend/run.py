"""
Entry point for running the refactored LitSearch API.

This script starts the Uvicorn server with the new modular application.
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload for development
        log_level="info",
        access_log=False,  # Disable verbose access logs
    )


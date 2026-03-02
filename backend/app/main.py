"""
Main FastAPI application.

This is the entry point for the refactored LitSearch API.
It uses the new modular structure with proper separation of concerns.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import RedirectResponse

from backend.app.config.settings import settings, setup_logging
from backend.app.database.connection import db_pool

# Set up logging
setup_logging()

# Initialize FastAPI app
app = FastAPI(
    title="LitSearch API",
    description="Literature search and visualization API with PostgreSQL backend",
    version="2.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add GZip middleware for compression
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup."""
    # Initialize database connection pool
    db_pool.initialize()


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    # Close database connection pool
    db_pool.close_all()


@app.get("/", include_in_schema=False)
def root():
    """Redirect root to API documentation."""
    return RedirectResponse(url="/docs")


@app.get("/health", summary="Health check endpoint")
def health_check():
    """Simple health check endpoint for monitoring."""
    return {"status": "healthy", "database": "connected"}


# Import and include routers
from backend.app.routes import clusters, papers, search, export, graph, scoring, pipeline, lod, recommendations

app.include_router(clusters.router)
app.include_router(papers.router)
app.include_router(search.router)
app.include_router(export.router)
app.include_router(graph.router)
app.include_router(scoring.router)
app.include_router(pipeline.router)
app.include_router(lod.router)
app.include_router(recommendations.router)


# paper_graph Backend API

Modern, modular FastAPI backend for the paper_graph literature search application.

## 🏗️ Architecture

The backend follows a clean, layered architecture:

```
backend/
├── app/
│   ├── config/         # Configuration management
│   ├── database/       # Database layer
│   ├── services/       # Business logic
│   ├── routes/         # API endpoints
│   ├── exceptions/     # Custom exceptions
│   └── main.py         # Application entry point
└── run.py              # Development server
```

## 📦 Modules

### Configuration (`app/config/`)
- **settings.py** - Centralized configuration using Pydantic Settings
  - Environment variable management
  - Path resolution for Docker and local development
  - Database connection strings
  - API configuration

### Database (`app/database/`)
- **connection.py** - PostgreSQL connection pooling
  - Thread-safe connection management
  - Auto-initialization and cleanup
  
- **queries.py** - SQL query abstractions
  - 19 specialized query functions
  - Clean separation from business logic
  - Optimized queries with proper indexing

### Services (`app/services/`)
Business logic layer with 5 specialized services:

- **cluster_service.py** - Cluster operations
  - Load and manage cluster labels
  - Fetch clusters with enriched metadata
  - Get cluster details with nodes and edges

- **paper_service.py** - Paper operations
  - Crossref API integration with caching
  - Paper metadata fetching
  - Ego network generation

- **search_service.py** - Search functionality
  - Multi-strategy search (substring, trigram, fuzzy)
  - Token-based similarity scoring
  - Spatial proximity search

- **export_service.py** - Data export
  - NDJSON generation with atomic writes
  - Full graph streaming
  - Paginated exports

- **reading_list_service.py** - Recommendations
  - Spatial + citation-based filtering
  - Configurable scoring weights
  - Citation network expansion

### Routes (`app/routes/`)
API endpoints organized by domain (13 total):

- **clusters.py** - 4 endpoints
  - GET /clusters
  - GET /cluster/{cid}
  - GET /labels/parent
  - GET /labels/sub

- **papers.py** - 2 endpoints
  - GET /paper/{doi}
  - GET /ego

- **search.py** - 2 endpoints
  - GET /find
  - GET /find/nearby

- **export.py** - 4 endpoints
  - GET /export/ndjson/initial/meta
  - GET /export/initial.ndjson
  - GET /export/ndjson
  - GET /export/json

- **graph.py** - 1 endpoint
  - GET /reading_list

- **pipeline.py** - Build orchestration
  - Create runs, trigger builds, manage pipeline lifecycle

- **scoring.py** - Scoring endpoints
  - Node scoring and relevance

- **lod.py** - Level-of-detail
  - LOD data for graph visualization at different zoom levels

- **recommendations.py** - Reading-list recommendations
  - Spatial + citation-based paper recommendations

## 🚀 Running

### Development
```bash
cd backend
python run.py
```

### Docker
```bash
# From project root
docker-compose -f docker-compose.unified.yml up -d backend postgres
```

## 🧪 Testing

Run integration tests from the project root (requires backend and postgres running):

```bash
python tests/run_integration_tests.py
```

## 📊 Key Features

- **Modular Design** - Easy to maintain and extend
- **Type Safety** - Full type hints throughout
- **Error Handling** - Comprehensive error management
- **Documentation** - Detailed docstrings for all functions
- **Performance** - Connection pooling and optimized queries
- **Testability** - Clean separation allows easy testing

## 🔧 Configuration

Environment variables (set in Docker or `.env`):

- `DATABASE_URL` - PostgreSQL connection string
- `LABEL_BASE` - Base name for label files
- `CORS_ORIGINS` - Allowed CORS origins

## 📝 API Documentation

Interactive API docs available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc


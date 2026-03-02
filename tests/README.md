# paper_graph Testing Guide

## Overview
This directory contains unit, integration, and labeling tests for the paper_graph backend and frontend.

## Test Organization

```
tests/
├── conftest.py                 # Pytest configuration, test environment setup
├── test_basic.py              # Basic smoke tests
├── unit/                      # Unit tests (mocked dependencies)
│   ├── test_database/        # Database connection tests
│   ├── test_services/        # Service layer tests (cluster, search, LOD, recommendations)
│   └── test_models/          # Data model tests
├── integration/              # Integration tests (real API calls)
│   └── test_api/            # API endpoint tests
└── labeling/                # Data pipeline labeling tests
    └── test_prompts_and_parsing.py
```

## Running Tests

### Prerequisites
1. **Docker postgres must be running**:
   ```bash
   docker-compose -f docker-compose.unified.yml up postgres -d
   ```

2. **Database must be initialized** with at least one graph (run_id)

### Backend Tests

#### Run All Tests
```bash
python -m pytest tests/ -v
```

#### Run Specific Test Categories
```bash
# Unit tests only
python -m pytest tests/unit/ -v

# Integration tests only
python -m pytest tests/integration/ -v

# Labeling tests only
python -m pytest tests/labeling/ -v
```

#### Run Specific Test File
```bash
python -m pytest tests/unit/test_services/test_recommendations_service.py -v
```

#### Run with Coverage (future)
```bash
python -m pytest tests/ --cov=backend --cov-report=html
open htmlcov/index.html
```

### Frontend Tests

#### Run All Tests
```bash
cd frontend
npm test -- --run
```

#### Watch Mode (auto-rerun on changes)
```bash
cd frontend
npm test
```

#### Interactive UI
```bash
cd frontend
npm run test:ui
```

## Test Environment Configuration

### Database Connection
- **Local tests**: Use `localhost:5432` (configured in `conftest.py`)
- **Docker tests**: Use `postgres:5432` (Docker internal hostname)
- **Environment variable**: `DATABASE_URL=postgresql://pg:secret@localhost:5432/litsearch`

The `conftest.py` file automatically sets `DATABASE_URL` for local testing if not already set.

### Frontend Setup
- **Test framework**: Vitest with jsdom
- **Component testing**: React Testing Library
- **localStorage**: Auto-cleared after each test (see `frontend/src/test/setup.js`)

## Writing New Tests

### Backend Unit Tests

**Template**:
```python
import pytest
from unittest.mock import patch, MagicMock

from backend.app.services.my_service import MyService


class TestMyService:
    @patch('backend.app.services.my_service.queries')
    def test_something(self, mock_queries):
        # Arrange
        mock_queries.fetch_something.return_value = [...]
        
        # Act
        service = MyService()
        result = service.do_something()
        
        # Assert
        assert result == expected
```

### Backend Integration Tests

**Template**:
```python
import requests

class TestMyEndpoint:
    BASE_URL = "http://localhost:8000"
    
    def test_my_endpoint(self):
        response = requests.get(f"{self.BASE_URL}/my/endpoint")
        assert response.status_code == 200
        data = response.json()
        assert "expected_field" in data
```

### Frontend Tests

**Hook test template**:
```javascript
import { renderHook, act } from '@testing-library/react';
import useMyHook from '../useMyHook';

it('does something', () => {
  const { result } = renderHook(() => useMyHook());
  
  act(() => {
    result.current.doSomething();
  });
  
  expect(result.current.value).toBe(expected);
});
```

**Component test template**:
```javascript
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MyComponent from '../MyComponent';

it('renders correctly', () => {
  render(<MyComponent prop="value" />);
  expect(screen.getByText('Expected Text')).toBeInTheDocument();
});
```

## Mocking Guidelines

### Database Mocking
- Use `@patch('backend.app.database.connection.get_db_connection')`
- Return `MagicMock` objects with proper context manager support:
  ```python
  mock_conn = MagicMock()
  mock_cursor = MagicMock()
  mock_cursor.fetchall.return_value = [...]
  mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
  mock_db.return_value.__enter__.return_value = mock_conn
  ```

### Query Mocking
- Use `@patch('backend.app.services.my_service.queries')`
- Mock specific query methods:
  ```python
  mock_queries.fetch_something.return_value = [...]
  mock_queries.get_active_run_id.return_value = 1
  ```

## Test Markers

### Available Markers
- `@pytest.mark.unit`: Unit tests (fast, fully mocked)
- `@pytest.mark.integration`: Integration tests (require running services)
- `@pytest.mark.slow`: Slow running tests

### Usage
```bash
# Run only unit tests
python -m pytest -m unit

# Skip slow tests
python -m pytest -m "not slow"
```

## Common Issues

### 1. "Connection refused" errors
**Problem**: Docker postgres not running
**Solution**: `docker-compose -f docker-compose.unified.yml up postgres -d`

### 2. "No active graph" warnings
**Problem**: Database has no graphs loaded
**Solution**: Run a pipeline build or load test data

### 3. Frontend "localStorage is not defined"
**Problem**: jsdom environment not configured
**Solution**: Check `vitest.config.js` has `environment: 'jsdom'`

## Future Improvements

1. **Add pytest-cov**: Generate actual coverage metrics
2. **Add Playwright**: E2E testing for complete workflows
3. **Add test fixtures**: Reusable test data sets
4. **Add benchmark tests**: Performance regression detection
5. **Add API contract tests**: Ensure API backwards compatibility

## Contributing

When adding new features:
1. Write tests FIRST (TDD) or alongside implementation
2. Aim for >80% coverage on new code
3. Include both happy path and error cases
4. Mock external dependencies (DB, API calls)
5. Use descriptive test names that explain what's being tested

## Contact
For questions about testing strategy or coverage, consult the development team.


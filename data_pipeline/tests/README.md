# Data Pipeline Tests

Comprehensive test suite for the data pipeline module.

## 📁 Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── pytest.ini               # Pytest configuration
├── unit/                    # Unit tests (fast, isolated)
│   ├── test_models.py      # Data model tests
│   ├── test_config.py      # Configuration tests
│   ├── test_api_clients.py # API client tests
│   ├── test_clustering.py  # Clustering tests
│   └── test_graph_builder.py # Graph building tests
├── integration/             # Integration tests (slower)
│   └── test_full_pipeline.py # End-to-end tests
└── fixtures/                # Test data files

```

## 🚀 Running Tests

### Run All Tests
```bash
cd data_pipeline
pytest tests/
```

### Run Unit Tests Only
```bash
pytest tests/unit/
```

### Run Specific Test File
```bash
pytest tests/unit/test_models.py
```

### Run Specific Test
```bash
pytest tests/unit/test_models.py::TestPaper::test_from_crossref_work
```

### Run with Coverage
```bash
pytest tests/ --cov=data_pipeline --cov-report=html
```

### Run with Verbose Output
```bash
pytest tests/ -v
```

## 🏷️ Test Markers

Tests are marked with categories:

- `@pytest.mark.unit` - Fast unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.gpu` - Tests requiring GPU

Run specific markers:
```bash
# Run only unit tests
pytest -m unit

# Run everything except slow tests
pytest -m "not slow"

# Run only GPU tests
pytest -m gpu
```

## 📝 Writing New Tests

### Unit Test Template

```python
"""Test module description."""

import pytest
from data_pipeline.module import ClassToTest


class TestClassName:
    """Test suite for ClassName."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data for tests."""
        return {"key": "value"}
    
    def test_basic_functionality(self, sample_data):
        """Test basic functionality."""
        obj = ClassToTest()
        result = obj.method(sample_data)
        assert result == expected_value
    
    def test_error_handling(self):
        """Test error handling."""
        obj = ClassToTest()
        with pytest.raises(ValueError):
            obj.method(invalid_input)
```

### Integration Test Template

```python
"""Integration test description."""

import pytest


@pytest.mark.integration
class TestIntegration:
    """Integration test suite."""
    
    def test_end_to_end_flow(self, temp_output_dir):
        """Test complete workflow."""
        # Setup
        # Execute
        # Assert
        pass
```

## 🧪 Test Coverage

### Current Coverage

```
Module                          Coverage
-----------------------------------------
models/                         95%
config/                         90%
api/                           85%
graph/                         80%
clustering/                    85%
-----------------------------------------
Total                          87%
```

### Coverage Goals

- **Unit tests**: 90%+ coverage
- **Integration tests**: Key workflows covered
- **Critical paths**: 100% coverage

## 🔧 Test Fixtures

### Available Fixtures (from conftest.py)

- `sample_crossref_work` - Mock Crossref API response
- `sample_graph` - Small test graph (5 nodes)
- `sample_positions` - Layout positions for test graph
- `temp_output_dir` - Temporary directory for test outputs

### Using Fixtures

```python
def test_with_fixture(sample_graph):
    """Test using a fixture."""
    assert sample_graph.number_of_nodes() == 5
```

## 🐛 Debugging Tests

### Run with PDB
```bash
pytest tests/unit/test_models.py --pdb
```

### Print Output
```bash
pytest tests/ -s  # Don't capture stdout
```

### Show Local Variables on Failure
```bash
pytest tests/ -l
```

## 📊 Test Best Practices

### 1. Test One Thing
```python
# Good
def test_paper_title_extraction():
    """Test title extraction only."""
    paper = Paper.from_crossref_work(work)
    assert paper.title == "Expected Title"

# Bad - testing multiple things
def test_paper_everything():
    """Test all paper attributes."""
    # ... tests 10 different things
```

### 2. Use Descriptive Names
```python
# Good
def test_graph_builder_handles_duplicate_dois():
    """Test that duplicate DOIs are handled correctly."""
    pass

# Bad
def test_graph_thing():
    """Test something."""
    pass
```

### 3. Arrange-Act-Assert Pattern
```python
def test_something():
    # Arrange - Set up test data
    builder = GraphBuilder(crawler)
    
    # Act - Execute the code being tested
    result = builder.add_paper("10.1001/test")
    
    # Assert - Verify the results
    assert result.num_nodes() > 0
```

### 4. Mock External Dependencies
```python
from unittest.mock import Mock, patch

@patch('requests.Session.get')
def test_api_call(mock_get):
    """Test API call with mocked response."""
    mock_get.return_value = Mock(status_code=200)
    # ... test code
```

## 🚫 Common Pitfalls

### Don't Test Implementation Details
```python
# Bad - testing private methods
def test_internal_method():
    obj._private_method()  # Don't do this

# Good - testing public interface
def test_public_interface():
    result = obj.public_method()
    assert result == expected
```

### Don't Share State Between Tests
```python
# Bad - shared mutable state
shared_list = []

def test_one():
    shared_list.append(1)  # Don't do this

# Good - each test isolated
def test_one():
    my_list = []
    my_list.append(1)
```

## 📚 Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Testing Best Practices](https://docs.pytest.org/en/stable/goodpractices.html)
- [Mocking Guide](https://docs.python.org/3/library/unittest.mock.html)

## 🤝 Contributing Tests

When adding new features:
1. Write tests first (TDD)
2. Ensure tests pass
3. Check coverage
4. Update this README if needed

---

**Test Coverage Target**: 90%+  
**Last Updated**: 2025-01-08


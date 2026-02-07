# Testing Guide

## Running Tests

### Quick Start

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=devmind --cov-report=html

# Run specific test file
pytest tests/test_rag_edge_cases.py -v

# Run specific test
pytest tests/test_rag_edge_cases.py::TestRAGEdgeCases::test_empty_query
```

### Test Categories

```bash
# Unit tests only (fast)
pytest -m unit

# Integration tests only (slower)
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

### Coverage Reports

After running tests with `--cov`, view the HTML report:

```bash
# Open in browser
start htmlcov/index.html  # Windows
open htmlcov/index.html   # macOS
xdg-open htmlcov/index.html  # Linux
```

## Test Structure

```
tests/
├── test_api_*.py          # API endpoint tests
├── test_embeddings.py     # Embedding service tests
├── test_vectorstore.py    # Vector store tests
├── test_retrieval_*.py    # Retrieval pipeline tests
├── test_rag_edge_cases.py # Edge case tests (NEW)
├── test_chat_integration.py # Integration tests (NEW)
└── test_integration.py    # End-to-end tests
```

## New Test Files

### test_rag_edge_cases.py

Tests edge cases and error conditions:

- **Empty/invalid queries**: Empty strings, whitespace, special characters
- **Oversized inputs**: Very long queries, large chunks
- **Concurrent operations**: Thread safety
- **Error recovery**: Corrupted indices, missing files
- **Boundary conditions**: Zero results, invalid top_k

**Example**:

```python
def test_empty_query(retrieval_pipeline):
    results = retrieval_pipeline.search("test_project", query="")
    assert len(results) == 0

def test_very_long_query(retrieval_pipeline):
    long_query = " ".join(["word"] * 10000)
    results = retrieval_pipeline.search("test_project", query=long_query)
    # Should handle gracefully
    assert isinstance(results, list)
```

### test_chat_integration.py

End-to-end integration tests:

- **Complete RAG workflow**: Ingestion → Retrieval → Chat
- **Streaming responses**: Async chunk handling
- **Context management**: Truncation, multi-turn conversations
- **Source citation**: Proper attribution
- **Error recovery**: Mixed valid/invalid files

**Example**:

```python
@pytest.mark.asyncio
async def test_complete_rag_pipeline(tmp_path):
    # 1. Ingest code
    result = pipeline.run()

    # 2. Add to index
    index_manager.add_chunks("test", result.chunks, encoder)

    # 3. Search
    search_results = retrieval_pipeline.search("test", query="add numbers")
    assert len(search_results) > 0
```

## Coverage Goals

Target: **85%+ code coverage**

### Current Coverage (Estimated)

| Module       | Coverage | Notes                  |
| ------------ | -------- | ---------------------- |
| api/         | 75%      | Good endpoint coverage |
| embeddings/  | 85%      | Well tested            |
| vectorstore/ | 80%      | Edge cases added       |
| retrieval/   | 70%      | New edge tests improve |
| ingestion/   | 65%      | Error handling tested  |
| llm/         | 60%      | Needs more mocking     |
| **Overall**  | **~72%** | **Target: 85%**        |

### Improving Coverage

Priority areas needing more tests:

1. **LLM providers** - Fallback scenarios, rate limiting
2. **Ingestion pipeline** - More error conditions
3. **Chat engine** - Context window handling
4. **API middleware** - Error handlers, rate limiting

## Writing Tests

### Test Naming

- Descriptive names: `test_empty_query_returns_no_results`
- Group by scenario: `TestErrorConditions`, `TestEdgeCases`
- Use markers: `@pytest.mark.integration`, `@pytest.mark.slow`

### Fixtures

```python
@pytest.fixture
def retrieval_pipeline(tmp_path):
    """Create test retrieval pipeline."""
    # Setup
    pipeline = create_pipeline(tmp_path)
    yield pipeline
    # Teardown (if needed)
```

### Async Tests

```python
@pytest.mark.asyncio
async def test_async_operation():
    result = await some_async_function()
    assert result is not None
```

### Mocking

```python
from unittest.mock import Mock, patch

def test_with_mock():
    mock_provider = Mock()
    mock_provider.generate.return_value = "response"

    result = use_provider(mock_provider)
    assert result == "response"
```

## Continuous Integration

### GitHub Actions (Future)

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest --cov --cov-fail-under=85
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Troubleshooting

### Import Errors

```bash
# Ensure devmind is in Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```

### Slow Tests

```bash
# Run with timeout
pytest --timeout=300

# Skip slow tests
pytest -m "not slow"
```

### Fixtures Not Found

```bash
# Check conftest.py exists
tests/conftest.py

# Verify fixture scope
@pytest.fixture(scope="session")
```

## Best Practices

1. **Fast tests**: Unit tests should run in <1s each
2. **Isolated**: No shared state between tests
3. **Deterministic**: No random failures
4. **Clear assertions**: One logical assertion per test
5. **Good coverage**: Test happy path + edge cases + error conditions

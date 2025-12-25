# Testing Guide

## Running Tests

### Backend Tests

```bash
cd backend

# Install test dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_validation.py

# Run specific test
pytest tests/test_cache.py::TestPromptCache::test_cache_hit

# Run marked tests only
pytest -m unit
```

### Frontend Tests

```bash
cd frontend

# Install dependencies
npm install

# Run tests
npm test

# Run tests with coverage
npm test -- --coverage
```

## Test Structure

### Backend Tests (`backend/tests/`)

- `test_validation.py` - Prompt and code security validation (15 tests)
- `test_cache.py` - Caching logic (prompt + video) (12 tests)
- `test_rate_limiter.py` - Rate limiting per IP (6 tests)
- `test_circuit_breaker.py` - Circuit breaker state machine (6 tests)

**Total: 39 unit tests**

### Test Coverage Goals

- **Validation Module**: >90% coverage
- **Cache Module**: >85% coverage  
- **Rate Limiter**: >80% coverage
- **Circuit Breaker**: >85% coverage

## CI/CD Pipeline

GitHub Actions runs tests automatically on:
- Push to `main` or `develop`
- Pull requests

**Pipeline includes:**
1. Backend tests (Python 3.9, 3.10, 3.11)
2. Frontend build verification
3. Code quality (Black, Flake8, isort)
4. Coverage reports

## Writing New Tests

### Unit Test Template

```python
import pytest
from src.your_module import YourClass

class TestYourClass:
    \"\"\"Test YourClass functionality.\"\"\"
    
    def test_basic_functionality(self):
        \"\"\"Test basic use case.\"\"\"
        obj = YourClass()
        result = obj.method()
        assert result == expected_value
    
    def test_error_handling(self):
        \"\"\"Test error scenarios.\"\"\"
        obj = YourClass()
        with pytest.raises(ValueError):
            obj.method_that_fails()
```

### Integration Test Template

```python
from fastapi.testclient import TestClient
from src.app import app

client = TestClient(app)

def test_generate_endpoint():
    \"\"\"Test full generation flow.\"\"\"
    response = client.post(\"/generate\", json={
        \"prompt\": \"A blue circle\",
        \"quality\": \"m\"
    })
    assert response.status_code == 200
    assert \"videoUrl\" in response.json()
```

## Continuous Integration

View test results and coverage:
- **GitHub Actions**: Check "Actions" tab in repository
- **Coverage Reports**: Uploaded to Codecov
- **Local HTML Report**: `backend/htmlcov/index.html`

## Best Practices

1. **Test Naming**: Use descriptive names that explain what's being tested
2. **Arrange-Act-Assert**: Structure tests clearly
3. **Isolation**: Each test should be independent
4. **Mocking**: Mock external dependencies (APIs, file system)
5. **Coverage**: Aim for >80% overall coverage

## Common Issues

### Import Errors
```bash
# Make sure you're in the backend directory
cd backend
pytest
```

### Async Test Failures
```bash
# Install pytest-asyncio
pip install pytest-asyncio
```

### Coverage Not Showing
```bash
# Generate HTML report
pytest --cov=src --cov-report=html
# Open htmlcov/index.html in browser
```

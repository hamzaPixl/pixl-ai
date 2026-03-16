---
paths:
  - "**/test_*.py"
  - "**/*_test.py"
  - "**/tests/**/*.py"
  - "**/conftest.py"
---
# Python Testing Rules

## Framework

- Use **pytest** (not unittest) for all new tests
- Use **httpx.AsyncClient** for FastAPI endpoint tests
- Use **pytest-asyncio** for async test functions

## Test Structure

```python
class TestUserService:
    def test_creates_user_with_valid_email(self, user_service):
        # Arrange
        input_data = CreateUserInput(email="test@example.com")
        # Act
        user = user_service.create(input_data)
        # Assert
        assert user.email == "test@example.com"
```

## Fixtures

- Use `conftest.py` for shared fixtures
- Scope fixtures appropriately: `function` (default), `class`, `module`, `session`
- Use `@pytest.fixture` with `yield` for setup/teardown
- Use factory fixtures for parameterized test data

## Markers

- `@pytest.mark.slow` — tests taking > 1 second
- `@pytest.mark.integration` — tests requiring external services
- `@pytest.mark.e2e` — end-to-end workflow tests
- Register all markers in `pyproject.toml` `[tool.pytest.ini_options]`

## Mocking

- Use `pytest-mock` (`mocker` fixture) over `unittest.mock` directly
- Mock at boundaries: external APIs, databases, file system
- Use `respx` for mocking httpx requests
- Prefer dependency injection over patching when possible

## Coverage

```bash
uv run pytest --cov=src --cov-report=term-missing
```

Aim for 80%+ on business logic. Don't test Pydantic models or FastAPI glue.

---
paths:
  - "**/*.py"
  - "**/pyproject.toml"
---
# Python Coding Style Rules

## Formatting

- Use **ruff** for formatting and linting (replaces black + isort + flake8)
- Line length: 88 (ruff/black default)
- Use `ruff check --fix` for auto-fixable lint issues

## Type Hints

- Type-annotate all public functions and methods
- Use `from __future__ import annotations` for deferred evaluation
- Prefer `X | Y` union syntax over `Union[X, Y]` (Python 3.10+)
- Use `TypeAlias` for complex type definitions

## Naming

- Functions/variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private: prefix with `_` (single underscore)
- Protected: prefix with `_` (NOT double underscore)

## Data Classes

- Use `@dataclass` for data containers, Pydantic `BaseModel` for validated data
- Prefer `@dataclass(frozen=True)` for immutable data
- Use `__slots__` for performance-critical data classes

## Error Handling

- Define custom exception hierarchies per domain
- Use `raise ... from err` to chain exceptions
- Never catch bare `Exception` — catch specific types
- Use `contextlib.suppress()` for intentionally ignored exceptions

## Async

- Use `async/await` for I/O-bound operations
- Use `asyncio.gather()` for concurrent async calls
- Never mix sync and async — use `asyncio.to_thread()` for blocking calls in async context
- Use `httpx` (async) over `requests` (sync) in async codebases

## Imports

- Group: stdlib → third-party → local (ruff enforces this)
- Use absolute imports over relative
- Avoid wildcard imports (`from module import *`)

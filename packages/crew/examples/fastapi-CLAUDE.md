# Project Name — FastAPI Service

## Overview

Python microservice built with FastAPI, Pydantic, and SQLAlchemy/Prisma.

## Stack

- **Framework**: FastAPI 0.115+
- **Validation**: Pydantic v2 (strict mode)
- **Database**: PostgreSQL via SQLAlchemy 2.0 or Prisma Client Python
- **Task queue**: Celery + Redis (optional)
- **Testing**: pytest + httpx
- **Package manager**: uv

## Structure

```
src/
├── api/
│   ├── routes/              # FastAPI routers
│   ├── dependencies/        # Dependency injection (DB sessions, auth)
│   └── middleware/           # CORS, logging, auth
├── domain/
│   ├── entities/            # Pydantic models (domain entities)
│   ├── services/            # Business logic
│   └── events/              # Domain events
├── infrastructure/
│   ├── repositories/        # Database access
│   ├── external/            # Third-party API clients
│   └── config.py            # Settings via pydantic-settings
tests/
├── unit/                    # Fast tests, mocked deps
├── integration/             # DB + API tests
└── conftest.py              # Shared fixtures
```

## Commands

```bash
uv run uvicorn src.main:app --reload    # Dev server
uv run pytest tests/ -v                  # Run tests
uv run ruff check .                      # Lint
uv run ruff format .                     # Format
```

## Conventions

- **Entities**: Pydantic BaseModel with validators, not raw dicts
- **Routes**: `/v1/resources` prefix, typed request/response models
- **Dependencies**: Use FastAPI `Depends()` for injection
- **Error handling**: HTTPException with structured error responses
- **Config**: `pydantic-settings` with `.env` files

## Key Patterns

- Repository pattern for database access
- Service layer for business logic (not in routes)
- Pydantic models for all API boundaries (request, response, internal)
- Dependency injection via FastAPI's `Depends` system
- Background tasks via Celery or FastAPI BackgroundTasks

## Don't

- Don't put business logic in route handlers
- Don't use raw dicts for API responses — use Pydantic models
- Don't skip type hints — full typing required
- Don't use synchronous DB calls — use async SQLAlchemy or async Prisma

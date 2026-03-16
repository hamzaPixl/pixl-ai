# Python Backend Patterns

Patterns used in Python/FastAPI codebases (e.g. pixl-platform). These complement the TypeScript patterns — agents should detect the project language from `pyproject.toml` vs `package.json` and apply the correct set.

## Pydantic Entity Pattern

Python codebases use mutable Pydantic `BaseModel` instead of immutable TypeScript classes:

```python
from pydantic import BaseModel, Field
from datetime import datetime

class WorkflowConfig(BaseModel):
    id: str
    name: str
    stages: list[StageConfig] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1

    # Mutations are in-place (Pythonic) — no immutable copy pattern
    def add_stage(self, stage: StageConfig) -> None:
        self.stages.append(stage)
        self.version += 1

    # Serialize for storage
    def to_dict(self) -> dict:
        return self.model_dump()

    # Reconstitute from storage
    @classmethod
    def from_dict(cls, data: dict) -> "WorkflowConfig":
        return cls.model_validate(data)
```

### Key Differences from TypeScript DDD

| TypeScript | Python |
|---|---|
| Private constructor + static `create()` | Public `__init__` via Pydantic |
| Immutable — `update()` returns new instance | Mutable — methods modify `self` |
| `toPersistence()` / `fromPersistence()` | `model_dump()` / `model_validate()` |
| Zod for validation | Pydantic validators / `Field()` |
| Version via new instance | Version increment in-place |

## FastAPI Route Conventions

```python
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

router = APIRouter(prefix="/sessions", tags=["sessions"])

@router.get("/")
async def list_sessions(
    project_id: str,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    # Return paginated list
    return {"data": items, "meta": {"total": total, "limit": limit, "offset": offset}}

@router.post("/", status_code=201)
async def create_session(body: CreateSessionRequest) -> dict:
    # Create and return
    return {"data": session.to_dict()}

@router.get("/{session_id}")
async def get_session(session_id: str) -> dict:
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return {"data": session.to_dict()}
```

### Conventions

- Use `APIRouter` with `prefix` and `tags`
- Dependency injection via `Depends()`
- `HTTPException` for errors (FastAPI returns `{"detail": "..."}` automatically)
- Background work via `BackgroundTasks`
- Response format: `{"data": ...}` for single, `{"data": [...], "meta": {...}}` for lists

## File-Based Storage Pattern (*Store classes)

For lightweight persistence (SQLite, JSON files), the platform uses `*Store` classes:

```python
class ConfigStore:
    """Persists workflow configs to SQLite via PixlDB."""

    def __init__(self, db: PixlDB) -> None:
        self._db = db

    def save(self, config: WorkflowConfig) -> None:
        self._db.upsert("configs", config.to_dict(), key="id")

    def get(self, config_id: str) -> WorkflowConfig | None:
        row = self._db.get("configs", config_id)
        return WorkflowConfig.from_dict(row) if row else None

    def list_all(self) -> list[WorkflowConfig]:
        return [WorkflowConfig.from_dict(r) for r in self._db.list("configs")]
```

This is distinct from the TypeScript repository pattern (Prisma + UoW). Both are valid — choose based on the project's stack.

## Testing Conventions (pytest)

```python
import pytest

class TestWorkflowConfig:
    def test_add_stage_increments_version(self):
        config = WorkflowConfig(id="w1", name="test")
        config.add_stage(StageConfig(name="build"))
        assert config.version == 2
        assert len(config.stages) == 1

    def test_roundtrip_serialization(self):
        config = WorkflowConfig(id="w1", name="test")
        restored = WorkflowConfig.from_dict(config.to_dict())
        assert restored == config
```

- Use `pytest` (not unittest)
- Group related tests in classes
- Fixtures via `@pytest.fixture` and `conftest.py`
- Async tests with `@pytest.mark.asyncio`
- Mocking with `unittest.mock.patch` or `pytest-mock`

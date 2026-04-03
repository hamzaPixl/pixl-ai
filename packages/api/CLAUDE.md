# pixl-api

FastAPI service wrapping pixl-engine — REST endpoints, JWT auth, WebSocket events.

## Structure

```
pixl_api/
├── app.py              # FastAPI factory + lifespan (pool cleanup)
├── auth/               # JWT auth (HS256, 24h expiry, 60s grace)
│   ├── jwt.py          # Token create/decode, secret auto-generation (~/.pixl/jwt_secret)
│   ├── hashing.py      # Bcrypt password hashing (8-char minimum)
│   └── dependencies.py # CurrentUser dependency, get_current_user()
├── routes/             # 24 route modules, ~144 endpoints
├── schemas/            # Pydantic request/response models per domain
├── foundation/         # JWT utils, error handlers, pagination helpers
├── db/                 # User/workspace SQLite DB (~/.pixl/api.db, WAL mode)
│   ├── schema.py       # 8 tables: users, workspaces, members, teams, invitations, projects, api_keys
│   └── operations.py   # User/workspace CRUD
├── ws.py               # WebSocket event stream (poll-based, 1s interval)
├── pool.py             # LRU ProjectDB connection pool (50 max, 5-min TTL)
└── db.py               # DB initialization + connection factory
tests/                  # ~157 tests (pytest + httpx.AsyncClient)
```

## Auth Flow

1. Login/signup → JWT (HS256, 24h expiry) stored as `auth` cookie or Bearer token
2. JWT secret: `$JWT_SECRET` env → auto-generated file at `~/.pixl/jwt_secret` (0600 perms)
3. Protected endpoints use `CurrentUser` dependency annotation
4. 60-second grace period on expired tokens for refresh
5. Workspace ID sent via `X-Workspace-ID` header

## Route Modules

| Module | Key Endpoints |
|--------|--------------|
| `auth.py` | login, signup, me, refresh |
| `sessions.py` | CRUD, pause/resume, nodes, report |
| `features.py` | CRUD via factory, transitions, history |
| `epics.py` | CRUD via factory, feature tree |
| `roadmaps.py` | CRUD via factory |
| `workflows.py` | list, detail, snapshots |
| `run.py` | execute workflow, stream results |
| `artifacts.py` | list, get, search |
| `events.py` | list, counts, transitions |
| `gates.py` | inbox, approve/reject |
| `agents.py` | config, model selection |
| `projects.py` | CRUD, list |
| `workspaces.py` | CRUD, members, invitations (20 endpoints) |
| `metrics.py` | agent/workflow performance |
| `usage.py` | token costs, budget |
| `views.py` | pre-aggregated projections |
| `dashboard.py` | summary, progress |
| `config.py` | project runtime config |
| `chains.py` | control flow chains |
| `recovery.py` | incident management |
| `sandbox.py` | sandbox execution |
| `github.py` | GitHub integration |
| `health.py` | health check |

## CRUD Router Factory

`foundation/crud_factory.py` generates 9 endpoints per entity (list, create, get, put, patch, delete, transition, history, transitions). Uses `exec()` for dynamic function generation (FastAPI introspection requirement). Used by features, epics, roadmaps.

## Connection Pool

`pool.py` — LRU cache of per-project PixlDB instances:
- Max 50 connections, 5-min idle TTL
- Reentrant lock for thread-safety
- Evicts oldest FIFO when full
- Critical: `project_pool.close_all()` called on shutdown via lifespan

## WebSocket

`GET /api/ws/events/{project_id}?token=JWT` — poll-based relay (1s intervals) from SQLite events table. Client sends `{"subscribe": "session-id"}` for session filtering. Keepalive pings every cycle.

## Error Handling

- `APIError` base → specific codes (401/403/404/409/422/400)
- Domain: `EntityNotFoundError`, `InvalidTransitionError`, `GateNotWaitingError`
- Unified response: `{error: {code, message, request_id, timestamp}}`
- Catch-all middleware logs unhandled exceptions

## Testing

```bash
make test-api                           # all API tests (~157)
uv run pytest packages/api/tests/ -x    # with early exit
uv run pytest packages/api/tests/test_run.py  # single file
```

- `conftest.py`: monkeypatch for isolated SQLite DB per test
- Mock backlog storage for unit tests
- httpx.AsyncClient for integration tests
- Covers: foundation, DB ops, routes, CRUD factory, auth

## Gotchas

- Pool cleanup is critical — if `close_all()` doesn't run on shutdown, SQLite connections leak
- JWT secret auto-generates on first run — don't delete `~/.pixl/jwt_secret` in production
- WebSocket is poll-based (not push) — 1s latency is by design for SQLite compatibility
- CRUD factory uses `exec()` — breakpoints inside generated functions need special handling
- Workspace auto-created on signup/login — every user always has a default workspace

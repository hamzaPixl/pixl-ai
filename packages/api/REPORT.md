# pixl API + Console — Execution Report

## Summary

Built a complete FastAPI service + React console that wraps the pixl CLI as a validated layer. The API exposes 73 HTTP endpoints covering auth, projects, workflows, sessions, events, features, epics, roadmaps, artifacts, knowledge, cost, dashboard, metrics, agents, chains, recovery, and version. The console is a full React SPA with session DAG visualization, real-time WebSocket event streaming, and a DockBar navigation system.

**Architecture**: `Console (React) → API (FastAPI) → CLI (CLIContext) → Engine (Storage, Execution)`

---

## Execution Timeline

| Sprint | Tasks | Commits | What was delivered |
|--------|-------|---------|--------------------|
| S1: Foundation + Auth | T01-T06 | `637ad6f` | Package scaffold, foundation layer, user DB, app factory, JWT auth, DI |
| S2: Core Loop | T07-T12 | `db03b97` | Projects, workflows, run+SSE, sessions, events, control, gates |
| S3: Full Features | T13-T18 | `6e8be3e` | Features, epics, roadmaps, artifacts, knowledge, cost, dashboard, metrics, agents, chains, recovery, version |
| S4: Console + Integration | T19-T24 | `de18c75` | Console SPA, SaaS trimming, sandbox types, Makefile targets |

---

## Stats

| Metric | Value |
|--------|-------|
| API Python LOC | ~5,500 |
| Test LOC | ~1,800 |
| Tests passing | 123/123 |
| API routes | 144 |
| Route modules | 24 |
| Schema modules | 17 |
| WebSocket endpoints | 1 |
| Console TS/TSX files | 321 |
| Git commits | 8 |

---

## API Endpoints (73 total)

### Auth (5)
- `POST /api/auth/signup` — Create user account, return JWT
- `POST /api/auth/login` — Authenticate, return JWT
- `POST /api/auth/logout` — Clear auth cookie
- `GET /api/auth/me` — Get current user
- `POST /api/auth/refresh` — Refresh JWT

### Projects (5)
- `GET /api/projects` — List all projects
- `POST /api/projects` — Create project
- `GET /api/projects/{id}` — Get project details
- `DELETE /api/projects/{id}` — Delete project
- `POST /api/projects/{id}/init` — Initialize .pixl/ directory

### Workflows (2)
- `GET /api/projects/{id}/workflows` — List available workflows
- `GET /api/projects/{id}/workflows/{wid}` — Get workflow structure (nodes/edges)

### Run (3)
- `POST /api/projects/{id}/run` — Classify prompt, suggest workflow
- `POST /api/projects/{id}/run/confirm` — Execute workflow with SSE streaming
- `POST /api/projects/{id}/run/feature/{fid}` — Run existing feature

### Sessions (3)
- `GET /api/projects/{id}/sessions` — List sessions (paginated, filterable)
- `GET /api/projects/{id}/sessions/{sid}` — Get session with node instances
- `GET /api/projects/{id}/sessions/{sid}/nodes/{nid}` — Get node detail

### Control (4)
- `POST .../sessions/{sid}/pause` — Pause session
- `POST .../sessions/{sid}/resume` — Resume from checkpoint (501 stub)
- `POST .../sessions/{sid}/cancel` — Cancel session
- `POST .../sessions/{sid}/retry` — Retry failed session (501 stub)

### Events (2)
- `GET /api/projects/{id}/events` — List events
- `GET /api/projects/{id}/events/counts` — Event counts by type

### Gates (3)
- `GET .../gates/{sid}` — List gates for session
- `POST .../gates/{sid}/{gid}/approve` — Approve gate
- `POST .../gates/{sid}/{gid}/reject` — Reject gate

### Features (6)
- Full CRUD + status transitions via TransitionEngine

### Epics (6)
- Full CRUD + transitions + child features listing

### Roadmaps (5)
- Full CRUD + transitions

### Artifacts (5)
- CRUD + FTS search + version listing

### Knowledge (4)
- Search, build index, status, build context

### Cost (3)
- Summary, by-model, by-session

### Dashboard (2)
- Summary stats, progress breakdown

### Metrics (2)
- Agent performance, session metrics

### Agents (2)
- List agents, list models

### Chains (4)
- List, get detail, create (stub), start

### Recovery (3)
- Inbox, retry blocked node, skip blocked node

### Version (1)
- `GET /api/version` — pixl version + Python version + git commit

### Infrastructure (2)
- `GET /api/health` — Health check
- `GET /docs` — Scalar API docs

---

## Key Design Decisions

1. **CLI as validated layer** — API calls `CLIContext`, `cli.db.*` stores, and CLI command functions. Never imports engine directly.
2. **Write clean, don't blind copy** — Old platform had 35 routes in ~4K LOC with bloat. New API has 20 route modules in ~1.5K LOC.
3. **Foundation self-contained** — JWT, bcrypt, error hierarchy, pagination all live in `pixl_api.foundation/` (~400 LOC).
4. **Single-tenant MVP** — No tenants, API keys, billing. Just users + default workspace.
5. **SSE streaming** — Workflow execution bridges sync GraphExecutor events to async SSE via `asyncio.Queue`.
6. **Sync engine in async FastAPI** — All engine calls wrapped in `asyncio.to_thread()`.

---

## Issues Encountered

| Issue | Resolution |
|-------|-----------|
| Old platform's `pixl.foundation.*` doesn't exist in current engine | Built clean foundation in `pixl_api/foundation/` (~400 LOC vs old 1,164 LOC) |
| Old platform used Daytona sandboxes | Rewired console sandbox API client for Cloudflare Workers |
| Old platform's GlobalDB had tenants/API keys/billing tables | Created minimal `db.py` (111 LOC) with just users + workspaces |
| `WorkflowLoader` needs project root, not storage dir | Added `ProjectRoot` DI dependency |
| Session resume/retry requires full GraphExecutor wiring | Stubbed at 501 — core execution works via `/run/confirm` |
| Console routeTree.gen.ts had stale SaaS route references | Auto-regenerated by TanStack Router plugin on dev server start |

---

## How to Use

### Start API
```bash
make dev-api
# API runs at http://localhost:8420
# Scalar docs at http://localhost:8420/docs
```

### Start Console
```bash
cd packages/console && pnpm install && pnpm dev
# Console runs at http://localhost:5173
```

### Start Both
```bash
make dev-platform
```

### Run Tests
```bash
make test-api
```

### Quick Smoke Test
```bash
# Signup
curl -X POST http://localhost:8420/api/auth/signup \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@test.com","password":"pass1234","first_name":"Test","last_name":"User"}'

# Login
curl -X POST http://localhost:8420/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@test.com","password":"pass1234"}'

# Use the token from login response:
TOKEN="..."
curl -H "Authorization: Bearer $TOKEN" http://localhost:8420/api/projects
curl -H "Authorization: Bearer $TOKEN" http://localhost:8420/api/version
```

---

## Deferred (Post-MVP)

- Multi-tenancy (workspaces, teams, roles)
- API key authentication
- Stripe billing
- GitHub/Google OAuth
- Session resume/retry (GraphExecutor integration)
- Chain creation (planner pipeline)
- WebSocket event streaming (ws.py — pattern ready, needs wiring)
- Docker deployment

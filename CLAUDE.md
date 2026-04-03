# pixl

AI dev platform — orchestration engine + Claude Code crew plugin.

## Structure

```
pyproject.toml                  # uv workspace root (name="pixl")
Makefile                        # setup, install, test, check, format, release
packages/
├── engine/                     # pixl-engine (Python) — DAG orchestration, LLM providers, SQLite storage
│   ├── pyproject.toml
│   ├── pixl/                   # ~200 modules
│   └── tests/
├── cli/                        # pixl-cli (Python) — Click-based `pixl` binary
│   ├── pyproject.toml          # bundles crew via force-include
│   ├── pixl_cli/
│   │   ├── main.py             # Click group + setup command
│   │   ├── crew.py             # get_crew_root() resolver
│   │   ├── sandbox_client.py   # HTTP client for sandbox API (JWT, SSE, token refresh)
│   │   └── commands/           # artifact, config, cost, events, knowledge, project, sandbox, session, setup, state, template, workflow
│   └── tests/
├── api/                        # pixl-api (Python) — FastAPI service over pixl-cli
│   ├── pyproject.toml
│   ├── pixl_api/               # 24 route modules, 144 endpoints
│   │   ├── app.py              # FastAPI factory + lifespan
│   │   ├── auth/               # JWT auth, bcrypt, dependencies
│   │   ├── routes/             # All API routes (sessions, features, views, budget, etc.)
│   │   ├── schemas/            # Pydantic request/response models
│   │   ├── foundation/         # JWT, error handlers, pagination
│   │   ├── ws.py               # WebSocket event stream
│   │   ├── pool.py             # LRU ProjectDB connection pool
│   │   └── db.py               # User/workspace/API-key SQLite DB
│   └── tests/                  # 123 tests (DB, routes, auth, workspaces, API keys)
├── console/                    # pixl-console (TypeScript) — React SPA
│   ├── package.json
│   ├── src/                    # 321 TS/TSX files
│   │   ├── routes/             # TanStack Router file-based routing
│   │   ├── components/         # Dashboard, sessions, features, settings
│   │   ├── hooks/              # React Query hooks, WebSocket event stream
│   │   ├── lib/api/            # Typed API client (12 domain modules)
│   │   ├── stores/             # Zustand (auth, project, UI)
│   │   └── types/              # TypeScript interfaces
│   ├── vite.config.ts          # Vite + proxy to API at :8420
│   └── tests/                  # Playwright E2E
├── crew/                       # pixl-crew (bash/md) — NOT a Python package
│   ├── .claude-plugin/
│   ├── agents/                 # 14 agents
│   ├── skills/                 # 75 skills (see skills/ROUTING.md)
│   ├── hooks/                  # event hooks
│   ├── references/             # shared domain knowledge
│   ├── studio/stacks/          # nextjs, saas scaffolds
│   ├── contexts/               # dynamic context overlays
│   ├── examples/               # CLAUDE.md templates
│   ├── schemas/                # JSON schemas
│   └── scripts/                # setup, release, scaffold
└── sandbox/                    # pixl-sandbox (TypeScript) — Cloudflare Sandbox containers
    ├── docker/                 # Dockerfile, init.sh, test workflow
    ├── src/                    # Hono router + Durable Object
    ├── scripts/                # e2e test script
    └── wrangler.jsonc          # Cloudflare Workers config
scripts/release.sh              # monorepo release script
.claude/rules/                  # coding style, testing, security, git, etc.
```

## Setup

```bash
# Full setup (recommended)
make setup                      # uv sync + pixl setup (registers crew with Claude Code)

# From PyPI
uv tool install pixl && pixl setup

# Crew-only (no Python/engine needed)
cd packages/crew && make setup

# Start API + Console (web UI)
make dev-platform               # API at :8420 + Console at :5173

# Optional: install RTK for 60-90% Bash token savings
brew install rtk && rtk init -g --hook-only
```

## Engine Architecture

### Core Domain Models

| Hierarchy | Models | Purpose |
|-----------|--------|---------|
| **Backlog** | Roadmap → Epic → Feature | What to build (planning) |
| **Execution** | WorkflowTemplate → WorkflowSession → NodeInstance | How to build it (runtime) |

Key models:
- **Baton** — inter-stage context relay
- **ExecutionGraph** — DAG of nodes + edges
- **ExecutorCursor** — tracks position in DAG during execution
- **EventBus** — in-process pub/sub for real-time event distribution
- **AgentRegistry** — parses crew agent markdown into SDK `AgentDefinition` objects

### Storage Layer

- **PixlDB** — SQLite with WAL mode, FTS5 for search, schema v37 (40+ tables)
- Protocol-based stores: `BacklogStore`, `SessionStore`, `ArtifactStore`, `EventStore`, `KnowledgeStore`, `ConfigStore`, `WorkflowStore`, `CostEventDB`, `WorkflowTemplateDB`, `SandboxDB`

### Execution Pipeline

```
WorkflowTemplate → WorkflowSession → GraphExecutor → ChainRunnerManager → TaskExecutor → OrchestratorCore
```

### Providers

**ProviderRegistry** — multi-provider LLM support (Anthropic, OpenAI, Gemini).

## CLI Reference

| Command | Description |
|---------|-------------|
| `pixl project init` | Initialize a `.pixl/` project directory |
| `pixl project new <name>` | Create a new project (dir + git + crew + optional setup workflow) |
| `pixl workflow run` | Execute a workflow template (auto-selects from prompt if `--workflow` omitted, `--yes` to auto-approve gates) |
| `pixl session list` | List workflow sessions |
| `pixl artifact list` | List build artifacts |
| `pixl knowledge build` | Build AST-indexed knowledge base |
| `pixl knowledge search` | Search knowledge base |
| `pixl state show` | Show entity state and transitions |
| `pixl events list` | List execution events |
| `pixl config get` | Get project configuration |
| `pixl cost summary` | Cost analytics: total, by-model, by-session |
| `pixl template list` | Manage DB-backed workflow templates (CRUD) |
| `pixl sandbox create` | Create sandbox project (`--fork-from` for session continuity) |
| `pixl sandbox workflow` | Run workflow in sandbox (with `--stream` for SSE) |
| `pixl sandbox sync` | Sync sandbox data (events, sessions, artifacts) to local DB |
| `pixl setup` | Register crew plugin with Claude Code |

Global options: `--json` (JSON output, NDJSON streaming for workflow run), `--project <path>` (project root).

## Crew Plugin

14 agents, 75 skills, 2 studio stacks (nextjs, saas) — see `packages/crew/CLAUDE.md` for full reference.

Hooks use `.pixl/pixl.db` (SQLite) when CLI is installed, falling back to `.claude/memory/` (file-based).

## Development

| Command | What it does |
|---------|-------------|
| `make setup` | Full setup: install + register crew |
| `make install` | Install workspace packages |
| `make test` | Run all tests (engine + cli + api) |
| `make test-engine` | Engine tests only |
| `make test-cli` | CLI tests only |
| `make test-api` | API tests only (157 tests) |
| `make test-cov` | Run tests with coverage report |
| `make check` | Lint + type check |
| `make typecheck` | Type check only (pyright) |
| `make format` | Auto-format |
| `make dev-api` | Start API dev server (port 8420) |
| `make dev-console` | Start Console dev server (port 5173) |
| `make dev-platform` | Start both API + Console |
| `make release` | Bump version, tag, push |

Engine deps are split: core deps always installed, API deps (`fastapi`, `redis`, `bcrypt`, `pyjwt`) optional via `[api]` extra.

## Environment

- Python 3.12+ (uv workspace)
- Node 20+ (console SPA)
- uv 0.4+ (package manager)

## Gotchas

- `packages/engine/pixl/execution/graph_executor.py` is ~77K — always use `offset`/`limit` when reading
- `contract_validator.py` (52K), `workflow_session_store.py` (46K), `task_executor.py` (44K) — same rule
- `packages/cli/pixl_cli/_crew/` is auto-synced from `packages/crew/` at build time — never edit directly
- Schema v37 with 40+ tables — adding tables requires bumping the version in `pixl/storage/db/schema.py`
- Engine deps are split: core deps always installed, API deps (`fastapi`, `redis`, `bcrypt`, `pyjwt`) optional via `[api]` extra
- All protocol-based stores (BacklogStore, SessionStore, etc.) are duck-typed interfaces — import protocols, not concrete implementations

## Operational Rules

- **Explore → Plan → Implement → Commit** — plan mode for multi-file changes
- **Skills over ad-hoc prompts** — if a skill exists, use it
- **Minimal changes** — only what's requested
- **Frequent commits** — commit after each logical unit
- **Parallel execution** — launch independent agents/tools concurrently
- **CLI-first** — crew hooks and agents use pixl CLI for persistence when available

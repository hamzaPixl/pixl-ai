# pixl

AI dev platform — orchestration engine + Claude Code crew plugin.

## Structure

```
pyproject.toml                  # uv workspace root (name="pixl")
Makefile                        # setup, install, test, check, format, release
packages/
├── engine/                     # pixl-engine (Python) — DAG orchestration, LLM providers, SQLite storage
│   ├── pyproject.toml
│   ├── pixl/                   # ~220 modules
│   └── tests/
├── cli/                        # pixl-cli (Python) — Click-based `pixl` binary
│   ├── pyproject.toml          # bundles crew via force-include
│   ├── pixl_cli/
│   │   ├── main.py             # Click group + setup command
│   │   ├── crew.py             # get_crew_root() resolver
│   │   ├── sandbox_client.py   # HTTP client for sandbox API (JWT, SSE, token refresh)
│   │   └── commands/           # artifact, config, cost, events, knowledge, project, sandbox, session, setup, state, template, workflow
│   └── tests/
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

## Agents

| Agent                | Role                                        |
| -------------------- | ------------------------------------------- |
| `orchestrator`       | Multi-agent coordination                    |
| `architect`          | System design, DDD                          |
| `product-owner`      | Task planning, sprints                      |
| `tech-lead`          | Code review, quality gates                  |
| `frontend-engineer`  | React/Next.js, shadcn/ui, design extraction |
| `backend-engineer`   | TypeScript backend, Fastify/Prisma          |
| `fullstack-engineer` | End-to-end across API boundary              |
| `qa-engineer`        | Testing, browser verification, review loops |
| `devops-engineer`    | Docker, CI/CD, deployment                   |
| `security-engineer`  | OWASP audits, RBAC, vulnerability analysis  |
| `explorer`           | Fast codebase exploration (haiku)           |
| `onboarding-agent`   | Client project onboarding (haiku)           |
| `build-error-resolver` | Surgical build/type error fixes (sonnet)  |
| `doc-updater`        | Keep docs in sync with code (haiku)         |

## Skills

**Frontend**: `/website`, `/design-extraction`, `/shadcn-ui`, `/svg-icon-creation`, `/i18n-setup`
**Website mods**: `/website-theme`, `/website-layout`
**Backend**: `/ddd-pattern`, `/fastapi-service`, `/pydantic-api-endpoint`
**Quality**: `/self-review-fix-loop`, `/code-reduction`, `/agent-browser`, `/react-doctor`, `/seo-audit`, `/cto-review`, `/cartographer`, `/test-runner`, `/test-writer`, `/benchmark`, `/schema-audit`, `/error-catalog`, `/api-audit`, `/dependency-review`, `/eval-harness`, `/security-scan`, `/spec-review`, `/code-review`
**Utilities**: `/file-parser`
**Marketing**: `/content-marketing`
**Video**: `/intro-video-brief` (create or enhance Remotion product intro videos)
**DevOps**: `/docker-cloudrun`, `/pm2`, `/makefile`, `/docker-prisma-setup`
**Planning**: `/prd-analysis`, `/task-plan`, `/content-pipeline`, `/sprint-planning`, `/task-persist`, `/migration-plan`, `/prd-pipeline`
**Workflow**: `/pr-creation`, `/claude-md`, `/skill-factory`, `/multi-agent-pipeline`, `/ralph-loop-crew`, `/context-packet-template`, `/crew-init`, `/studio-guide`, `/session-wrap`, `/client-project-setup`, `/strategic-compact`, `/continuous-learning`, `/batch`, `/changelog`
**Swift**: `/swift-patterns`
**Project types**: `/website-project`, `/saas-microservice`, `/fullstack-app`, `/admin-dashboard`, `/blog`, `/fastapi-api`
**Plugin dev**: `/agent-development`, `/command-development`, `/hook-development`, `/plugin-settings`, `/plugin-structure`, `/skill-factory`
**Database/Payments**: `/supabase-postgres-best-practices`, `/stripe-best-practices`
**Intelligence**: `/intel`, `/strategic-intel`, `/vision-advisory`

## Hooks & Memory

When the CLI is installed, hooks use `.pixl/pixl.db` (SQLite) as primary storage. When the CLI is absent, hooks fall back to `.claude/memory/` (file-based):

```
.claude/memory/
├── decisions.jsonl          # Append-only decision log
├── instincts.jsonl          # Learned patterns from /continuous-learning
├── costs.jsonl              # Per-session token costs
└── sessions/                # Per-session summaries (last 3 loaded on start)
```

## Development

| Command | What it does |
|---------|-------------|
| `make setup` | Full setup: install + register crew |
| `make install` | Install workspace packages |
| `make test` | Run all tests |
| `make test-engine` | Engine tests only |
| `make test-cli` | CLI tests only |
| `make test-cov` | Run tests with coverage report |
| `make check` | Lint + type check |
| `make typecheck` | Type check only (pyright) |
| `make format` | Auto-format |
| `make release` | Bump version, tag, push |

Engine deps are split: core deps always installed, API deps (`fastapi`, `redis`, `bcrypt`, `pyjwt`) optional via `[api]` extra.

## Companion Plugins

Installed by `pixl setup`:

| Plugin | Source | What it adds |
|--------|--------|-------------|
| `ralph-loop` | claude-plugins-official | Autonomous loop runtime |
| `commit-commands` | claude-plugins-official | `/amend`, `/fixup`, `/squash` |
| `playground` | claude-plugins-official | Interactive HTML playgrounds |
| `typescript-lsp` | claude-plugins-official | Go-to-definition, find-references for TS |
| `pyright-lsp` | claude-plugins-official | Type-aware Python code intelligence |
| `swift-lsp` | claude-plugins-official | Swift/SwiftUI code intelligence |
| `supply-chain-risk-auditor` | trailofbits | Dependency risk scoring |
| `variant-analysis` | trailofbits | Find similar vulnerabilities |
| `property-based-testing` | trailofbits | QuickCheck-style property tests |
| `static-analysis` | trailofbits | Semgrep + CodeQL orchestration |
| `semgrep-rule-creator` | trailofbits | Test-driven Semgrep rule authoring |

## Studio Stacks

| Stack | Use case | Skill |
|-------|----------|-------|
| `nextjs` | Websites, landing pages | `/website` |
| `saas` | Backend microservices (DDD, RBAC, audit) | `/saas-microservice` |

## Rules (`.claude/rules/`)

| Rule file | Scope |
|-----------|-------|
| `coding-style.md` | Immutability, naming, file size, error handling |
| `testing.md` | TDD workflow, 80% coverage, test types |
| `security.md` | Input validation, auth, secrets, OWASP |
| `git-workflow.md` | Conventional commits, PR hygiene, branch naming |
| `patterns.md` | Search-first, read-before-write, grep-before-edit |
| `workflow.md` | Background tasks, parallel execution, frequent commits |
| `permissions.md` | Permission wildcards — scoped over blanket |
| `context-management.md` | Context budgets, compaction, subagent delegation |
| `performance.md` | Measure before optimizing, DB, frontend, API patterns |

## Operational Rules

- **Explore → Plan → Implement → Commit** — plan mode for multi-file changes
- **Skills over ad-hoc prompts** — if a skill exists, use it
- **Minimal changes** — only what's requested
- **Frequent commits** — commit after each logical unit
- **Parallel execution** — launch independent agents/tools concurrently
- **CLI-first** — crew hooks and agents use pixl CLI for persistence when available

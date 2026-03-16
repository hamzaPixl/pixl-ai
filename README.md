# pixl

AI dev platform — orchestration engine + Claude Code crew plugin.

**14 agents · 70 skills · 11 workflows · 1 MCP server**

## What is pixl?

Three components, one install:

1. **Engine** — DAG-based workflow orchestration, multi-provider LLMs (Anthropic, OpenAI, Gemini), SQLite storage with FTS5, AST-indexed knowledge search
2. **CLI** — `pixl` binary for projects, workflows, sessions, artifacts, knowledge, and crew setup
3. **Crew** — Claude Code plugin with 14 specialized agents, 70 skills, event hooks, and studio templates

```
User → pixl CLI → Engine (DAG, LLM, Storage) → Claude Agent SDK
                → Crew Plugin (Agents, Skills, Hooks) → Claude Code
```

## Quick Start

### Install from PyPI

```bash
uv tool install pixl        # installs pixl binary + bundled crew
pixl setup                   # registers crew with Claude Code, installs companion plugins
```

Or with pipx:

```bash
pipx install pixl
pixl setup
```

### From Source

```bash
git clone https://github.com/hamzaPixl/pixl-ai.git && cd pixl
make setup                   # uv sync + pixl setup
```

## CLI Reference

```
pixl [--json] [--project PATH] COMMAND
```

| Command | Description |
|---------|-------------|
| `pixl project init` | Initialize a `.pixl/` project directory |
| `pixl workflow run` | Execute a workflow template |
| `pixl session list` | List workflow sessions |
| `pixl artifact list` | List build artifacts |
| `pixl knowledge build` | Build AST-indexed knowledge base |
| `pixl knowledge search` | Search knowledge base |
| `pixl state get` | Get project state |
| `pixl events list` | List execution events |
| `pixl config get` | Get project configuration |
| `pixl setup` | Register crew plugin with Claude Code |

## Agents

The crew plugin provides 14 specialized agents that Claude Code can delegate to:

| Agent | Role |
|-------|------|
| `orchestrator` | Multi-agent coordination for complex, multi-phase projects |
| `architect` | System design, DDD bounded contexts, technology selection |
| `product-owner` | Task planning, sprint breakdown, acceptance criteria |
| `tech-lead` | Code review, quality gates, standards enforcement |
| `frontend-engineer` | React/Next.js, shadcn/ui, design extraction, i18n |
| `backend-engineer` | TypeScript (Fastify/Prisma) or Python (FastAPI/Pydantic) |
| `fullstack-engineer` | End-to-end features crossing the API boundary |
| `qa-engineer` | Testing, browser verification, review-fix loops |
| `devops-engineer` | Docker, CI/CD, Cloud Run, PM2, Makefiles |
| `security-engineer` | OWASP audits, RBAC review, vulnerability analysis |
| `explorer` | Fast codebase exploration and research |
| `onboarding-agent` | Client project scanning and CLAUDE.md generation |
| `build-error-resolver` | Surgical build/type error fixes |
| `doc-updater` | Keep documentation in sync with code |

## Skills

70 skills organized by domain:

**Frontend** `/website` · `/design-extraction` · `/shadcn-ui` · `/svg-icon-creation` · `/i18n-setup` · `/website-theme` · `/website-layout` · `/website-redesign`

**Backend** `/ddd-pattern` · `/fastapi-service` · `/pydantic-api-endpoint`

**Quality** `/self-review-fix-loop` · `/code-reduction` · `/react-doctor` · `/seo-audit` · `/cto-review` · `/test-runner` · `/test-writer` · `/benchmark` · `/schema-audit` · `/error-catalog` · `/api-audit` · `/dependency-review` · `/security-scan` · `/code-review`

**Planning** `/task-plan` · `/sprint-planning` · `/content-pipeline` · `/task-persist` · `/migration-plan`

**DevOps** `/docker-cloudrun` · `/pm2` · `/makefile` · `/docker-prisma-setup`

**Workflow** `/pr-creation` · `/claude-md` · `/skill-factory` · `/batch` · `/session-retrospective` · `/continuous-learning` · `/crew-init`

**Project Scaffolding** `/website-project` · `/saas-microservice` · `/fullstack-app` · `/admin-dashboard` · `/blog` · `/fastapi-api`

**Intelligence** `/intel` · `/strategic-intel`

## Studio Stacks

Pre-built project templates for scaffolding client projects:

| Stack | Use Case | Skill |
|-------|----------|-------|
| **Next.js** | Websites, landing pages — 10 pages, i18n, blog, Stripe, Supabase, SEO | `/website` |
| **SaaS** | Backend microservices — 17 foundation packages: identity, tenancy, RBAC, audit, outbox, DDD | `/saas-microservice` |

## Hooks & Memory

Event hooks automate quality checks, context management, and session persistence:

- **SessionStart** — loads last 3 session summaries + recent decisions
- **PreCompact** — saves session state before context compaction
- **Stop** — captures git diff stats, modified files, task state
- **Cost tracker** — logs per-session token usage and costs

Storage uses `.pixl/pixl.db` (SQLite) via the CLI, with `.claude/memory/` (flat files) as fallback.

## Companion Plugins

Installed automatically by `pixl setup`:

| Plugin | Source | Purpose |
|--------|--------|---------|
| `ralph-loop` | claude-plugins-official | Autonomous loop runtime |
| `commit-commands` | claude-plugins-official | `/amend`, `/fixup`, `/squash` |
| `playground` | claude-plugins-official | Interactive HTML playgrounds |
| `typescript-lsp` | claude-plugins-official | TS go-to-definition, find-references |
| `pyright-lsp` | claude-plugins-official | Python type-aware code intelligence |
| `swift-lsp` | claude-plugins-official | Swift/SwiftUI code intelligence |
| `supply-chain-risk-auditor` | trailofbits | Dependency risk scoring |
| `variant-analysis` | trailofbits | Find similar vulnerabilities |
| `property-based-testing` | trailofbits | QuickCheck-style property tests |
| `static-analysis` | trailofbits | Semgrep + CodeQL orchestration |
| `semgrep-rule-creator` | trailofbits | Test-driven Semgrep rule authoring |

Skip categories with flags: `pixl setup --skip-lsp --skip-security --skip-plugins`

## MCP Servers

Bundled in `.mcp.json`:

| Server | What it provides |
|--------|-----------------|
| `sentry` | Production errors, stack traces, releases, Seer AI analysis |

## Engine Architecture

### Execution Pipeline

```
WorkflowTemplate → WorkflowSession
    → GraphExecutor (DAG traversal with ExecutorCursor)
        → ChainRunnerManager (parallel/sequential multi-node execution)
            → TaskExecutor (prompt → query → validation → baton patch)
                → ProviderRegistry (Anthropic, OpenAI, Gemini)
```

### Storage

SQLite with WAL mode and FTS5 full-text search. Protocol-based stores:

`BacklogStore` · `SessionStore` · `ArtifactStore` · `EventStore` · `KnowledgeStore` · `ConfigStore` · `WorkflowStore`

### Recovery

Error classification → contract repair → patch & test → replan.

## Development

```bash
make setup          # Full setup: install + register crew
make test           # Run all tests
make test-engine    # Engine tests only
make test-cli       # CLI tests only
make check          # Lint check
make format         # Auto-format
make release        # Bump patch version, tag, push
```

### Project Layout

```
pixl/
├── packages/engine/    # pixl-engine — Python orchestration engine
├── packages/cli/       # pixl-cli — Click CLI (bundles crew in wheel)
├── packages/crew/      # pixl-crew — Claude Code plugin
└── scripts/            # Release tooling
```

The uv workspace manages `engine` and `cli`. The `crew` package is plain files (not Python) — bundled into the CLI wheel via hatch `force-include`.

## License

MIT

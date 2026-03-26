# pixl

AI dev platform — orchestration engine + Claude Code crew plugin.

**14 agents · 75 skills · 11 workflows · sandboxed execution**

## What is pixl?

Four components, one install:

1. **Engine** — DAG-based workflow orchestration, multi-provider LLMs (Anthropic, OpenAI, Gemini), SQLite storage (schema v37, 40+ tables), FTS5 search, EventBus, agent registry
2. **CLI** — `pixl` binary for projects, workflows, sessions, artifacts, knowledge, sandboxes, cost analytics, and crew setup
3. **Crew** — Claude Code plugin with 14 specialized agents, 75 skills, event hooks, and studio templates
4. **Sandbox** — Cloudflare Workers containers for isolated AI execution with full pixl stack

```
User → pixl CLI → Engine (DAG, LLM, Storage, EventBus) → Claude Agent SDK
                → Crew Plugin (Agents, Skills, Hooks) → Claude Code
                → Sandbox (Cloudflare Workers) → Isolated containers
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
| `pixl workflow run` | Execute a workflow template (`--yes` to auto-approve gates) |
| `pixl session list` | List workflow sessions |
| `pixl artifact list` | List build artifacts |
| `pixl knowledge build` | Build AST-indexed knowledge base |
| `pixl knowledge search` | Search knowledge base |
| `pixl state show` | Show entity state and transitions |
| `pixl events list` | List execution events |
| `pixl config get` | Get project configuration |
| `pixl cost summary` | Cost analytics (total, by-model, by-session) |
| `pixl template list` | Manage DB-backed workflow templates |
| `pixl sandbox create` | Create sandbox project (`--fork-from` for session continuity) |
| `pixl sandbox workflow` | Run workflow in sandbox (`--stream` for SSE) |
| `pixl sandbox sync` | Sync sandbox data to local DB |
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

75 skills organized by domain:

**Frontend** `/website` · `/design-extraction` · `/shadcn-ui` · `/svg-icon-creation` · `/i18n-setup` · `/website-theme` · `/website-layout`

**Backend** `/ddd-pattern` · `/fastapi-service` · `/pydantic-api-endpoint`

**Quality** `/self-review-fix-loop` · `/code-reduction` · `/react-doctor` · `/seo-audit` · `/cto-review` · `/test-runner` · `/test-writer` · `/benchmark` · `/schema-audit` · `/error-catalog` · `/api-audit` · `/dependency-review` · `/security-scan` · `/code-review` · `/runbook`

**Planning** `/task-plan` · `/sprint-planning` · `/content-pipeline` · `/task-persist` · `/migration-plan` · `/prd-analysis` · `/prd-pipeline`

**DevOps** `/docker-cloudrun` · `/pm2` · `/makefile` · `/docker-prisma-setup`

**Workflow** `/pr-creation` · `/claude-md` · `/skill-factory` · `/batch` · `/session-wrap` · `/continuous-learning` · `/crew-init` · `/changelog` · `/ship-milestone`

**Project Scaffolding** `/website-project` · `/saas-microservice` · `/fullstack-app` · `/admin-dashboard` · `/blog` · `/fastapi-api`

**Intelligence** `/intel` · `/strategic-intel` · `/vision-advisory`

## Studio Stacks

Pre-built project templates for scaffolding client projects:

| Stack | Use Case | Skill |
|-------|----------|-------|
| **Next.js** | Websites, landing pages — 10 pages, i18n, blog, Stripe, Supabase, SEO | `/website` |
| **SaaS** | Backend microservices — 18 foundation packages: identity, tenancy, RBAC, audit, outbox, DDD | `/saas-microservice` |

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

SQLite with WAL mode, FTS5 full-text search, schema v37 (40+ tables). Protocol-based stores:

`BacklogStore` · `SessionStore` · `ArtifactStore` · `EventStore` · `KnowledgeStore` · `ConfigStore` · `WorkflowStore` · `CostEventDB` · `WorkflowTemplateDB` · `SandboxDB`

### Agent SDK Integration

- **AgentRegistry** — parses crew agent markdown into SDK `AgentDefinition` with model/tools per agent
- **Plugin loading** — crew plugin loaded programmatically via `plugins` param
- **Hook bridge** — crew shell hooks bridged to SDK callbacks with profile filtering
- **EventBus** — in-process pub/sub for real-time event distribution

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
├── packages/sandbox/   # pixl-sandbox — Cloudflare Workers sandbox runtime
└── scripts/            # Release tooling
```

The uv workspace manages `engine` and `cli`. The `crew` package is plain files (not Python) — bundled into the CLI wheel via hatch `force-include`.

## License

MIT

<div align="center">

<br>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://img.shields.io/badge/pixl--crew-v7.0.0-white?style=for-the-badge&labelColor=000">
  <img alt="pixl-crew" src="https://img.shields.io/badge/pixl--crew-v7.0.0-black?style=for-the-badge&labelColor=fff">
</picture>

### Your AI development team as a Claude Code plugin.

14 agents &middot; 70 skills &middot; 1 MCP server &middot; 11 companion plugins &middot; 2 studio stacks

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude_Code-plugin-blueviolet)](https://claude.ai/code)

<br>

[Quick Start](#quick-start) &middot; [Agents](#agents) &middot; [Skills](#skills) &middot; [Companion Plugins](#companion-plugins) &middot; [Studio Stacks](#studio-stacks) &middot; [Hooks & Memory](#hooks--memory) &middot; [Routing](#project-routing)

</div>

---

## What is pixl-crew?

**pixl-crew** turns Claude Code into a full AI development team. Instead of one assistant, it delegates to **14 specialized agents** — an architect designs, a backend engineer builds APIs, a frontend engineer creates UI, and a QA engineer tests. It ships with **70 reusable skills**, **production-ready scaffolding** for Next.js and SaaS backends, and **automated hooks** that enforce quality and persist context across sessions.

---

## Quick Start

```bash
uv tool install pixl && pixl setup   # recommended
# or from source:
git clone https://github.com/hamzaPixl/pixl-ai.git && cd pixl-ai
make setup
```

```bash
make setup SKIP_PLUGINS=1    # skip companion plugin sync
make setup SKIP_LSP=1        # skip LSP language servers
make setup SKIP_SECURITY=1   # skip Trail of Bits security plugins
make scaffold STACK=nextjs   # interactive project scaffold
make release                 # bump patch, tag, push
make release BUMP=minor      # bump minor version
make check                   # show installed plugins
```

After setup, open Claude Code in any project — agents and skills are immediately available.

---

## Agents

| Agent | Model | Role |
| :--- | :--- | :--- |
| **orchestrator** | opus | Multi-phase project coordination |
| **architect** | opus | System design, DDD, scalability (read-only) |
| **tech-lead** | opus | Code review, quality gates |
| **security-engineer** | opus | OWASP audits, RBAC, CVEs (read-only) |
| **frontend-engineer** | inherit | React/Next.js, shadcn/ui, design extraction |
| **backend-engineer** | inherit | Fastify/Prisma, DDD entities, FastAPI |
| **fullstack-engineer** | inherit | End-to-end across API boundary |
| **product-owner** | sonnet | Task planning, sprint breakdown |
| **qa-engineer** | sonnet | Testing, browser verification, review loops |
| **devops-engineer** | sonnet | Docker, CI/CD, Cloud Run |
| **explorer** | haiku | Fast codebase search (cost-efficient) |
| **onboarding-agent** | haiku | Client project onboarding (read-only) |
| **build-error-resolver** | sonnet | Surgical build/type error fixes |
| **doc-updater** | haiku | Keep docs in sync with code |

> **Model tiers**: Opus for architecture and review decisions. Sonnet for structured, repetitive work. Haiku for fast read-only exploration. Inherit uses the parent context's model.

---

## Skills

70 slash commands grouped by what you're trying to do.

| Category | Skills | What they do |
| :--- | :--- | :--- |
| **Build a website** | `/website`, `/website-project`, `/design-extraction`, `/shadcn-ui`, `/svg-icon-creation`, `/i18n-setup` | Full Next.js site pipeline, Figma/URL extraction, components, icons, i18n |
| **Modify a website** | `/website-theme`, `/website-layout` | Change colors/fonts/shadows or restructure sections/grids/layout |
| **Build backend** | `/saas-microservice`, `/ddd-pattern`, `/fastapi-service`, `/fastapi-api`, `/pydantic-api-endpoint`, `/docker-prisma-setup` | SaaS scaffolding, DDD patterns, FastAPI services, CRUD endpoints |
| **Project templates** | `/website-project`, `/fullstack-app`, `/admin-dashboard`, `/blog` | Multi-agent pipelines for common project types |
| **Quality & review** | `/self-review-fix-loop`, `/code-reduction`, `/react-doctor`, `/cto-review`, `/spec-review`, `/agent-browser`, `/code-review` | Review cycles, dead code removal, CTO-level critique, PR review, spec drift |
| **Testing** | `/test-runner`, `/test-writer`, `/eval-harness`, `/benchmark` | Run tests, generate test suites (TDD red phase), evals, benchmarks |
| **Audits** | `/schema-audit`, `/api-audit`, `/error-catalog`, `/dependency-review`, `/security-scan`, `/seo-audit` | DB schemas, API endpoints, errors, deps/CVEs, OWASP, SEO |
| **Planning** | `/task-plan`, `/sprint-planning`, `/migration-plan`, `/content-pipeline`, `/content-marketing`, `/task-persist` | Task decomposition, sprints, migrations, content strategy |
| **DevOps** | `/docker-cloudrun`, `/pm2`, `/makefile` | Containerize, deploy, process management |
| **Workflow** | `/pr-creation`, `/claude-md`, `/skill-factory`, `/client-project-setup`, `/crew-init`, `/strategic-compact`, `/continuous-learning`, `/batch` | PR workflows, project setup, context management, parallel execution, learning |
| **Intelligence** | `/intel`, `/strategic-intel`, `/cartographer` | AST code search, business intelligence, PR decomposition |
| **Swift** | `/swift-patterns` | SwiftUI, Swift 6.2 concurrency, actors, protocol DI |

<details>
<summary><strong>Plugin development</strong> (6 skills)</summary>

`/agent-development`, `/command-development`, `/hook-development`, `/plugin-settings`, `/plugin-structure`, `/skill-factory`

</details>

<details>
<summary><strong>Database & payments</strong> (2 skills)</summary>

`/supabase-postgres-best-practices`, `/stripe-best-practices`

</details>

<details>
<summary><strong>Utilities</strong> (6 skills)</summary>

`/file-parser`, `/multi-agent-pipeline`, `/ralph-loop-crew`, `/context-packet-template`, `/studio-guide`, `/session-export`, `/session-retrospective`

</details>

---

## Companion Plugins

Installed by `make setup` alongside pixl-crew.

### MCP Servers

| Server | Transport | What it provides |
| :--- | :--- | :--- |
| **Sentry** | HTTP | Production errors, stack traces, releases, Seer AI analysis |

OAuth on first use. Optional: [Semgrep](https://semgrep.dev/) for AST-aware static analysis.

### LSP (Language Server Protocol)

| Plugin | Language | Capabilities |
| :--- | :--- | :--- |
| `typescript-lsp` | TypeScript/JS | Go-to-definition, find-references, type info |
| `pyright-lsp` | Python | Type checking, completions, symbol search |
| `swift-lsp` | Swift/SwiftUI | SourceKit-LSP integration |

### Trail of Bits Security

| Plugin | What it does |
| :--- | :--- |
| `supply-chain-risk-auditor` | Dependency risk scoring (maintainers, CVEs, staleness) |
| `variant-analysis` | Find similar vulnerabilities after discovering one |
| `property-based-testing` | QuickCheck-style tests (Hypothesis, fast-check) |
| `static-analysis` | Semgrep + CodeQL orchestration with SARIF parsing |
| `semgrep-rule-creator` | Test-driven Semgrep rule authoring |

### Utilities

| Plugin | What it adds |
| :--- | :--- |
| `ralph-loop` | Autonomous loop runtime for `/ralph-loop-crew` |
| `commit-commands` | `/amend`, `/fixup`, `/squash` commit manipulation |
| `playground` | Interactive HTML playgrounds for design exploration |

### Optional: Prompt Injection Defense

[Lasso claude-hooks](https://github.com/lasso-security/claude-hooks) — PostToolUse scanner for prompt injection in tool outputs.

---

## Studio Stacks

Two production-ready template stacks, scaffolded via `make scaffold`.

### Next.js Stack (`studio/stacks/nextjs/`)

75+ templates for Next.js websites with App Router, shadcn/ui, Tailwind, SEO, i18n, MDX blog, Stripe, and Supabase auth. **12 design archetypes** drive unique visual output: Minimal, Bold, Playful, Corporate, Luxury, Organic, Brutalist, Editorial, Neubrutalism, Glassmorphism, Aurora, Cyberpunk.

### SaaS Stack (`studio/stacks/saas/`)

Production-grade TypeScript microservice infrastructure with DDD, multi-tenancy, and transactional outbox.

<details>
<summary><strong>18 foundation packages</strong></summary>

| Package | Purpose | Package | Purpose |
| :--- | :--- | :--- | :--- |
| `contracts` | Zod schemas, branded types | `outbox` | Transactional outbox pattern |
| `config` | Configuration management | `events` | Domain event bus |
| `logger` | Structured logging | `jobs` | Background job processing |
| `domain` | Entities, aggregates, VOs | `media` | File upload + CDN |
| `identity` | JWT + API key auth | `cache` | Cache contracts + adapters |
| `tenancy` | Multi-tenant isolation | `observability` | Tracing + metrics |
| `db` | Prisma + tenant-scoped repos | `realtime` | WebSocket/SSE |
| `rbac` | Role-based access control | `notifications` | Email/SMS/push |
| `audit` | Audit trail logging | `api-factory` | Route scaffolding + guards |

</details>

---

## Hooks & Memory

### Hook Profiles

| Profile | What runs |
| :--- | :--- |
| **minimal** | Critical only: destructive command blocking |
| **standard** | Critical + quality: formatting, TDD, skill enforcement |
| **strict** | All: TypeScript type checking, console.log audit |

```bash
PIXL_HOOK_PROFILE=minimal claude       # fast exploratory session
PIXL_DISABLED_HOOKS=typecheck claude    # disable specific hooks
```

### Cross-Session Memory

```
.claude/memory/
├── decisions.jsonl          # Architectural decisions (auto-injected on start)
├── instincts.jsonl          # Learned patterns from /continuous-learning
├── costs.jsonl              # Per-session token costs
└── sessions/                # Session summaries (last 3 loaded on start)
```

SessionStart loads previous context. Stop hook saves summaries, decisions, and task state. Memory files are gitignored.

### pixl CLI Integration

When the pixl CLI is installed, agents use AST-indexed code search via `/intel`. Falls back to Glob/Grep when unavailable.

---

## Project Routing

| You want to... | Use |
| :--- | :--- |
| Build a new website | `/website` or `/website-project` |
| Build a SaaS backend | Orchestrator + `/saas-microservice` |
| Build a fullstack app | Orchestrator + `/fullstack-app` |
| Add an endpoint to existing service | Backend engineer (follows existing patterns) |
| Refactor to DDD | `/ddd-pattern` |
| Review code quality | `/self-review-fix-loop` or `/cto-review` |
| Review a PR before merge | `/code-review` |
| Run same change across many files | `/batch` |
| Compare implementation against spec | `/spec-review` |
| Generate tests for existing code | `/test-writer` |
| Plan a sprint | `/task-plan` + `/sprint-planning` |
| Audit a database schema | `/schema-audit` |
| Review dependencies for CVEs | `/dependency-review` |
| Onboard a new client project | `/client-project-setup` |

> See `skills/ROUTING.md` for the full decision tree.

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Make changes following the rules in `.claude/rules/`
4. Run `make check` to verify
5. Submit a pull request

Add agents in `agents/`, skills in `skills/`, templates in `studio/stacks/`. Use `/skill-factory` to auto-generate skills.

---

## License

[MIT](LICENSE) &copy; [Hamza Mounir](https://github.com/hamzaPixl)

---

<div align="center">

Built with [Claude Code](https://claude.ai/code) &middot; Powered by [Anthropic](https://anthropic.com)

</div>

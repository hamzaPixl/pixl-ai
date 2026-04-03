# pixl-crew

Claude Code plugin — AI dev crew with agents, skills, and studio templates.

## Structure

```
.claude-plugin/plugin.json   # manifest
Makefile                     # setup, release, check
agents/                      # 14 agents
skills/                      # 75 skills (see skills/ROUTING.md for decision tree)
hooks/hooks.json             # event hooks (routed via run-with-flags.sh orchestrator)
references/                  # shared domain knowledge (see references/INDEX.md, AGENT-REGISTRY.md)
contexts/                    # dynamic context overlays (dev, research, review)
studio/stacks/{nextjs,saas}  # scaffolding templates
examples/                    # CLAUDE.md templates for common project types
schemas/                     # JSON schemas for hooks.json and plugin.json
scripts/                     # setup, release, scaffold, download-assets, visual-diff
```

## Setup

```bash
make setup                   # install/update plugins + LSP + security
make setup SKIP_PLUGINS=1    # skip plugin sync
make setup SKIP_LSP=1        # skip LSP plugins
make setup SKIP_SECURITY=1   # skip Trail of Bits security plugins
make release                 # bump patch, tag, push, refresh
make release BUMP=minor      # bump minor
make check                   # show status
make scaffold STACK=nextjs   # interactive project scaffold
```

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
**Quality**: `/self-review-fix-loop`, `/code-reduction`, `/agent-browser`, `/react-doctor`, `/seo-audit`, `/cto-review`, `/cartographer`, `/test-runner`, `/test-writer`, `/benchmark`, `/schema-audit`, `/error-catalog`, `/api-audit`, `/dependency-review`, `/eval-harness`, `/security-scan`, `/spec-review`, `/code-review`, `/runbook`
**Utilities**: `/file-parser`
**Marketing**: `/content-marketing`
**Video**: `/intro-video-brief` (create or enhance Remotion product intro videos)
**DevOps**: `/docker-cloudrun`, `/pm2`, `/makefile`, `/docker-prisma-setup`
**Planning**: `/prd-analysis`, `/task-plan`, `/content-pipeline`, `/sprint-planning`, `/task-persist`, `/migration-plan`, `/prd-pipeline`
**Workflow**: `/pr-creation`, `/claude-md`, `/skill-factory`, `/multi-agent-pipeline`, `/ralph-loop-crew`, `/context-packet-template`, `/crew-init`, `/studio-guide`, `/session-wrap`, `/client-project-setup`, `/strategic-compact`, `/continuous-learning`, `/batch`, `/changelog`, `/ship-milestone`
**Swift**: `/swift-patterns`
**Scripts**: `download-assets.sh` (asset downloading), `visual-diff.mjs` (pixelmatch visual regression)
**Project types**: `/website-project`, `/saas-microservice`, `/fullstack-app`, `/admin-dashboard`, `/blog`, `/fastapi-api`
**Plugin dev**: `/agent-development`, `/command-development`, `/hook-development`, `/plugin-settings`, `/plugin-structure`, `/skill-factory`
**Database/Payments**: `/supabase-postgres-best-practices`, `/stripe-best-practices`
**Intelligence**: `/intel`, `/strategic-intel`, `/vision-advisory`

## Rules (`.claude/rules/`)

| Rule file             | Scope                                                     |
| --------------------- | --------------------------------------------------------- |
| `agent-authoring.md`  | Agent `.md` files — frontmatter, examples, structure      |
| `skill-authoring.md`  | Skill `SKILL.md` files — frontmatter, description quality |
| `studio-templates.md` | `.tmpl` files — token syntax, no hardcoded values         |
| `permissions.md`      | Permission wildcards — scoped over blanket                |
| `workflow.md`         | Background tasks, parallel execution, frequent commits    |
| `coding-style.md`     | Immutability, naming, file size, error handling           |
| `testing.md`          | TDD workflow, 80% coverage, test types                    |
| `security.md`         | Input validation, auth, secrets, OWASP                    |
| `git-workflow.md`     | Conventional commits, PR hygiene, branch naming           |
| `patterns.md`         | Search-first, read-before-write, grep-before-edit         |
| `typescript/*.md`     | TypeScript-specific coding style and testing rules        |
| `swift/*.md`          | Swift-specific coding style rules                         |
| `python/*.md`         | Python-specific coding style and testing rules            |
| `performance.md`      | Measure before optimizing, DB, frontend, API patterns     |

## Operational Rules

- **Explore → Plan → Implement → Commit** — plan mode for multi-file changes
- **Skills over ad-hoc prompts** — if a skill exists, use it
- **Minimal changes** — only what's requested
- **Frequent commits** — commit after each logical unit; don't accumulate large diffs
- **Background tasks** — run dev servers, builds, watchers with `run_in_background`
- **Parallel execution** — launch independent agents/tools concurrently in one message
- **Self-improvement** — if you discover a repeatable pattern, propose a skill via `/skill-factory`

## Project-Type Routing

See `skills/ROUTING.md` for the full decision tree. Quick reference:

| Building                             | Use                                                              |
| ------------------------------------ | ---------------------------------------------------------------- |
| New backend/API/service              | Orchestrator → `/saas-microservice` (uses `studio/stacks/saas/`) |
| New fullstack app                    | Orchestrator → `/fullstack-app`                                  |
| New website/landing page             | Frontend-engineer → `/website`                                   |
| DDD refactoring                      | `/ddd-pattern`                                                   |
| Adding endpoints to existing service | Backend-engineer (follow existing patterns)                      |

**Never build backend infrastructure from scratch** — the SaaS studio stack has 18+ foundation packages covering identity (JWT + API key), tenancy, RBAC, audit, outbox, media upload, locale resolution, cache, and more.

## Hook Profiles

Control hook behavior with `PIXL_HOOK_PROFILE`:

| Profile    | Hooks that run                                    |
| ---------- | ------------------------------------------------- |
| `minimal`  | Only critical: destructive command blocking        |
| `standard` | Critical + quality: formatting, TDD, skill checks |
| `strict`   | All: includes typecheck, console.log audit         |

```bash
PIXL_HOOK_PROFILE=minimal claude    # fast exploratory session
PIXL_DISABLED_HOOKS=typecheck,tdd-check claude  # disable specific hooks
```

**Note:** SDK sessions spawned by `pixl workflow run` automatically use `minimal` profile to reduce hook teardown noise.

## Dynamic Contexts

Load context overlays for different modes (from `contexts/` directory):

- `contexts/dev.md` — active development priorities
- `contexts/research.md` — read-only exploration mode
- `contexts/review.md` — code review checklist and focus

## Cross-Session Memory

```
.claude/memory/
├── decisions.jsonl          # Append-only decision log (auto-injected on SessionStart)
├── instincts.jsonl          # Learned patterns from /continuous-learning
├── costs.jsonl              # Per-session token costs (from cost-tracker hook)
└── sessions/                # Per-session summaries (last 3 loaded on start)
```

- **Stop hook** runs a shell script that captures git diff stats, modified files, and preserves task state
- **SessionStart hook** injects last 3 summaries + last 10 decisions
- **PreCompact hook** saves session state before context compaction
- **Cost tracker hook** logs per-session token usage and cost estimates
- See `references/orchestration/memory-protocol.md` for the full protocol

## pixl CLI Integration

When the pixl CLI is installed, agents use AST-indexed code search, artifacts, and events via `/intel` skill. All features degrade gracefully to Glob/Grep when the CLI is absent.

- **SessionStart hook** runs `pixl knowledge build --code` in background
- **Stop hook** rebuilds the index for changed files
- **Explorer agent** uses `pixl knowledge search` alongside Grep
- See `references/intel/pixl-cli-reference.md` for the full command reference

## Companion Plugins

Installed by `make setup` alongside pixl-crew:

| Plugin | Source | What it adds |
|--------|--------|-------------|
| `ralph-loop` | claude-plugins-official | Autonomous loop runtime for `/ralph-loop-crew` |
| `commit-commands` | claude-plugins-official | `/amend`, `/fixup`, `/squash` commit manipulation |
| `playground` | claude-plugins-official | Interactive HTML playgrounds for design exploration |
| `typescript-lsp` | claude-plugins-official | Go-to-definition, find-references, type info for TS |
| `pyright-lsp` | claude-plugins-official | Type-aware Python code intelligence |
| `swift-lsp` | claude-plugins-official | Swift/SwiftUI code intelligence |
| `supply-chain-risk-auditor` | trailofbits | Dependency risk scoring (maintainers, CVEs, staleness) |
| `variant-analysis` | trailofbits | Find similar vulnerabilities after discovering one |
| `property-based-testing` | trailofbits | QuickCheck-style property tests (Hypothesis, fast-check) |
| `static-analysis` | trailofbits | Semgrep + CodeQL orchestration with SARIF parsing |
| `semgrep-rule-creator` | trailofbits | Test-driven Semgrep rule authoring |
| `frontend-design` | claude-plugins-official | Anti-AI-slop aesthetics: bold typography, distinctive colors, motion |

### Optional Token Optimization

[RTK (Rust Token Killer)](https://github.com/rtk-ai/rtk) — compresses Bash tool outputs by 60-90% via PreToolUse hook rewrite. Reduces context pressure and cost. Built-in tools (Read, Grep, Glob) are unaffected — only Bash commands are compressed.

```bash
brew install rtk && rtk init -g --hook-only   # or: make setup (includes RTK)
```

### Optional Session Observability

[claude-devtools](https://github.com/matt1398/claude-devtools) — zero-config desktop app for Claude Code session analysis. Shows context fill/compaction visualization, token attribution per turn, subagent execution trees, and tool call patterns. Complements pixl console metrics (engine = workflow-level, devtools = session-level).

### Optional Security Hardening

[Lasso claude-hooks](https://github.com/lasso-security/claude-hooks) — prompt injection defense for tool outputs:

```bash
git clone https://github.com/lasso-security/claude-hooks /tmp/lasso-hooks
cd /tmp/lasso-hooks && ./install.sh /path/to/your/project
```

Detects: instruction override, role-playing jailbreaks, encoding obfuscation (base64, hex, homoglyphs), context manipulation, instruction smuggling in HTML/code comments. PostToolUse hook on Read, WebFetch, Bash, Grep, Task.

## Key Patterns

- **Agents**: `.md` + YAML frontmatter — `color` required, `<example>` blocks in description required for triggering
  - Read-only agents (`architect`, `security-engineer`, `explorer`) use `permissionMode: plan` + `disallowedTools: Write, Edit`
- **Skills**: `SKILL.md` + YAML frontmatter (name, description, allowed-tools, argument-hint)
  - Orchestration skills use `context: fork` (isolated context window)
  - Side-effect skills use `disable-model-invocation: true` (user-only invocation)
- **Templates**: `.tmpl` files with `{{TOKEN_NAME}}` replacement via `scripts/scaffold.sh`

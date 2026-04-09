# Changelog

## v11.3.0 — gstack-Inspired Crew Expansion

> 8 new skills, expanded code review (8 specialist reviewers), confidence scoring standard, and sprint workflow methodology — inspired by patterns from [gstack](https://github.com/garrytan/gstack).

### New Skills (8)

- **feat(crew)**: `/investigate` — Root cause debugging with enforced 4-phase methodology: reproduce → diagnose → hypothesize → fix. Prevents jumping to solutions; requires regression test on every fix
- **feat(crew)**: `/health` — Code quality dashboard wrapping project toolchain (types, lint, tests, dead code) into a composite 0-10 score with trend tracking via `--trend` and auto-fix via `--fix`
- **feat(crew)**: `/retro` — Engineering retrospective from git history: commit distribution, code churn hotspots, shipping velocity, per-contributor breakdown. Time-windowed (24h/7d/14d/30d/compare)
- **feat(crew)**: `/cross-review` — Multi-tier code review running Sonnet + Haiku independently on the same diff, producing a consensus table that flags agreements, single-model findings, and taste decisions
- **feat(crew)**: `/deploy-verify` — Post-merge release verification: waits for deploy, runs canary checks (page load, content, API health, SSL), supports `--revert` for auto-rollback on critical failure
- **feat(crew)**: `/checkpoint` — Save and restore full working context (branch, stash, task state, decisions, remaining work) for seamless task switching and session resumption
- **feat(crew)**: `/design-variants` — Generate N distinct visual design variants (minimal, bold, editorial, brutalist, organic, tech) as self-contained HTML files with a comparison board
- **feat(crew)**: `/guard` — Session-scoped file protection: declare protected paths (`/guard protect .env`) or restrict edits to a scope (`/guard scope src/api/`), enforced via guard file checks

### Enhanced Code Review

- **feat(crew)**: `/code-review` expanded from 3 to 8 specialist reviewer dimensions — adds Performance (D), API Contracts (E), Data Migration Safety (F), Maintainability (G), and Red Team/adversarial (H)
- **feat(crew)**: Quick mode (3 reviewers, default) vs Full mode (`--full`, 8 reviewers) for cost-appropriate review depth
- **feat(crew)**: AUTO-FIX / ASK classification on every finding — low-risk mechanical fixes (unused imports, missing types) vs judgment-required changes. `--auto-fix` flag applies AUTO-FIX findings directly
- **feat(crew)**: 5-tier confidence scoring aligned with new standard (90-100 near certain → 1-39 speculative)

### Standards & Methodology

- **feat(crew)**: Confidence Scoring Standard in `references/standards/code-review.md` — 5-tier scale with boosters (+10 consensus, +5 critical path) and penalties (-15 incomplete context), fix classification (AUTO-FIX vs ASK). Applies across `/code-review`, `/cto-review`, `/security-scan`, `/api-audit`, `/schema-audit`, `/dependency-review`
- **feat(crew)**: Sprint Workflow Reference in `references/methodology/sprint-workflow.md` — Think → Plan → Build → Review → Test → Ship → Reflect with pixl skill mappings per phase
- **feat(crew)**: Completeness Principle added to orchestrator and architect agents — prefer full implementations over stubs, finish what you start, avoid TODO-driven development
- **feat(crew)**: Cross-reference between `/cross-review` and `multi-model-arbitration.md` to distinguish proactive review from stuck-state arbitration

### Registry Updates

- **chore(crew)**: Skill count updated 75 → 84 across all CLAUDE.md files and structure trees
- **chore(crew)**: `skills/ROUTING.md` — 8 new routing entries, removed duplicate `/session-wrap` entry
- **chore(crew)**: `references/INDEX.md` — added `sprint-workflow.md` and `multi-model-arbitration.md` entries
- **chore(crew)**: `plugin.json` description updated to reflect 84 skills

## v11.2.3 — Codex Scaffold Root Fix

> Fix the remaining root causes behind hook failures in fresh non-git Codex projects.

### Codex
- **fix(codex)**: Generate `hooks.json` with project-local `.codex/hooks/...` paths instead of `git rev-parse --show-toplevel`
- **fix(codex)**: Inject the resolved crew root into generated `_env.sh` so hooks can load without importing `pixl_cli` from system `python3`
- **fix(codex)**: Add regression coverage for `_env.sh` template substitution during Codex scaffold generation

## v11.2.2 — Codex Hook Portability Fix

> Fix Codex scaffold hook portability on macOS and align fresh project wrappers with the current permission-check flow.

### Crew
- **fix(crew)**: Make `session-start.sh` work without GNU `timeout` by falling back to `gtimeout` or a plain background build
- **fix(codex)**: Update fresh project `PreToolUse` wrapper to call `permission-check.sh` instead of the legacy `block-destructive.sh`

### Verification
- **test(codex)**: Regenerated a fresh project scaffold and verified generated `SessionStart`, `UserPromptSubmit`, `PreToolUse`, and `Stop` wrappers all exit successfully

## v11.2.1 — Codex Agent TOML Fix

> Fix invalid `.codex/agents/*.toml` generation during project auto-init so new sessions on fresh projects no longer emit malformed agent role warnings.

### CLI
- **fix(cli)**: Escape Codex agent `description` values when generating TOML from crew agent markdown
- **fix(cli)**: Preserve quoted example prompts inside agent descriptions without breaking TOML parsing

### Tests
- **test(cli)**: Add regression coverage for quoted agent descriptions in generated Codex TOML files

## v11.2.0 — Harness Engineering Improvements

> Steering queue, task graph validation, and declarative permission tiers — closing the top 3 gaps from a Claude Code architecture audit.

### Engine — Mid-Task Steering Queue
- **feat(engine)**: `OrchestratorCore._steering_queue` — soft redirect at tool boundaries (vs binary interrupt)
- **feat(engine)**: `steer()` + `_pop_steering_instruction()` — queue instruction, drain at next boundary
- **feat(engine)**: `__STEER__` sentinel in `_process_streaming_message()` — interrupts current query, re-queries with REDIRECT prompt
- **feat(engine)**: `WorkflowRunnerManager.steer_session(session_id, instruction)` — external entry point

### Engine — Task Graph Validation
- **feat(engine)**: New `pixl.utils.task_graph` module — `graphlib.TopologicalSorter`-based
- **feat(engine)**: `validate_task_graph()` — detects cycles, orphan `blockedBy` refs, self-dependencies
- **feat(engine)**: `compute_execution_order()` — topologically sorted task IDs
- **feat(engine)**: `compute_critical_path()` — DP longest-path with size weights (S=1, M=3, L=8)

### Crew — YAML Permission Tiers
- **feat(crew)**: `config/permissions.yaml` — 22 deny + 5 allow + 4 ask_user rules
- **feat(crew)**: `permission-check.sh` replaces `block-destructive.sh` + `detect-secrets.sh`
- **feat(crew)**: Three-tier model: `always_deny` (exit 2), `always_allow` (exit 0), `ask_user` (profile-aware)
- **feat(crew)**: Per-rule `case_insensitive` flag, `tools` filter (Bash/Write/Edit/Read/Agent/Skill)
- **feat(crew)**: `hooks.json` updated — Bash and Write|Edit matchers use `permission-check.sh`
- **feat(crew)**: JSON Schema at `schemas/permissions.schema.json`

### Crew — Skill Integration
- **feat(crew)**: `/task-persist` validates dependency graph before save (graceful fallback)
- **feat(crew)**: `/task-plan` Step 4 computes algorithmic critical path (graceful fallback)

### Tests
- **test**: 29 new engine tests (steering queue + task graph) — 1856 total passing
- **test**: 9 new permission tier tests

### CTO Review Fixes
- **fix(crew)**: Wire `permission-check.sh` into `hooks.json` (was dead code)
- **fix(crew)**: Fix `ask_user` TTY detection — use `PIXL_HOOK_PROFILE` instead
- **fix(crew)**: Add missing `password`/`secret` assignment patterns
- **fix(crew)**: Fix shell injection — env vars instead of string interpolation
- **fix(crew)**: Fix `git reset --hard` pattern (remove trailing `$` anchor)
- **fix(crew)**: Narrow `.env` pattern, remove blanket `re.IGNORECASE`

## v11.1.0 — Harness Integrity Protocol

> Quality-over-completion enforcement for the harness workflow: no hacking, zero assumptions, consensus evaluation.

### Crew — Integrity Protocol
- **feat(crew)**: New `integrity-protocol.md` reference — 4-part protocol: no-hack rules (5 rules), zero-assumption debug methodology (5 steps), consensus validation, escalation format
- **feat(crew)**: Harness SKILL.md now requires integrity-protocol.md alongside anti-rationalization and grading rubric
- **feat(crew)**: Dual evaluator consensus — 2 parallel QA agents score independently, convergence check (delta ≤ 2), tiebreaker on divergence
- **feat(crew)**: Score gate with stagnation detection and escalation handling in fallback path

### Engine — Stagnation Detection
- **feat(engine)**: Score gate hook now tracks `score_history` across iterations and detects plateau (< 1 point total improvement over 2 consecutive iterations)
- **feat(engine)**: Generator escalation detection — if agent reports `stuck_issues` or `escalation` in baton, score gate triggers pause instead of blind looping
- **feat(engine)**: Stagnation hint injection — on plateau, generator receives "change approach or escalate" directive instead of the same critique

### Engine — Hack Detection Contract
- **feat(engine)**: New `detect_hacks` contract option — scans output files for shortcut patterns (!important, empty catch, @ts-ignore, .skip(), hardcoded UUIDs, eslint-disable, noqa)
- **feat(engine)**: 12 hack detection regex patterns in `contract_constants.py` alongside existing stub patterns
- **feat(engine)**: `detect_hacks: true` enabled on harness generate stage by default

### Engine — Generator Prompt Integrity
- **feat(engine)**: Generator prompt (`harness-generate.yaml`) now includes mandatory integrity rules: no hacking, evidence-based debugging, escalation after 2 failed attempts
- **feat(engine)**: Generator baton output includes `evidence_log` (mandatory for fix iterations), `stuck_issues`, and `escalation` fields
- **feat(engine)**: Evaluator prompt (`harness-evaluate.yaml`) audits generator evidence, tracks score trends, and flags fixes without proof as P0

## v11.0.0 — Codex Integration & Verification

> Major release: first-class Codex scaffolding, agents/skills support, and engine verification flow.

- **feat(codex)**: Add AGENTS.md + `.codex/` scaffolding (config, hooks, rules, agents) and `.agents/skills` symlinks
- **feat(cli)**: New `pixl codex setup` and `pixl codex verify` commands
- **feat(engine)**: New `codex-verify` workflow for lightweight Codex + Pixl engine validation
- **feat(engine)**: Loader now prefers `AGENTS.md` (Codex) before `CLAUDE.md`
- **feat(rules)**: Codex rules allowlist for common read-only and test commands
- **feat(docs)**: Updated README + USAGE with Codex setup, default provider notes, and verification steps
- **chore**: Added `scripts/verify-codex.sh` for automated verification

## v10.3.1 — Deduplication & Hook Hardening

- **docs**: Deduplicate root CLAUDE.md — agents/skills/plugins/studio/rules tables moved to crew reference. Added Environment section and Gotchas section
- **feat**: New package CLAUDE.md files for engine, api, and console — scoped documentation for each component
- **security**: Wire detect-secrets.sh into hooks.json as PreToolUse(Write|Edit) at critical level
- **chore**: Clean debug entries from .claude/settings.local.json
- **feat**: Enhanced crew-init template with pixl CLI section, cross-session memory, and hook profiles
- **feat**: New crew-context.md rule template for context management best practices
- **feat**: `pixl project init` now installs crew-context.md alongside existing rule files
- **chore**: Update .gitignore with Claude Code artifact entries

## v10.3.0 — RTK Token Optimization & Tool Awareness

- **feat(crew)**: RTK integration — 60-90% Bash output compression via PreToolUse hook
- **feat(crew)**: Python typecheck PostToolUse hook (pyright/ruff) alongside TypeScript typecheck
- **feat(crew)**: Tool-awareness rules: large file warnings, search truncation, LSP over Grep for refactoring
- **feat(engine)**: Metrics storage module for agent/workflow performance tracking
- **docs**: Setup script with optional RTK, LSP, and security plugin installation

## v10.2.0 — API + Console Full Integration

> Major release: complete web UI for pixl.

- **feat(api)**: 24 route modules, 144 endpoints — full REST API over pixl-engine
- **feat(api)**: JWT auth (HS256, 24h expiry) with bcrypt, WebSocket event stream, LRU connection pool
- **feat(api)**: CRUD factory generating 9 endpoints per entity, workspace system, API key management
- **feat(console)**: React SPA with TanStack Router (40+ pages), real-time WebSocket SSE, shadcn/ui
- **feat(console)**: Zustand stores (auth, project, UI), Recharts visualization, command palette
- **test**: 123 API tests covering foundation, DB, routes, auth, workspaces

## v10.1.0

- **docs**: Update project workflow guide, add PRD-to-code scenario
- **fix**: Handle str crew_path in `_build_crew_system_prompt`
- **feat**: Heartbeat, memory bridge, crew skill prompt, and doc sync

## v10.0.1 — SDK Output Migration

- **refactor**: Migrate from `pixl_output` envelope to SDK native structured output
- **docs**: Add project workflow guide with sandbox validation

## v10.0.0 — Centralized DB, Workflow Classifier, SDK Hook Fixes

> Major version bump: breaking changes in output format and hook configuration.

- **fix**: Suppress pricing warning for empty model string
- **fix**: Disable debug-to-stderr in SDK sessions — cleans up workflow output
- **fix**: Remove wildcard PostToolUse hooks causing 3x errors per tool call
- **chore**: Remove detect-secrets PreToolUse hook to reduce friction

## v9.1.0 — Architecture Gap Closure

> 15 of 17 architecture gaps closed. 2 deferred by design (P3).

### Agent SDK Integration
- **Agent Registry** (GAP-02): Parse crew agent markdown into SDK `AgentDefinition` objects. Auto-select agents with correct model/tools per workflow node.
- **Plugin Loading** (GAP-01): Programmatically load crew plugin via `plugins` param in SDK sessions. Resolves via `PIXL_CREW_ROOT` env → monorepo → bundled wheel.
- **Crew Hook Bridge** (GAP-03): Bridge 15+ crew shell hooks (block-destructive, detect-secrets, TDD check, quality-gate) to SDK `HookCallback` functions with profile-based filtering (minimal/standard/strict).
- **TodoWrite Bridge** (GAP-05): Capture SDK TodoWrite tool calls as `todo_update` events in engine EventDB for progress tracking.
- **Per-Agent Tool Restrictions** (GAP-06): Read-only agents (architect, explorer) get restricted tool sets from registry. Explicit `allowed_tools` overrides still work.

### Real-Time Events & Streaming
- **EventBus** (GAP-13): In-process pub/sub for real-time event distribution. Thread-safe, error-isolated subscribers.
- **NDJSON Streaming** (GAP-08): `pixl workflow run --json` streams events as newline-delimited JSON in real-time (not just final result).
- **EventDB Integration**: EventBus wired into EventDB — events published to subscribers after successful DB commit. Batch mode publishes after transaction.

### Storage & Schema
- **Schema v35-v37**: 3 migrations adding sandbox tables (`sandbox_projects`, `sandbox_operations`), provenance columns (`sandbox_origin_id` on events/sessions/artifacts), and workflow template storage.
- **Cost Aggregation** (GAP-17): `breakdown_by_model()`, `breakdown_by_adapter()`, `total_by_session()`, `summary()`, `total_cost_for_month()` queries on cost_events table.
- **Workflow Templates** (GAP-14): DB-backed templates with versioning, CRUD, and source tracking (db/filesystem/imported).
- **Sandbox Store** (GAP-10): Track sandbox projects and operations in local pixl.db with status lifecycle and operation audit logging.

### Execution
- **Graceful Interruption** (GAP-11): GraphExecutor checks interrupt signal between nodes, saves session as `paused` with checkpoint. In-progress nodes complete before pause.

### CLI
- **`pixl cost`**: summary, by-model, by-session subcommands for cost analytics.
- **`pixl template`**: list, get, create, update, delete subcommands for DB-backed workflow templates.
- **`pixl sandbox`**: 12 subcommands — create, list, status, workflow, cancel, events, sessions, export-session, import-session, git, exec, destroy, sync.
- **`--fork-from`** (GAP-09): Bootstrap new sandbox from existing session: `pixl sandbox create new --fork-from old:sess-123`.
- **SandboxClient**: HTTP client with JWT auth (HS256), scoped tokens, SSE streaming, auto-refresh.

### Sandbox Worker (packages/sandbox/)
- **pixl-sandbox**: Cloudflare Workers + Durable Objects sandbox runtime.
  - Hono REST API with 16 endpoints
  - JWT auth with scoped tokens: `read`, `write`, `admin` (GAP-16)
  - Rate limiting: 60 req/min per IP
  - Audit logging on POST/DELETE operations
  - SSE streaming for exec and workflow execution
  - Session export/import for cross-sandbox continuity
  - Docker container: Python 3.12 + uv + pixl-cli + Claude Code CLI

### Security (GAP-16)
- **Scoped JWT Tokens**: `read`/`write`/`admin` scope enforcement on all sandbox endpoints. Static API key fallback grants admin scope for backwards compatibility.
- **Token Auto-Refresh**: SandboxClient regenerates JWT within 5 minutes of expiry. Thread-safe with Lock.
- **Rate Limiting**: 60 requests/minute per IP on sandbox Worker.
- **Audit Logging**: POST/DELETE operations logged with timestamps.

### Testing
- **206 tests total** (110 engine + 96 CLI), all passing
- New test coverage: agent registry (23), crew bridge (39), todo bridge (7), EventBus integration (7), cost events (19), workflow templates (20), sandbox DB (16), sandbox client (44), sandbox CLI (25), JWT scope (16)

### Deferred (P3)
- **GAP-04** (Pydantic model_json_schema): Current JSON Schema approach works fine.
- **GAP-15** (PostgreSQL adapter): Not needed until multi-tenancy required. Protocol abstraction ready.
- **GAP-07** (TS SDK in Worker): Dropped — engine already wraps Claude SDK with full orchestration value.

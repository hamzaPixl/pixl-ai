# Changelog

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

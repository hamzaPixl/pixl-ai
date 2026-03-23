# Pixl Platform: Architecture Analysis

> Comprehensive analysis of the pixl platform across all layers, gap analysis against the Claude Agent SDK, and prioritized recommendations.
>
> Generated: 2026-03-23 | Engine schema: v35 | Crew: v9.0.2 | SDK: v0.1.37+

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current Architecture Map](#2-current-architecture-map)
3. [SDK Integration Analysis](#3-sdk-integration-analysis)
4. [Sandbox-Engine Integration Analysis](#4-sandbox-engine-integration-analysis)
5. [Architecture Gaps & Technical Debt](#5-architecture-gaps--technical-debt)
6. [Recommendations Matrix](#6-recommendations-matrix)
7. [SDK Feature Compatibility Checklist](#7-sdk-feature-compatibility-checklist)
8. [Critical Files Index](#8-critical-files-index)
9. [Future Work (Deferred)](#9-future-work-deferred)
10. [SDK Integration Solutions (Per Official Doc)](#10-sdk-integration-solutions-per-official-doc)

---

## 1. Executive Summary

### Vision

A **project management platform** where AI agent teams work on projects through orchestrated DAG workflows. The platform has four layers:

- **Engine** — Python DAG orchestration with SQLite storage, multi-provider LLM support, and Claude Agent SDK integration
- **CLI** — Click-based binary (`pixl`) that drives the engine
- **Crew Plugin** — 14 specialized agents, 70+ skills, shell hooks, and reference library for Claude Code
- **Sandboxes** — Cloudflare Workers containers where AI works in isolation with the full pixl stack

The end goal: sandboxed AI agents execute workflows with plugin assistance, all wired through the Claude Agent SDK. A future API + frontend will expose execution data, sessions, and results.

### Current State

The platform is **architecturally mature** with a production-grade engine (194+ modules, schema v35 with 40+ tables, FTS5 search, protocol-based storage, chain executor for parallel swarm work). The crew plugin is the most comprehensive Claude Code plugin available (14 agents, 70+ skills, hooks system with 3 profiles). The sandbox layer is functional with a full REST API.

### Key Findings

- **17 gaps** identified across SDK integration, sandbox wiring, and architecture
- **The biggest gap** is between what the Claude Agent SDK offers and what the engine actually uses — several key SDK features (programmatic plugin loading, agent definitions, callback hooks) are not wired
- **The sandbox is a "dumb pipe"** — it runs `pixl workflow run` as a shell command, not via the SDK. No real-time events, no session continuity, no data sync
- **The storage layer is ready** — protocol-based architecture was explicitly designed for swappable backends. All stores have comprehensive query methods
- **The chain executor** is the most advanced feature and closest to the "AI agent team" vision — parallel multi-feature execution with conflict detection, PR management, and quality judges

---

## 2. Current Architecture Map

### 2.1 Engine Layer

**Location**: `packages/engine/pixl/` — 194+ Python modules

| Component | Modules | Status | Description |
|-----------|---------|--------|-------------|
| **Domain Models** | `models/` (22 files) | Complete | Roadmap→Epic→Feature (planning), WorkflowSession→NodeInstance (execution), Baton (context relay), StageOutput (contracts) |
| **Storage** | `storage/` (32 files) | Complete | Protocol-based (Ports & Adapters). SQLite with WAL mode, FTS5, 40+ tables, schema v35. 5 domain stores: BacklogStore, SessionStore, ArtifactStore, EventStore, KnowledgeStore |
| **Execution** | `execution/` (56 files) | Complete | GraphExecutor (DAG step), TaskExecutor (SDK query loop), Chain executor (swarm parallel), Recovery engine |
| **Orchestration** | `orchestration/` (6 files) | Complete | OrchestratorCore wrapping claude_agent_sdk with persistent clients, streaming, circuit breaker |
| **Agents** | `agents/` (3 files) | Partial | SDK options builder with thinking/resume/output_format. No agent registry, no plugin loading |
| **Providers** | `providers/` (10 files) | Complete | ProviderRegistry for Anthropic, OpenAI, Gemini |
| **Knowledge** | `knowledge/` | Complete | AST-indexed code search with FTS5 + BM25 scoring |
| **Recovery** | `recovery/` (6 files) | Partial | Error classification, contract repair, incident tracking |

#### Domain Model Hierarchy

```
Planning Layer:                    Execution Layer:
Roadmap                           WorkflowTemplate
  └─ Epic                           └─ WorkflowSnapshot (immutable)
       └─ Feature                        └─ WorkflowSession
            ├─ depends_on[]                    ├─ ExecutorCursor (checkpoint)
            ├─ success_criteria[]              ├─ NodeInstance[] (per-node state)
            └─ cost tracking                   ├─ LoopState[] (iteration tracking)
                                               └─ Baton (inter-stage context)
```

#### Database Schema (v35)

**Core tables** (7): `roadmaps`, `milestones`, `epics`, `features`, `feature_dependencies`, `state_transitions`, `notes`

**Execution tables** (5): `workflow_sessions`, `node_instances`, `loop_states`, `workflow_snapshots`, `events`

**Artifact & Knowledge** (5): `artifacts`, `artifact_chunks`, `artifacts_fts`, `documents`, `chunks`, `chunks_fts`, `knowledge_manifest`

**Chain/Swarm** (5): `execution_chains`, `execution_chain_nodes`, `execution_chain_edges`, `chain_signals`, `chain_signals_fts`, `quality_scores`

**Metrics & Tracking** (9): `agent_metrics`, `autonomy_profiles`, `autonomy_outcomes`, `cost_events`, `heartbeat_runs`, `task_sessions`, `session_report_jobs`, `wakeup_requests`, `incidents`, `incidents_fts`

**Sandbox** (2): `sandbox_projects`, `sandbox_operations`

**Config** (3): `config`, `env_vars`, `schema_version`, `id_sequences`

**FTS5 indexes**: artifacts, chunks, incidents, chain_signals (with auto-sync triggers)

**Total**: 40+ tables, 80+ indexes

#### Execution Pipeline

```
WorkflowTemplate
    │
    ▼ (snapshot for immutability)
WorkflowSnapshot
    │
    ▼ (one per execution)
WorkflowSession
    │
    ▼
GraphExecutor.step()
    │
    ├─ Get ready nodes from ExecutorCursor.ready_queue
    ├─ If empty, compute from DAG predecessors
    │
    ▼
TaskExecutor.execute_with_orchestrator()
    │
    ├─ Build prompt (PromptBuilder + Baton context)
    ├─ Resolve agent + model
    ├─ Set up structured output format
    │
    ▼ (retry loop with validation)
OrchestratorCore.query_with_streaming()
    │
    ├─ [Anthropic] → ClaudeSDKClient (persistent, per agent+model)
    │                   ├─ Streaming messages → SDK events → EventStore
    │                   └─ ResultMessage → cost tracking, session ID
    │
    └─ [External] → query_external_provider() → OpenAI/Gemini API
    │
    ▼
StageOutput (structured)
    │
    ├─ ContractValidator → validates against node contract
    ├─ On failure → generate repair prompt → retry
    ├─ On success → apply baton_patch → follow edges
    │
    ▼
Save to SQLite (node_instances, events, artifacts, costs)
    │
    ▼
Next node(s) → repeat until terminal
```

#### Chain Executor (Swarm)

```
Epic with N features
    │
    ▼
ExecutionChain → topological sort → waves + parallel groups
    │
    ▼
ChainRunnerManager.run_chain_loop()
    │
    ├─ Reconcile running nodes from session state
    ├─ Refresh file claims (conflict detection)
    ├─ Process signal queue (blockers, discoveries, file_modified)
    ├─ Check judge quality gates
    ├─ Dispatch ready nodes (parallel execution)
    ├─ Auto-merge PRs if configured
    └─ Adaptive sleep (1-5s backoff)
```

### 2.2 CLI Layer

**Location**: `packages/cli/pixl_cli/` — 11 command modules

| Command | Engine Integration | Key Files |
|---------|-------------------|-----------|
| `pixl workflow run --prompt <PRD>` | GraphExecutor, TaskExecutor | `commands/workflow.py` |
| `pixl session list/get/create` | WorkflowSessionStore | `commands/session.py` |
| `pixl artifact get/put/list/search` | ArtifactStore (FTS5) | `commands/artifact.py` |
| `pixl knowledge build/search/context` | KnowledgeStore (FTS5 + BM25) | `commands/knowledge.py` |
| `pixl events list` | EventStore | `commands/events.py` |
| `pixl state show/graph/deps` | TransitionEngine | `commands/state.py` |
| `pixl project init/list/get/create/delete` | ProjectRegistry | `commands/project.py` |
| `pixl config get/set` | ConfigStore | `commands/config.py` |
| `pixl setup` | Plugin registration | `commands/setup.py` |
| `pixl sandbox create/workflow/events/destroy` | SandboxClient (HTTP) | `commands/sandbox.py` |

**Crew integration**: `crew.py` resolves crew root via `PIXL_CREW_ROOT` env → monorepo `packages/crew/` → bundled `_crew/` in wheel.

**Output**: Unified formatting via `_output.py` — `emit_json()`, `emit_table()`, `emit_detail()`, `emit_error()`. Supports `--json` flag for machine output.

### 2.3 Sandbox Layer

**Location**: `packages/sandbox/` — Cloudflare Workers + Durable Objects

| Component | Technology | Description |
|-----------|-----------|-------------|
| **Router** | Hono (TypeScript) | REST API with bearer auth, CORS, 10MB body limit |
| **Runtime** | Cloudflare Durable Objects | Isolated container per sandbox |
| **Container** | Docker (`cloudflare/sandbox:0.7.18`) | Python 3.12 + uv + pixl-cli + Claude Code CLI |
| **Init** | Shell script | `pixl project init` + `pixl setup` inside container |

**Endpoints**:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sandboxes` | POST | Create sandbox (env vars, git clone, pixl init) |
| `/sandboxes/:id` | DELETE | Destroy sandbox |
| `/sandboxes/:id/status` | GET | Versions, git info, project state, env var names |
| `/sandboxes/:id/exec` | POST | Execute command (stdout/stderr/exitCode) |
| `/sandboxes/:id/exec/stream` | POST | SSE command stream |
| `/sandboxes/:id/workflow` | POST | Run `pixl workflow run --prompt "..."` |
| `/sandboxes/:id/workflow/stream` | POST | SSE workflow stream |
| `/sandboxes/:id/events` | GET | Fetch pixl events from sandbox DB |
| `/sandboxes/:id/sessions` | GET | Fetch pixl sessions from sandbox DB |
| `/sandboxes/:id/files` | GET/POST | Read/write files (path validation) |
| `/sandboxes/:id/git` | GET | Git status, log, branch |
| `/sandboxes/:id/git/push` | POST | Git push with logging |
| `/sandboxes/:id/git/config` | POST | Set git user/email/remote |
| `/sandboxes/:id/env` | POST | Update env vars at runtime |
| `/sandboxes/:id/process/start` | POST | Start background process |
| `/sandboxes/:id/process/:pid` | DELETE | Kill background process |
| `/sandboxes/:id/usage` | GET | Aggregated operation stats |

**Sandbox data flow**:
```
CLI → SandboxClient (httpx, sync)
    │
    ▼ HTTP POST /sandboxes/:id/workflow
Cloudflare Worker → Durable Object
    │
    ▼ sb.exec("pixl workflow run --prompt '...' --json")
CLI process inside container → Engine → SDK → Claude API
    │
    ▼
stdout/stderr → JSON response or SSE stream
    │
    ▼ HTTP response
CLI receives result, logs operation to local SandboxDB
```

### 2.4 Crew Plugin

**Location**: `packages/crew/` — bash/markdown (NOT a Python package)

| Component | Count | Description |
|-----------|-------|-------------|
| **Agents** | 14 | Markdown files with YAML frontmatter (model, color, memory, tools, skills) |
| **Skills** | 70+ | SKILL.md files with frontmatter (allowed-tools, description, context) |
| **Hooks** | 15+ scripts | Shell hooks via hooks.json covering SessionStart, PreToolUse, PostToolUse, Notification, Stop |
| **References** | 20+ files | Shared domain knowledge (backend, frontend, devops, methodology, standards) |
| **Studio stacks** | 2 | nextjs (website scaffold), saas (DDD microservice scaffold) |
| **Contexts** | 3 | Dynamic overlays: dev, research, review |
| **Schemas** | 3 | JSON schemas for hooks, plugins, skill-config |

**Agent specializations**:

| Agent | Model | Memory | Role |
|-------|-------|--------|------|
| `orchestrator` | opus | project | Multi-phase coordinator |
| `architect` | opus | project | System design, DDD (read-only) |
| `tech-lead` | opus | project | Code review, quality gates |
| `security-engineer` | opus | project | OWASP audits, RBAC (read-only) |
| `product-owner` | sonnet | — | Task decomposition, sprints |
| `qa-engineer` | sonnet | — | Testing, browser verification |
| `devops-engineer` | sonnet | — | Docker, CI/CD, deployment |
| `build-error-resolver` | sonnet | — | Surgical build error fixes |
| `frontend-engineer` | inherit | — | React/Next.js, shadcn/ui |
| `backend-engineer` | inherit | — | Fastify/Prisma or FastAPI/Pydantic |
| `fullstack-engineer` | inherit | — | End-to-end API + UI |
| `explorer` | haiku | user | Fast codebase search (read-only) |
| `onboarding-agent` | haiku | user | Client project scanning (read-only) |
| `doc-updater` | haiku | user | Keep docs in sync |

**Hook profiles**:

| Profile | Hooks | Use Case |
|---------|-------|----------|
| `minimal` | Block destructive commands only | CI/CD, production |
| `standard` | + formatting, TDD, skill enforcement | Development |
| `strict` | + typecheck, console.log audit | Code review |

### 2.5 Integration Points

| From | To | Mechanism | Status |
|------|----|-----------|--------|
| CLI → Engine | Python import | Direct function calls, same process | Working |
| Engine → Claude SDK | `claude_agent_sdk` | Persistent clients, async streaming | Working |
| Engine → External LLMs | `anthropic`/`openai` SDK | Direct API via ProviderRegistry | Working |
| CLI → Sandbox | `SandboxClient` (httpx) | HTTP/REST, synchronous | Working |
| Sandbox → Engine | Shell commands | `pixl workflow run` inside container | Working (limited) |
| Crew → Claude Code | `plugin.json` + `hooks.json` | Plugin registration | Working |
| Engine → Crew | **None** | No bridge between engine and crew agents/skills/hooks | **GAP** |
| Sandbox → Parent DB | **None** | No data sync mechanism | **GAP** |
| Engine → Real-time consumers | **None** | Events stored in SQLite, no pub/sub | **GAP** |

---

## 3. SDK Integration Analysis

### 3.1 Feature Comparison

| SDK Feature | SDK Docs Reference | Engine Status | Details |
|-------------|-------------------|---------------|---------|
| `plugins` parameter | "Plugins in the SDK" | **Not used** | `build_sdk_options()` does not pass `plugins` to `ClaudeAgentOptions` |
| `agents` parameter | "Subagents in the SDK" | **Accepted, never populated** | `build_sdk_options()` accepts `agents` param but no one populates from crew |
| `settingSources` | "Skills in the SDK" | **Used** | `setting_sources=["user", "project"]` at `sdk_options.py:167` |
| `Skill` tool | "Skills in the SDK" | **Available** | Implicitly available via `setting_sources` |
| `outputFormat` (JSON Schema) | "Structured Output" | **Used** | `output_format` param forwarded at `sdk_options.py:192` |
| `HookCallback` functions | "Hooks" | **Partial** | Safety hooks only (tool budget, context window). Crew hooks not bridged |
| `resume` / `continue_conversation` | "Subagents resuming" | **Used** | `sdk_options.py:172-175` |
| `fork_session` | "Subagents" | **Used** | `sdk_options.py:197` |
| `total_cost_usd` / `modelUsage` | "Cost Tracking" | **Used** | Engine tracks via `cost_events` table |
| `TodoWrite` tool | "Todo Lists" | **Not integrated** | SDK Todo system not connected to engine task system |
| `canUseTool` callback | "Permissions" | **Not used** | Static `bypassPermissions` mode only |
| Slash commands via prompt | "Slash Commands" | **Not used** | Could use `/compact` in long workflows |
| `ClaudeSDKClient` persistent | "Overview" | **Used** | Keyed by (agent_name, model) at `core.py:98` |
| `thinking` config | "SDK Reference" | **Used** | Adaptive/enabled/disabled at `sdk_options.py:199` |
| `effort` parameter | "SDK Reference" | **Used** | `sdk_options.py:128` |
| `max_budget_usd` | "SDK Reference" | **Used** | `sdk_options.py:184` |
| `fallback_model` | "SDK Reference" | **Used** | `sdk_options.py:188` |
| `system_prompt` | "SDK Reference" | **Used** | `sdk_options.py:180` |

### 3.2 GAP-01: Plugin Not Loaded Programmatically

**Current state**: `build_sdk_options()` at `packages/engine/pixl/agents/sdk_options.py:161` constructs `ClaudeAgentOptions` with `setting_sources=["user", "project"]` but **no `plugins` parameter**. The crew plugin is only registered for CLI use via `pixl setup` (writes to `~/.claude/plugins/installed_plugins.json`).

**SDK capability** (from "Plugins in the SDK"):
```python
ClaudeAgentOptions(
    plugins=[{"type": "local", "path": "/path/to/crew"}],
    setting_sources=["user", "project"],
)
```

**Impact**: In headless contexts (sandbox containers, future API, CI), the crew plugin may not be available to the SDK session. Skills, agents, and hooks defined in the plugin won't be loaded unless `pixl setup` was previously run in that environment.

**Recommended fix**:
- Add `plugins` parameter to `build_sdk_options()`
- Resolve crew root via `pixl_cli.crew.get_crew_root()` or `PIXL_CREW_ROOT` env var
- Pass `plugins=[{"type": "local", "path": crew_root}]` to `ClaudeAgentOptions`

**Files**: `packages/engine/pixl/agents/sdk_options.py`

**Priority**: P1

### 3.3 GAP-02: No Agent Registry Bridge

**Current state**: The engine has `ProviderRegistry` for LLM providers but **no `AgentRegistry`**. Crew agents are defined as markdown files with YAML frontmatter (`packages/crew/agents/*.md`). The engine's `build_sdk_options()` at `sdk_options.py:114` accepts `agents: dict[str, AgentDefinition]` but this parameter is never populated from crew files. `_build_query_options()` at `core.py:241` forwards agents but they're always `None` unless explicitly passed by callers.

**SDK capability** (from "Subagents in the SDK"):
```python
agents={
    "code-reviewer": AgentDefinition(
        description="Expert code reviewer...",
        prompt="You are a code review specialist...",
        tools=["Read", "Grep", "Glob"],
        model="sonnet",
    )
}
```

**What crew agent markdown contains**:
```yaml
---
name: backend-engineer
description: "Delegate to this agent for backend implementation..."
color: green
model: inherit
tools: [Read, Write, Edit, Bash, Glob, Grep, Task]
skills: [ddd-pattern, fastapi-service]
maxTurns: 50
---
System prompt content here...
```

**Impact**: The engine cannot programmatically leverage crew agent specializations. When running workflows, there's no way to:
- Auto-select the right agent (model, tools) for a task node
- Delegate to specialist subagents via the SDK's native `agents` parameter
- Enforce tool restrictions per agent (e.g., read-only for architect)

**Recommended fix**:
1. Create `AgentRegistry` class that parses crew markdown frontmatter
2. Map crew fields to SDK `AgentDefinition`: `model` → SDK model, `tools` → tools list, body → prompt
3. Load registry at engine startup from crew root
4. Modify `build_sdk_options()` to accept registry and auto-resolve agents
5. Modify `_build_query_options()` to pass agents from registry

**Files**:
- New: `packages/engine/pixl/agents/registry.py`
- New: `packages/engine/pixl/agents/parser.py`
- Modify: `packages/engine/pixl/agents/sdk_options.py`
- Modify: `packages/engine/pixl/orchestration/core.py`

**Priority**: P1

### 3.4 GAP-03: Shell Hooks Only, No SDK Callback Hooks

**Current state**: The crew plugin defines 15+ hook scripts in `packages/crew/hooks/hooks.json` covering:
- `block-destructive.sh` — Prevent unsafe commands (PreToolUse:Bash)
- `detect-secrets.sh` — Scan for credential leaks (PreToolUse:Write|Edit)
- `tdd-check.sh` — Enforce TDD practices (PreToolUse:Write|Edit)
- `quality-gate.sh` — Post-edit quality validation (PostToolUse:Write|Edit)
- `enforce-skill-first.sh` — Route to skills before ad-hoc (PreToolUse:Agent)
- `observe-patterns.sh` — Learn from session patterns (PostToolUse)
- `cost-tracker.sh` — Log token usage (PostToolUse)
- `validate-agent-selection.sh` — Check agent routing (PreToolUse:Agent)

The engine uses only safety hooks from `pixl.agents.hooks` at `sdk_options.py:142-159` — tool budget, context window, output truncation.

**SDK capability** (from "Hooks"):
```python
async def block_destructive(input_data, tool_use_id, context):
    command = input_data["tool_input"].get("command", "")
    if any(cmd in command for cmd in ["rm -rf", "git push --force"]):
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "Destructive command blocked",
            }
        }
    return {}

ClaudeAgentOptions(
    hooks={
        "PreToolUse": [HookMatcher(matcher="Bash", hooks=[block_destructive])]
    }
)
```

**Impact**: When the engine runs workflows directly (not through Claude Code CLI), it misses the crew's quality gates. TDD enforcement, destructive command blocking, secret detection, and skill routing only fire in interactive Claude Code sessions.

**Recommended fix**:
1. Create hook adapter that wraps shell scripts as async Python `HookCallback` functions
2. Register critical hooks (block-destructive, detect-secrets, quality-gate) as SDK callbacks
3. Maintain shell script as source of truth; Python adapter executes via subprocess
4. Add profile-based selection (which hooks to bridge)

**Files**:
- New: `packages/engine/pixl/agents/hooks/crew_bridge.py`
- Modify: `packages/engine/pixl/agents/sdk_options.py`

**Priority**: P2

### 3.5 GAP-04: Structured Output Could Leverage Pydantic Natively

**Current state**: The engine uses SDK structured output via `output_format` parameter. `TaskExecutor` sends a JSON Schema and validates with `ContractValidator`. However, the engine's domain models are already Pydantic — `StageOutput`, `Baton`, `Feature`, etc. These could generate JSON schemas automatically via `.model_json_schema()` instead of maintaining separate contract definitions.

**SDK capability** (from "Structured Output"):
```python
class FeaturePlan(BaseModel):
    feature_name: str
    steps: list[Step]
    risks: list[str]

ClaudeAgentOptions(
    output_format={
        "type": "json_schema",
        "schema": FeaturePlan.model_json_schema(),
    }
)
# Result: plan = FeaturePlan.model_validate(message.structured_output)
```

**Impact**: Maintaining separate JSON Schema definitions when Pydantic models already exist creates drift risk. Using `.model_json_schema()` ensures the output schema always matches the domain model.

**Recommended fix**: Where Pydantic models already define the expected output shape, use `.model_json_schema()` to generate the `output_format` schema instead of manual JSON Schema construction.

**Files**: `packages/engine/pixl/execution/task_executor.py`

**Priority**: P3 (nice-to-have, existing system works)

### 3.6 GAP-05: TodoWrite Not Integrated with Engine

**Current state**: The SDK's `TodoWrite` tool tracks task progress within a session. The engine has its own task tracking via `NodeInstance` states (task_pending → task_running → task_completed) and the backlog (Feature states). These are disconnected.

**SDK capability** (from "Todo Lists"):
```python
# SDK automatically creates todos for complex multi-step tasks
# TodoWrite tool updates: pending → in_progress → completed
```

**Impact**: Low. The engine's NodeInstance tracking is more sophisticated. However, if workflows run inside Claude Code sessions with the SDK, TodoWrite updates could provide UX-visible progress that complements engine-level tracking.

**Recommended fix**: Consider a PostToolUse hook that mirrors TodoWrite updates to NodeInstance states, or vice versa.

**Priority**: P3

### 3.7 GAP-06: No Dynamic Permission Handling

**Current state**: `build_sdk_options()` sets `permission_mode="bypassPermissions"` at `sdk_options.py:163`. All tools are auto-approved. No `canUseTool` callback is used.

**SDK capability** (from "Permissions"):
```python
# canUseTool callback for dynamic per-tool-call decisions
ClaudeAgentOptions(
    permission_mode="dontAsk",
    allowed_tools=["Read", "Grep", "Glob"],
)
```

**Impact**: In sandbox contexts, all tools are available with no restrictions. A `canUseTool` callback could enforce per-node tool restrictions based on the workflow template's `TaskConfig.tools` or the agent's allowed tools from the registry.

**Recommended fix**: When agent registry (GAP-02) is implemented, use the agent's tool list to populate `allowed_tools` per-query instead of using a global bypass.

**Files**: `packages/engine/pixl/agents/sdk_options.py`

**Priority**: P2

---

## 4. Sandbox-Engine Integration Analysis

### 4.1 GAP-07: Sandbox Runs CLI Commands, Not SDK

**Current state**: The sandbox router at `packages/sandbox/src/router.ts` (workflow endpoint) executes workflows via:
```typescript
const result = await sb.exec(
    `pixl workflow run --prompt "${escapedPrompt}" ${workflowFlag} ${yesFlag} --json`,
    { timeout, env }
);
```

This spawns a CLI process inside the container, which starts the engine, which then uses the SDK. The sandbox Worker itself has no SDK client.

**What could be done**: The Claude Agent SDK has a TypeScript SDK (`@anthropic-ai/claude-agent-sdk`). The sandbox Worker could import it directly:
```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
    prompt: "...",
    options: {
        plugins: [{ type: "local", path: "/opt/pixl-crew" }],
        cwd: "/workspace",
        settingSources: ["user", "project"],
    }
})) {
    // Stream SDK messages directly
}
```

**Impact**: Current approach means:
- No structured SDK message events from sandbox (only stdout text)
- No real-time progress visibility at the protocol level
- No ability to resume or fork SDK sessions from the parent orchestrator
- Double process overhead (Worker → shell → Python → SDK)

**Recommended fix** (phased):
1. **Short-term**: Improve the CLI JSON output to include structured events, not just final result
2. **Medium-term**: Use the TypeScript SDK directly in the Worker for Anthropic models
3. **Long-term**: Have the sandbox Worker act as an SDK proxy, streaming SDK messages to the parent via WebSocket

**Files**: `packages/sandbox/src/router.ts`

**Priority**: P1

### 4.2 GAP-08: No Real-Time Event Streaming from Sandbox

**Current state**: The sandbox supports SSE streaming for `exec/stream` and `workflow/stream` endpoints, but these stream **stdout lines**, not structured events. The parent CLI (`SandboxClient`) is synchronous httpx — it doesn't consume SSE at all.

```python
# SandboxClient.workflow() — synchronous, no streaming
def workflow(self, project_id: str, prompt: str, ...) -> dict:
    resp = self._post(f"/sandboxes/{project_id}/workflow", json=body)
    return resp.json()
```

**Impact**: The parent has no real-time visibility into sandbox execution. It sends a request and waits for completion. No progress updates, no intermediate events, no ability to react to errors in real-time.

**Recommended fix**:
1. Make `SandboxClient` async and add SSE consumption for streaming endpoints
2. Parse SSE events into structured `Event` objects matching the engine's event schema
3. Forward parsed events to the parent's EventStore for persistence
4. Add a WebSocket-based alternative for bidirectional communication

**Files**:
- `packages/cli/pixl_cli/sandbox_client.py`
- `packages/sandbox/src/router.ts` (add structured event SSE format)

**Priority**: P1

### 4.3 GAP-09: No Session Continuity Across Sandbox Boundaries

**Current state**: Each `pixl workflow run` inside a sandbox creates a new WorkflowSession with its own SQLite state. The parent orchestrator has no way to:
- Resume a sandbox workflow session from the parent
- Fork a sandbox session into a new sandbox
- Continue a conversation across sandbox restarts

The engine supports `resume_session_id` and `fork_session` at the SDK level (`sdk_options.py:172-197`), but these operate within a single process/environment.

**Impact**: Multi-sandbox orchestration scenarios (e.g., run feature A in sandbox 1, feature B in sandbox 2, merge results) require independent workflows with no shared session context.

**Recommended fix**:
1. Export SDK session IDs from sandbox via the status endpoint
2. Add a session export/import mechanism (serialize session state as JSON)
3. When creating a new sandbox, optionally pass a `fork_from_session_id` that bootstraps from exported state

**Files**:
- `packages/sandbox/src/router.ts` (expose session IDs in status)
- `packages/engine/pixl/storage/sync.py` (new: session serialization)

**Priority**: P2

### 4.4 GAP-10: No Data Sync Between Sandbox and Parent

**Current state**: The sandbox has its own SQLite DB at `/workspace/.pixl/pixl.db`. The parent's `SandboxClient` reads sandbox data via HTTP calls that shell out to CLI commands:

```typescript
// router.ts — events endpoint
const result = await sb.exec("pixl events list --json", { timeout: 30_000 });
return c.json(JSON.parse(result.stdout));
```

After sandbox destruction, all execution data (events, artifacts, sessions, costs) is lost.

**Impact**:
- No persistent record of sandbox execution history in the parent system
- No unified cost aggregation across sandbox and local executions
- Audit trail has gaps — sandbox events disappear on destroy
- No way to query historical sandbox data from a dashboard

**Recommended fix**:
1. Add `GET /sandboxes/:id/export` endpoint to sandbox Worker — bulk export of events, sessions, artifacts, costs as JSON
2. Add `pixl sandbox sync <project-id>` CLI command that pulls data and stores in parent DB with sandbox provenance
3. Add `sandbox_id` column to events, sessions, and artifacts tables for provenance tracking
4. Trigger sync automatically on `pixl sandbox destroy` (pre-destroy hook)
5. Optionally, periodic sync during long-running workflows

**Files**:
- `packages/sandbox/src/router.ts` (add export endpoint)
- `packages/engine/pixl/storage/db/schema.py` (add provenance columns)
- New: `packages/engine/pixl/storage/sync.py`
- `packages/cli/pixl_cli/commands/sandbox.py` (add sync command)

**Priority**: P1

### 4.5 GAP-11: No Pause/Interrupt from Parent

**Current state**: Once a workflow starts in a sandbox, the parent has no way to pause, interrupt, or cancel it. The only option is to destroy the sandbox entirely.

The engine has `OrchestratorCore.request_interrupt()` at `core.py:151` which sets a threading Event, but this is in-process only — not exposed via HTTP.

**Impact**: Long-running workflows in sandboxes cannot be gracefully stopped. If a workflow is consuming too many tokens or going in the wrong direction, the only recourse is destruction.

**Recommended fix**:
1. Add `POST /sandboxes/:id/workflow/cancel` endpoint
2. Inside sandbox, propagate cancel signal to the running `pixl workflow run` process
3. Engine should handle SIGINT/SIGTERM gracefully (save session state before exit)

**Files**:
- `packages/sandbox/src/router.ts`
- `packages/engine/pixl/execution/graph_executor.py` (graceful shutdown)

**Priority**: P2

---

## 5. Architecture Gaps & Technical Debt

### 5.1 GAP-12: Plugin-Engine Contract Disconnect

**Current state**: The crew plugin (bash/markdown) and the engine (Python/Pydantic) have **no shared contract**:

| Concept | Crew Plugin | Engine |
|---------|------------|--------|
| Agent definition | Markdown YAML frontmatter | `AgentDefinition` (SDK Pydantic model) |
| Skill definition | SKILL.md with frontmatter | No skill registry |
| Hook definition | Shell scripts in hooks.json | `HookCallback` Python functions |
| Agent routing | Claude Code's semantic matching | Manual agent name passing |
| Configuration | Plugin settings (JSON) | `ConfigStore` (SQLite) |

**Impact**: The engine and plugin operate as parallel systems. The engine can run workflows without the plugin's agents, and the plugin's agents can run without the engine's orchestration. There's no single source of truth for agent capabilities.

**Recommended fix**: Build the agent registry (GAP-02) and plugin loading (GAP-01) bridges. The crew markdown files remain the source of truth; the engine parses them into SDK-compatible structures at startup.

**Priority**: P1

### 5.2 GAP-13: No Real-Time Event Bus

**Current state**: Events are written to SQLite's `events` table via `EventStore.emit()`. There is no publish/subscribe mechanism. No way for external consumers to receive events in real-time.

**Impact**: A frontend dashboard would need to poll the database, adding latency and inefficiency. The sandbox cannot push events to the parent in real-time.

**Recommended fix**:
1. Create in-process event bus using asyncio queues
2. Add optional Redis pub/sub backend for cross-process events
3. Hook into `EventStore.emit()` to publish events to the bus
4. Consumers (WebSocket endpoint, sandbox sync, monitoring) subscribe to the bus

**Files**:
- New: `packages/engine/pixl/events/bus.py`
- New: `packages/engine/pixl/events/schemas.py`
- Modify: `packages/engine/pixl/storage/db/events.py`

**Priority**: P1

### 5.3 GAP-14: Workflow Templates Filesystem-Only

**Current state**: Workflow templates are YAML files loaded from `.pixl/workflows/` via `WorkflowLoader`. No database storage, no versioning, no CRUD operations beyond filesystem.

**Impact**: Templates cannot be managed, versioned, or shared via an API. A frontend cannot create or edit workflow templates without filesystem access.

**Recommended fix**:
1. Add `workflow_templates` table to schema
2. Add `WorkflowTemplateStore` protocol
3. Support both filesystem and DB templates (filesystem takes precedence for dev)
4. Add template versioning with change tracking

**Files**:
- `packages/engine/pixl/storage/db/schema.py`
- `packages/engine/pixl/storage/protocols.py`
- New: `packages/engine/pixl/storage/db/workflow_templates.py`

**Priority**: P2

### 5.4 GAP-15: Single-Tenant SQLite

**Current state**: Each project has its own `pixl.db` at `{project}/.pixl/pixl.db`. The `StorageBackend` protocol was designed for swappable backends (the docstring at `protocols.py:17` explicitly mentions `pg/` for PostgreSQL and `api/` for remote API), but only the SQLite adapter exists.

**Impact**: Multi-project aggregation requires connecting to multiple SQLite files. Not suitable for a multi-user SaaS scenario. However, this is architecturally sound — the protocol abstraction means a PostgreSQL adapter can be added without changing any calling code.

**Recommended fix**: For now, SQLite is appropriate for single-user/single-project use. When multi-tenancy is needed:
1. Implement a PostgreSQL adapter for `StorageBackend`
2. Or create a "meta-DB" that indexes project summaries from SQLite files

**Priority**: P3 (deferred)

### 5.5 GAP-16: Security Gaps

| Issue | Location | Severity | Description |
|-------|----------|----------|-------------|
| Static bearer token | `sandbox/src/router.ts` | Medium | `SANDBOX_API_KEY` with no rotation or expiry |
| Plaintext API keys | `sandbox_client.py:46-52`, `router.ts:73-79` | Medium | `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` forwarded in HTTP body |
| No rate limiting | `sandbox/src/router.ts` | Low | Sandbox endpoints have no rate limiting |
| No encryption at rest | `storage/db/connection.py` | Low | SQLite DB may contain sensitive code, artifacts |
| No API access audit | All layers | Low | Only sandbox operation logging exists |

**Recommended fix**:
1. JWT-based sandbox auth with expiry (replace static bearer token)
2. Use sandbox's native `setEnvVars()` for secrets instead of passing in HTTP body
3. Add rate limiting middleware to Hono router
4. Consider SQLCipher for sensitive deployments

**Priority**: P2

### 5.6 GAP-17: Cost/Metrics Tables Without Aggregation

**Current state**: The schema has comprehensive tracking tables:
- `cost_events` — per-execution cost (session_id, node_id, model, input/output tokens, cost_usd)
- `agent_metrics` — per-agent performance (agent_name, model, success rate, error types)
- `autonomy_outcomes` — session-level autonomy tracking
- `heartbeat_runs` — execution windows with token counts
- `quality_scores` — swarm quality metrics

These tables are populated during execution but there are no aggregation queries, no summary views, and no way to query "total cost by model this week" or "most expensive workflow" without writing raw SQL.

**Recommended fix**:
1. Add aggregation methods to the storage protocols: `get_cost_summary()`, `get_agent_performance()`, `get_session_costs()`
2. These feed into future API endpoints when the API layer is built

**Files**:
- `packages/engine/pixl/storage/protocols.py`
- New: `packages/engine/pixl/storage/db/analytics.py`

**Priority**: P2

---

## 6. Recommendations Matrix

### SDK Integration

| Priority | Gap | Recommendation | Impact | Effort | Key Files |
|----------|-----|---------------|--------|--------|-----------|
| P1 | GAP-01 | Add `plugins` param to `build_sdk_options()`, resolve crew root | Ensures crew available in all contexts | 0.5 day | `sdk_options.py` |
| P1 | GAP-02 | Build AgentRegistry — parse crew markdown into SDK AgentDefinition | Enables programmatic agent selection and delegation | 2 days | New: `agents/registry.py`, `agents/parser.py`; Modify: `sdk_options.py`, `core.py` |
| P2 | GAP-03 | Bridge crew shell hooks to SDK HookCallbacks | Brings quality gates into engine workflows | 2 days | New: `agents/hooks/crew_bridge.py`; Modify: `sdk_options.py` |
| P3 | GAP-04 | Use Pydantic `.model_json_schema()` for output_format | Eliminates schema drift | 0.5 day | `task_executor.py` |
| P3 | GAP-05 | Mirror TodoWrite to NodeInstance states | Unified progress tracking | 1 day | Hook integration |
| P2 | GAP-06 | Use agent tool lists for `allowed_tools` per query | Enforces agent specialization | 0.5 day | `sdk_options.py` |

### Sandbox Wiring

| Priority | Gap | Recommendation | Impact | Effort | Key Files |
|----------|-----|---------------|--------|--------|-----------|
| P1 | GAP-07 | Phase 1: Structured CLI output. Phase 2: TypeScript SDK in Worker | Real SDK event visibility | 3 days | `router.ts` |
| P1 | GAP-08 | Async SandboxClient with SSE consumption | Real-time progress updates | 2 days | `sandbox_client.py`, `router.ts` |
| P2 | GAP-09 | Session export/import mechanism | Multi-sandbox orchestration | 2 days | `router.ts`, new: `storage/sync.py` |
| P1 | GAP-10 | Export endpoint + sync command + provenance columns | Persistent sandbox data | 3 days | `router.ts`, `schema.py`, new: `storage/sync.py`, `commands/sandbox.py` |
| P2 | GAP-11 | Workflow cancel endpoint + graceful shutdown | Control over long-running workflows | 1 day | `router.ts`, `graph_executor.py` |

### Architecture

| Priority | Gap | Recommendation | Impact | Effort | Key Files |
|----------|-----|---------------|--------|--------|-----------|
| P1 | GAP-12 | Solved by GAP-01 + GAP-02 | Plugin-engine bridge | (included above) | — |
| P1 | GAP-13 | In-process event bus + optional Redis pub/sub | Enables real-time consumers | 2 days | New: `events/bus.py`, `events/schemas.py` |
| P2 | GAP-14 | DB-backed workflow templates with versioning | API-manageable templates | 2 days | `schema.py`, `protocols.py`, new: `workflow_templates.py` |
| P3 | GAP-15 | PostgreSQL adapter (when needed) | Multi-tenancy | 5+ days | New: `storage/pg/` |
| P2 | GAP-16 | JWT auth, rate limiting, secure env transport | Production readiness | 2 days | `router.ts`, `sandbox_client.py` |
| P2 | GAP-17 | Aggregation queries + analytics store | Cost visibility | 1 day | `protocols.py`, new: `analytics.py` |

### Priority Summary

| Priority | Count | Description |
|----------|-------|-------------|
| **P1** | 7 gaps | Plugin loading, agent registry, sandbox SDK/sync/events, event bus, contract bridge |
| **P2** | 7 gaps | Hook bridge, dynamic permissions, session continuity, cancel, templates, security, analytics |
| **P3** | 3 gaps | Pydantic schemas, TodoWrite, PostgreSQL adapter |

---

## 7. SDK Feature Compatibility Checklist

Full checklist of every feature from the official Claude Agent SDK documentation:

### Plugins (from "Plugins in the SDK")

| Feature | Status | Notes |
|---------|--------|-------|
| Load plugins via `plugins` param | **Missing** | GAP-01: Not passed in `build_sdk_options()` |
| Plugin path resolution (relative/absolute) | **N/A** | Not loading plugins programmatically yet |
| Verify plugin in init message | **N/A** | Not loading plugins programmatically yet |
| Plugin skill namespacing (`plugin:skill`) | **Available** | Works when plugin registered via `pixl setup` |
| Multiple plugin sources | **Available** | Companion plugins installed via setup |

### Skills (from "Skills in the SDK")

| Feature | Status | Notes |
|---------|--------|-------|
| `settingSources` for skill loading | **Used** | `["user", "project"]` at `sdk_options.py:167` |
| `Skill` in `allowed_tools` | **Used** | Included in `DEFAULT_TOOLS` |
| Project skills (`.claude/skills/`) | **Available** | Loaded via `setting_sources` |
| User skills (`~/.claude/skills/`) | **Available** | Loaded via `setting_sources` |
| Plugin skills | **Partial** | Depends on plugin being loaded (GAP-01) |
| `allowed-tools` frontmatter | **N/A** | Not supported in SDK (only CLI) |

### Subagents (from "Subagents in the SDK")

| Feature | Status | Notes |
|---------|--------|-------|
| `agents` param (programmatic) | **Accepted, unused** | GAP-02: Parameter exists but never populated from crew |
| `AgentDefinition` (description, prompt, tools, model) | **Available** | Imported from `claude_agent_sdk` |
| Filesystem agents (`.claude/agents/`) | **Available** | Crew agents loaded when plugin registered |
| Agent tool restrictions | **Not used** | All agents get full tool access |
| Dynamic agent configuration (factory) | **Not used** | Could be useful for per-node agent config |
| Subagent resuming | **Used** | `resume_session_id` in options |
| Built-in general-purpose agent | **Available** | Always available via Agent tool |

### Slash Commands (from "Slash Commands in the SDK")

| Feature | Status | Notes |
|---------|--------|-------|
| Send `/compact` via prompt | **Not used** | Could help in long-running workflows |
| Send `/clear` via prompt | **Not used** | Could help between workflow stages |
| Custom slash commands | **Available** | Via crew skills/commands |
| Discover commands in init message | **Not used** | Could validate crew registration |

### Hooks (from "Hooks")

| Feature | Status | Notes |
|---------|--------|-------|
| `PreToolUse` callback | **Partial** | Safety hooks only (tool budget, context window) |
| `PostToolUse` callback | **Partial** | Safety hooks only |
| `Stop` callback | **Not used** | Could persist state on workflow end |
| `SubagentStart`/`SubagentStop` | **Not used** | Could track parallel agent activity |
| `Notification` callback | **Not used** | Could forward to monitoring |
| `PreCompact` callback | **Not used** | Could archive before summarizing |
| `PermissionRequest` callback | **Not used** | Using `bypassPermissions` instead |
| `UserPromptSubmit` callback | **Not used** | Could inject workflow context |
| `SessionStart`/`SessionEnd` (TS only) | **N/A** | Engine is Python |
| Matchers (regex patterns) | **Partial** | Used with safety hooks |
| Async hook output | **Not used** | Could be useful for logging/telemetry |
| `updatedInput` (modify tool input) | **Not used** | Could redirect file paths in sandbox |
| `systemMessage` injection | **Not used** | Could inject workflow context |

### Structured Output (from "Structured Output")

| Feature | Status | Notes |
|---------|--------|-------|
| `outputFormat` with JSON Schema | **Used** | Forwarded via `output_format` param |
| Zod/Pydantic schema generation | **Partial** | Manual schemas used instead of `.model_json_schema()` (GAP-04) |
| `structured_output` on result message | **Used** | Parsed in TaskExecutor |
| Error handling (`error_max_structured_output_retries`) | **Used** | Retry logic in TaskExecutor |

### Cost Tracking (from "Cost Tracking")

| Feature | Status | Notes |
|---------|--------|-------|
| `total_cost_usd` on result message | **Used** | Stored in `cost_events` table |
| Per-step token usage (TS only) | **N/A** | Engine is Python |
| `modelUsage` breakdown (TS only) | **N/A** | Engine is Python |
| Accumulate across queries | **Used** | `cost_events` aggregates per session |
| Cache token tracking | **Partial** | SDK handles caching automatically |

### Todo Lists (from "Todo Lists")

| Feature | Status | Notes |
|---------|--------|-------|
| `TodoWrite` tool monitoring | **Not used** | GAP-05: Not integrated with engine task system |
| Real-time progress display | **Not used** | Engine has its own progress via NodeInstance |

### Hosting (from "Hosting")

| Feature | Status | Notes |
|---------|--------|-------|
| `ClaudeSDKClient` persistent | **Used** | Keyed by (agent, model) at `core.py:98` |
| Client lifecycle management | **Used** | `cleanup_sdk_clients()` at `core.py:139` |
| Concurrent query support | **Used** | `ConcurrencyManager` for parallel execution |

---

## 8. Critical Files Index

### Engine (`packages/engine/pixl/`)

| File | Lines | Role |
|------|-------|------|
| `agents/sdk_options.py` | ~210 | SDK options builder — central point for all SDK configuration |
| `agents/constants.py` | ~30 | Default tool set for SDK sessions |
| `orchestration/core.py` | ~400 | OrchestratorCore — persistent SDK clients, streaming, circuit breaker |
| `execution/graph_executor.py` | ~600 | DAG step algorithm, event emission, state management |
| `execution/task_executor.py` | ~500 | SDK query loop with validation retries, structured output, baton |
| `execution/chain/runner.py` | ~400 | Chain executor for parallel swarm orchestration |
| `storage/protocols.py` | ~500 | Protocol interfaces for all stores |
| `storage/db/schema.py` | ~890 | SQLite schema v35, 40+ tables, FTS5 |
| `storage/db/connection.py` | ~300 | PixlDB — SQLite WAL, thread-local connections |
| `models/workflow.py` | ~400 | WorkflowTemplate, ExecutionGraph, Node, Edge |
| `models/session.py` | ~250 | WorkflowSession, ExecutorCursor, NodeInstance |
| `models/baton.py` | ~200 | Inter-stage context relay |
| `models/feature.py` | ~150 | Feature model with status, deps, metrics |
| `providers/registry.py` | ~100 | Multi-provider LLM support |

### CLI (`packages/cli/pixl_cli/`)

| File | Lines | Role |
|------|-------|------|
| `main.py` | ~150 | Click entry point, global flags |
| `context.py` | ~100 | CLIContext — project resolution, storage initialization |
| `sandbox_client.py` | ~200 | HTTP bridge to Cloudflare sandbox API |
| `commands/workflow.py` | ~200 | Workflow execution command |
| `commands/sandbox.py` | ~300 | Sandbox lifecycle commands |
| `crew.py` | ~50 | Crew root resolution |

### Sandbox (`packages/sandbox/`)

| File | Lines | Role |
|------|-------|------|
| `src/router.ts` | ~500 | Hono REST API with all endpoints |
| `src/helpers.ts` | ~150 | Version detection, env building, path validation |
| `src/usage.ts` | ~80 | Operation logging and aggregation |
| `src/types.ts` | ~50 | TypeScript interfaces |
| `docker/Dockerfile` | ~60 | Container image definition |
| `docker/init.sh` | ~40 | Init script (git + pixl init + pixl setup) |

### Crew (`packages/crew/`)

| File | Lines | Role |
|------|-------|------|
| `.claude-plugin/plugin.json` | ~30 | Plugin manifest |
| `agents/*.md` | ~100 each | Agent definitions (14 files) |
| `hooks/hooks.json` | ~150 | Hook system configuration |
| `skills/ROUTING.md` | ~200 | Skill routing decision tree |
| `skills/*/SKILL.md` | ~50-500 each | Skill definitions (70+ files) |

---

## 9. Future Work (Deferred)

The following are identified as needed but **not planned for implementation now**:

### API Layer
- FastAPI application factory with CORS, error handling
- JWT authentication (bcrypt + pyjwt — already in `[api]` extra deps)
- REST endpoints for all domains (projects, backlog, sessions, events, artifacts, workflows, sandboxes, analytics)
- WebSocket endpoint for real-time event streaming
- Redis for event pub/sub and caching (already in `[api]` extra deps)
- OpenAPI spec auto-generation
- CLI command: `pixl api serve`

### Frontend / Dashboard
- Project overview dashboard
- Execution graph visualizer (render DAG with node states)
- Real-time session monitoring (via WebSocket)
- Backlog management (roadmap → epic → feature CRUD)
- Cost analytics dashboard (per model, per agent, per session)
- Sandbox management UI
- Artifact browser with FTS search

### PostgreSQL Adapter
- Implement `StorageBackend` protocol with PostgreSQL
- Connection pooling, migrations, multi-tenant isolation
- The protocol abstraction at `protocols.py` is designed for this — zero call-site changes needed

### Artifact Cloud Storage
- S3/R2 backend for large artifacts (code, documents, images)
- Streaming upload/download
- Content-addressed deduplication (content_hash already tracked)

---

## 10. SDK Integration Solutions (Per Official Doc)

> Core principle: **Claude Code is the main tool on the SDK**. The pixl engine, CLI, and crew plugin sit on top to ensure DAG workflows are orchestrated, skills/agents are loaded, and the per-project SQLite DB traces everything.
>
> Each subsection maps to one official SDK doc link, shows what pixl does today, and defines the concrete solution.

---

### 10.1 Hosting

> Doc: https://platform.claude.com/docs/en/agent-sdk/hosting

**SDK Doc Says**:
- Use `ClaudeSDKClient` for persistent connections that survive multiple queries
- Manage client lifecycle (connect, query, disconnect)
- Support concurrent queries with thread safety
- Track session IDs for resume capability

**Pixl Today** (Working):
- `OrchestratorCore` at `packages/engine/pixl/orchestration/core.py:98` maintains persistent SDK clients keyed by `(agent_name, resolved_model)`
- Client lifecycle managed via `_get_or_create_client()` (line 107) and `cleanup_sdk_clients()` (line 139)
- `ConcurrencyManager` handles thread-pool rate limiting per provider
- Tool sets locked at client creation to prevent runtime drift (line 118)
- Circuit breaker at 5 consecutive unrecoverable API errors (line 43)
- SDK query timeout configurable via `PIXL_SDK_QUERY_TIMEOUT` env var (default 600s)

**Status**: Fully aligned with SDK docs. No changes needed.

**DB Trace**:
- `heartbeat_runs` table: records each SDK query invocation with `input_tokens`, `output_tokens`, `cost_usd`, `steps_executed`
- `task_sessions` table: persists SDK session IDs (`adapter_session_id`) per node for resume
- `cost_events` table: per-query cost tracking with `adapter_name`, `model_name`

---

### 10.2 Plugins

> Doc: https://platform.claude.com/docs/en/agent-sdk/plugins

**SDK Doc Says**:
- Load plugins via `options.plugins = [{"type": "local", "path": "./my-plugin"}]`
- Plugins add skills, agents, hooks, and MCP servers to agent sessions
- Plugin skills are namespaced: `plugin-name:skill-name`
- Verify plugin loaded via `system.init` message's `plugins` field
- Path can be relative or absolute

**Pixl Today** (GAP-01):
- Crew plugin registered via `pixl setup` → writes to `~/.claude/plugins/installed_plugins.json`
- `build_sdk_options()` at `sdk_options.py:161` does **not** pass `plugins` parameter
- Crew root resolved via `pixl_cli/crew.py:get_crew_root()` with fallback chain: `PIXL_CREW_ROOT` env → monorepo `packages/crew/` → bundled `_crew/`
- In sandbox, `init.sh` runs `pixl setup` inside container to register crew

**Solution**:

```python
# In packages/engine/pixl/agents/sdk_options.py

def _resolve_crew_plugin_path() -> str | None:
    """Resolve crew plugin path for programmatic loading."""
    # 1. Env override
    env_root = os.environ.get("PIXL_CREW_ROOT")
    if env_root and Path(env_root).is_dir():
        return env_root

    # 2. Monorepo layout (engine is sibling of crew)
    engine_dir = Path(__file__).resolve().parent.parent.parent  # packages/engine/
    crew_dir = engine_dir.parent / "crew"
    if (crew_dir / ".claude-plugin" / "plugin.json").exists():
        return str(crew_dir)

    # 3. Bundled in wheel
    bundled = Path(__file__).parent.parent / "_crew"
    if (bundled / ".claude-plugin" / "plugin.json").exists():
        return str(bundled)

    return None

def build_sdk_options(..., load_crew_plugin: bool = True) -> ClaudeAgentOptions:
    # ... existing code ...

    plugins = []
    if load_crew_plugin:
        crew_path = _resolve_crew_plugin_path()
        if crew_path:
            plugins.append({"type": "local", "path": crew_path})

    options = ClaudeAgentOptions(
        allowed_tools=allowed_tools,
        permission_mode="bypassPermissions",
        cwd=str(cwd or project_path),
        max_turns=max_turns,
        hooks=hooks if hooks else None,
        setting_sources=["user", "project"],
        agents=agents,
        plugins=plugins if plugins else None,  # NEW
        extra_args={"debug-to-stderr": None},
    )
```

**Files to modify**: `packages/engine/pixl/agents/sdk_options.py`

**DB Trace**:
- No new tables needed. Plugin loading is a runtime concern.
- Crew skills invoked during workflows are already tracked via `events` table (event_type captures tool usage including Skill invocations)

---

### 10.3 Skills

> Doc: https://platform.claude.com/docs/en/agent-sdk/skills

**SDK Doc Says**:
- Skills are `SKILL.md` files in `.claude/skills/` or plugin `skills/` directories
- Must set `settingSources: ["user", "project"]` to load skills from filesystem
- Must include `"Skill"` in `allowed_tools`
- Claude autonomously invokes skills based on description matching
- `allowed-tools` frontmatter in SKILL.md does **NOT** apply in SDK mode — tool access controlled via `allowedTools` option
- Skills from plugins auto-namespaced: `plugin-name:skill-name`

**Pixl Today** (Mostly Working):
- `build_sdk_options()` sets `setting_sources=["user", "project"]` — skills from `.claude/skills/` are loaded
- `DEFAULT_TOOLS` at `agents/constants.py` includes `"Skill"`
- Crew has 70+ skills in `packages/crew/skills/*/SKILL.md`
- **Gap**: Crew skills only available if plugin is loaded (depends on GAP-01 fix)
- **Gap**: `allowed-tools` frontmatter in SKILL.md is ignored by SDK — but the engine uses `bypassPermissions` so all tools available anyway

**Solution**:
- Once GAP-01 (plugin loading) is fixed, crew skills will be auto-discovered and namespaced as `pixl-crew:skill-name`
- The engine's `TaskConfig` on each workflow node can specify required skills — add skill hints to the prompt so Claude knows which skills to invoke
- For per-node tool restrictions (future): use `allowed_tools` per query call instead of global bypass

```python
# In TaskExecutor, when building the prompt for a node:
def _build_task_prompt(self, node, baton, feature):
    prompt = ...
    # If node config specifies skills, hint them
    if node.task_config and node.task_config.skills:
        skill_hints = ", ".join(f"/pixl-crew:{s}" for s in node.task_config.skills)
        prompt += f"\n\nAvailable skills for this task: {skill_hints}"
    return prompt
```

**Files to modify**:
- `packages/engine/pixl/agents/sdk_options.py` (GAP-01 fix enables this)
- `packages/engine/pixl/execution/task_executor.py` (skill hints in prompts)

**DB Trace**:
- Skill invocations logged in `events` table with `event_type='tool_use'` and `payload_json` containing skill name
- The `track-skill-invocation.sh` crew hook already tracks skill usage — once bridged (GAP-03), this data flows into the DB

---

### 10.4 Slash Commands

> Doc: https://platform.claude.com/docs/en/agent-sdk/slash-commands

**SDK Doc Says**:
- Send slash commands by including them in the prompt string: `prompt="/compact"`
- `/compact` reduces conversation history by summarizing older messages
- `/clear` starts a fresh conversation
- Custom commands from `.claude/commands/` or plugin `skills/` directories
- Commands appear in `system.init` message's `slash_commands` field

**Pixl Today** (Not Used):
- The engine never sends slash commands programmatically
- Long-running workflows accumulate context across nodes but never compact
- Each node in the DAG gets a fresh prompt built by `PromptBuilder`, but the underlying SDK session may accumulate tool results

**Solution**:
- Use `/compact` between workflow nodes when context is getting large
- Use `/clear` when switching between fundamentally different tasks in a chain

```python
# In GraphExecutor, between node executions:
async def _maybe_compact_session(self, session, node_count):
    """Send /compact if session has accumulated many nodes."""
    if node_count > 0 and node_count % 5 == 0:  # Every 5 nodes
        # The SDK handles /compact internally when sent as prompt
        await self.orchestrator.query_with_streaming(
            prompt="/compact",
            model=self.default_model,
            max_turns=1,
        )
        self._emit_event(Event(
            event_type=EventType.CONTEXT_COMPACT,
            session_id=session.id,
            payload={"trigger": "auto", "node_count": node_count},
        ))
```

**Files to modify**:
- `packages/engine/pixl/execution/graph_executor.py` (auto-compact logic)
- `packages/engine/pixl/models/event.py` (add `CONTEXT_COMPACT` event type if missing)

**DB Trace**:
- Compact events recorded in `events` table with `event_type='context_compact'`
- The `pre-compact.sh` crew hook preserves session state before compaction — once bridged, this triggers automatically

---

### 10.5 Subagents

> Doc: https://platform.claude.com/docs/en/agent-sdk/subagents

**SDK Doc Says**:
- Define subagents via `agents` parameter: `{"name": AgentDefinition(description=..., prompt=..., tools=[...], model="sonnet")}`
- Each subagent runs in its own fresh conversation (context isolation)
- Subagents can run in parallel for speedup
- Claude auto-delegates based on `description` field, or explicit: "Use the code-reviewer agent to..."
- Subagent tool restrictions via `tools` field
- Subagents cannot spawn their own subagents (no `Agent` in tools)
- Subagent transcripts persist independently of main conversation
- Resume subagents via `agent_id` from tool result

**Pixl Today** (GAP-02):
- `build_sdk_options()` accepts `agents` parameter but it's never populated from crew
- Crew defines 14 agents in `packages/crew/agents/*.md` with YAML frontmatter: `name`, `description`, `model`, `tools`, `skills`, `maxTurns`, `memory`, `color`
- When crew plugin is loaded via filesystem, these agents are available via Claude Code's semantic matching
- But the engine has no way to programmatically select agents per workflow node

**Solution** — Build `AgentRegistry`:

```python
# New file: packages/engine/pixl/agents/registry.py

import re
from pathlib import Path
from dataclasses import dataclass
from claude_agent_sdk import AgentDefinition

@dataclass
class CrewAgent:
    name: str
    description: str
    prompt: str  # Body of the markdown (system prompt)
    model: str   # opus, sonnet, haiku, inherit
    tools: list[str] | None
    skills: list[str]
    max_turns: int

class AgentRegistry:
    def __init__(self):
        self._agents: dict[str, CrewAgent] = {}

    def load_from_crew(self, crew_root: Path) -> None:
        """Parse all agent markdown files from crew/agents/."""
        agents_dir = crew_root / "agents"
        if not agents_dir.is_dir():
            return
        for md_file in sorted(agents_dir.glob("*.md")):
            agent = self._parse_agent_md(md_file)
            if agent:
                self._agents[agent.name] = agent

    def _parse_agent_md(self, path: Path) -> CrewAgent | None:
        """Parse YAML frontmatter + body from agent markdown."""
        text = path.read_text()
        match = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
        if not match:
            return None
        import yaml
        meta = yaml.safe_load(match.group(1))
        body = match.group(2).strip()
        return CrewAgent(
            name=meta["name"],
            description=meta.get("description", ""),
            prompt=body,
            model=meta.get("model", "inherit"),
            tools=meta.get("tools"),
            skills=meta.get("skills", []),
            max_turns=meta.get("maxTurns", 50),
        )

    def get_agent_definition(self, name: str, parent_model: str = "claude-sonnet-4-6") -> AgentDefinition | None:
        """Convert a CrewAgent to an SDK AgentDefinition."""
        agent = self._agents.get(name)
        if not agent:
            return None
        model = agent.model if agent.model != "inherit" else None
        tools = agent.tools  # None = inherit all
        if tools and "Agent" in tools:
            tools = [t for t in tools if t != "Agent"]  # Subagents can't spawn subagents
        return AgentDefinition(
            description=agent.description,
            prompt=agent.prompt,
            tools=tools,
            model=model,
        )

    def get_all_definitions(self, parent_model: str = "claude-sonnet-4-6") -> dict[str, AgentDefinition]:
        """Get all agents as SDK AgentDefinitions."""
        result = {}
        for name in self._agents:
            defn = self.get_agent_definition(name, parent_model)
            if defn:
                result[name] = defn
        return result

    def list_agents(self) -> list[str]:
        return list(self._agents.keys())
```

Then wire into `build_sdk_options()`:

```python
# In sdk_options.py
def build_sdk_options(
    ...,
    agent_registry: AgentRegistry | None = None,
    load_all_agents: bool = False,
) -> ClaudeAgentOptions:
    # Resolve agents from registry if provided
    agents_dict = agents  # Explicit agents take precedence
    if agent_registry and load_all_agents and not agents_dict:
        agents_dict = agent_registry.get_all_definitions()

    options = ClaudeAgentOptions(
        ...,
        agents=agents_dict,
    )
```

And in `OrchestratorCore.__init__()`:

```python
# In core.py
from pixl.agents.registry import AgentRegistry

class OrchestratorCore:
    def __init__(self, project_path: Path) -> None:
        ...
        self.agent_registry = AgentRegistry()
        crew_path = _resolve_crew_plugin_path()
        if crew_path:
            self.agent_registry.load_from_crew(Path(crew_path))
```

**Files**:
- New: `packages/engine/pixl/agents/registry.py`
- Modify: `packages/engine/pixl/agents/sdk_options.py`
- Modify: `packages/engine/pixl/orchestration/core.py`

**DB Trace**:
- `agent_metrics` table: tracks per-agent performance (`agent_name`, `model_name`, `success`, `error_type`, `input_tokens`, `output_tokens`, `total_cost_usd`)
- `node_instances` table: records which `agent_name` and `model_name` executed each node
- `autonomy_profiles` table: tracks agent confidence per task type

---

### 10.6 Structured Output

> Doc: https://platform.claude.com/docs/en/agent-sdk/structured-outputs

**SDK Doc Says**:
- Define output shape via `outputFormat: {"type": "json_schema", "schema": {...}}`
- Use Pydantic `.model_json_schema()` to generate schema from models
- Validate result via `FeaturePlan.model_validate(message.structured_output)`
- Agent uses tools freely, then produces validated JSON at the end
- Handle `error_max_structured_output_retries` on failure

**Pixl Today** (Working, could improve):
- `build_sdk_options()` forwards `output_format` parameter at `sdk_options.py:192`
- `TaskExecutor` uses `output_format` with contract-defined JSON schemas
- `ContractValidator` validates structured output against node contracts
- On validation failure, generates repair prompt and retries (up to `max_attempts`)
- Cost estimation per model tracked on each attempt

**Solution** — Use Pydantic models directly:

```python
# In task_executor.py, when building output_format:
from pixl.models.stage_output import StageOutput

def _build_output_format(self, node) -> dict | None:
    """Build output_format from Pydantic model if available."""
    if node.task_config and node.task_config.output_model:
        # Use the Pydantic model's schema directly
        return {
            "type": "json_schema",
            "schema": node.task_config.output_model.model_json_schema(),
        }
    # Fall back to existing contract-based schema
    return self._build_contract_schema(node)
```

And validate the result:

```python
# After receiving structured_output from SDK:
if result.structured_output and node.task_config.output_model:
    validated = node.task_config.output_model.model_validate(result.structured_output)
    # Store as typed object, not raw dict
```

**Files to modify**: `packages/engine/pixl/execution/task_executor.py`

**DB Trace**:
- Structured output stored in `node_instances.output_json` (already working)
- Validation failures tracked in `incidents` table with `error_type='contract_violation'`
- Retry attempts tracked via `node_instances.attempt` counter

---

### 10.7 Hooks

> Doc: https://platform.claude.com/docs/en/agent-sdk/hooks

**SDK Doc Says**:
- Register Python callback hooks via `ClaudeAgentOptions(hooks={...})`
- Hook events: `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `Stop`, `SubagentStart`, `SubagentStop`, `PreCompact`, `Notification`, `PermissionRequest`, `UserPromptSubmit`
- Callbacks receive `(input_data, tool_use_id, context)`, return `{hookSpecificOutput: {...}}`
- `permissionDecision`: `"allow"`, `"deny"`, or `"ask"`
- `updatedInput`: modify tool input before execution
- `systemMessage`: inject context into conversation
- Matchers: regex patterns against tool names (e.g., `"Write|Edit"`, `"^mcp__"`)
- Async hooks: return `{"async": True}` for fire-and-forget (logging, telemetry)
- Multiple hooks chain in order; `deny` overrides `allow`

**Pixl Today** (GAP-03 — Partial):
- Engine registers safety hooks only (`sdk_options.py:142-159`): tool budget, context window, output truncation
- Crew defines 15+ shell script hooks in `hooks/hooks.json`: block-destructive, detect-secrets, tdd-check, quality-gate, enforce-skill-first, observe-patterns, cost-tracker, validate-agent-selection
- Shell hooks only fire in interactive Claude Code sessions, not in engine-driven workflows

**Solution** — Bridge crew hooks to SDK callbacks:

```python
# New file: packages/engine/pixl/agents/hooks/crew_bridge.py

import asyncio
import subprocess
import json
import os
from pathlib import Path
from claude_agent_sdk import HookCallback, HookMatcher

async def _run_shell_hook(script_path: str, input_data: dict) -> dict:
    """Execute a crew shell hook and parse its JSON output."""
    env = {**os.environ, "HOOK_INPUT": json.dumps(input_data)}
    proc = await asyncio.to_thread(
        subprocess.run,
        ["bash", script_path],
        capture_output=True, text=True, timeout=30, env=env,
    )
    if proc.returncode == 0 and proc.stdout.strip():
        try:
            return json.loads(proc.stdout.strip())
        except json.JSONDecodeError:
            pass
    return {}

def create_crew_hook(script_path: str) -> HookCallback:
    """Create an SDK HookCallback that delegates to a crew shell script."""
    async def hook(input_data, tool_use_id, context):
        return await _run_shell_hook(script_path, input_data)
    return hook

def load_crew_hooks(crew_root: Path, profile: str = "standard") -> dict:
    """Load crew hooks.json and build SDK hook matchers."""
    hooks_json = crew_root / "hooks" / "hooks.json"
    if not hooks_json.exists():
        return {}

    config = json.loads(hooks_json.read_text())
    sdk_hooks = {}

    for event_name, entries in config.items():
        if event_name not in ("PreToolUse", "PostToolUse", "Stop", "Notification"):
            continue
        matchers = []
        for entry in entries:
            script = entry.get("command", "")
            if not script:
                continue
            # Resolve script path
            script_path = crew_root / "hooks" / "scripts" / script
            if not script_path.exists():
                continue
            # Check profile
            hook_profile = entry.get("profile", "standard")
            if _profile_rank(hook_profile) > _profile_rank(profile):
                continue
            callback = create_crew_hook(str(script_path))
            matcher = entry.get("matcher")
            matchers.append(HookMatcher(matcher=matcher, hooks=[callback]))

        if matchers:
            sdk_hooks[event_name] = matchers

    return sdk_hooks

def _profile_rank(profile: str) -> int:
    return {"minimal": 0, "standard": 1, "strict": 2}.get(profile, 1)
```

Then wire into `build_sdk_options()`:

```python
# In sdk_options.py
def build_sdk_options(..., crew_hook_profile: str = "standard") -> ClaudeAgentOptions:
    hooks = {}
    # Safety hooks (existing)
    if enable_safety_hooks and _HOOKS_AVAILABLE:
        hooks = create_sdk_hooks_from_registry(create_default_registry())

    # Crew hooks (NEW)
    crew_path = _resolve_crew_plugin_path()
    if crew_path:
        from pixl.agents.hooks.crew_bridge import load_crew_hooks
        crew_hooks = load_crew_hooks(Path(crew_path), profile=crew_hook_profile)
        for event, matchers in crew_hooks.items():
            existing = hooks.get(event, [])
            hooks[event] = existing + matchers
```

**Files**:
- New: `packages/engine/pixl/agents/hooks/crew_bridge.py`
- Modify: `packages/engine/pixl/agents/sdk_options.py`

**DB Trace**:
- Hook executions logged via `events` table when they modify behavior (deny, updatedInput)
- `cost-tracker.sh` hook feeds into `cost_events` table
- `observe-patterns.sh` hook feeds into `.claude/memory/instincts.jsonl` (crew memory) or `config` table (pixl DB)
- `block-destructive.sh` denials logged as `incidents` with `error_type='hook_denied'`

---

### 10.8 Cost Tracking

> Doc: https://platform.claude.com/docs/en/agent-sdk/cost-tracking

**SDK Doc Says**:
- `ResultMessage` includes `total_cost_usd` and cumulative `usage` dict
- Each `query()` call reports its own cost independently
- `usage` includes: `input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`
- Accumulate costs across multiple calls yourself
- TypeScript SDK also provides per-model breakdown via `modelUsage` (not available in Python)

**Pixl Today** (Working):
- `TaskExecutor` reads `result.total_cost_usd` from SDK `ResultMessage`
- Costs stored in `cost_events` table: `session_id`, `run_id`, `node_id`, `adapter_name`, `model_name`, `input_tokens`, `output_tokens`, `cost_usd`
- `heartbeat_runs` table tracks per-invocation costs
- `agent_metrics` table aggregates per-agent costs
- Per-model pricing defined in `providers/registry.py`

**Solution** — Ensure full SDK cost data is captured:

```python
# In task_executor.py, after receiving result:
async def _record_cost(self, result, session_id, node_id, model_name, agent_name):
    """Capture full SDK cost data into per-project DB."""
    usage = getattr(result, "usage", {}) or {}
    self.storage.cost_events.record(
        session_id=session_id,
        node_id=node_id,
        model_name=model_name,
        agent_name=agent_name,
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        cache_read_tokens=usage.get("cache_read_input_tokens", 0),   # NEW
        cache_creation_tokens=usage.get("cache_creation_input_tokens", 0),  # NEW
        cost_usd=result.total_cost_usd or 0.0,
    )
```

Schema change to capture cache tokens:

```sql
-- Add to cost_events table
ALTER TABLE cost_events ADD COLUMN cache_read_tokens INTEGER DEFAULT 0;
ALTER TABLE cost_events ADD COLUMN cache_creation_tokens INTEGER DEFAULT 0;
```

**Files to modify**:
- `packages/engine/pixl/execution/task_executor.py` (capture cache tokens)
- `packages/engine/pixl/storage/db/schema.py` (add cache token columns)
- `packages/engine/pixl/storage/db/cost_events.py` (update record method)

**DB Trace**:
- `cost_events` table: now includes `cache_read_tokens` and `cache_creation_tokens` for full SDK parity
- Per-session cost: `SELECT SUM(cost_usd) FROM cost_events WHERE session_id = ?`
- Per-model cost: `SELECT model_name, SUM(cost_usd), SUM(input_tokens), SUM(output_tokens) FROM cost_events GROUP BY model_name`
- Per-agent cost: `SELECT agent_name, SUM(cost_usd) FROM cost_events JOIN agent_metrics ... GROUP BY agent_name`
- Cache savings: `SELECT SUM(cache_read_tokens) * price_per_token_saved FROM cost_events`

---

### 10.9 Todo Tracking

> Doc: https://platform.claude.com/docs/en/agent-sdk/todo-tracking

**SDK Doc Says**:
- SDK automatically creates todos for complex multi-step tasks (3+ actions)
- `TodoWrite` tool updates: `pending` → `in_progress` → `completed`
- Monitor via `tool_use` blocks where `block.name == "TodoWrite"`
- Each todo has: `content`, `status`, `activeForm` (verb for in-progress display)
- Todos removed when all tasks in a group complete

**Pixl Today** (Not Used):
- Engine has its own task tracking via `NodeInstance` states: `task_pending` → `task_running` → `task_completed` / `task_failed`
- Feature-level tracking: `backlog` → `planned` → `in_progress` → `review` → `done`
- These are more granular than SDK todos but exist in a different system

**Solution** — Mirror TodoWrite to engine state via PostToolUse hook:

```python
# In packages/engine/pixl/agents/hooks/todo_bridge.py

from claude_agent_sdk import HookCallback, HookMatcher

def create_todo_tracking_hook(session_store, session_id: str) -> HookCallback:
    """Mirror SDK TodoWrite updates to engine NodeInstance states."""
    async def hook(input_data, tool_use_id, context):
        if input_data.get("hook_event_name") != "PostToolUse":
            return {}
        if input_data.get("tool_name") != "TodoWrite":
            return {}

        # Extract todo updates from tool input
        todos = input_data.get("tool_input", {}).get("todos", [])
        for todo in todos:
            # Log todo state change as an event
            # This creates a parallel trace in the per-project DB
            pass

        # Return async — don't block the agent
        return {"async_": True}

    return hook
```

For now this is **P3** — the engine's `NodeInstance` tracking is more sophisticated than SDK todos. The main value is UX-visible progress in Claude Code's interface, which already works when workflows run inside Claude Code.

**DB Trace**:
- `node_instances` table already tracks: `state` (task_pending/running/completed/failed), `started_at`, `ended_at`, `attempt`
- Todo states could be logged in `events` table with `event_type='todo_update'` for audit
- No new tables needed — engine tracking is superior to SDK todos

---

### 10.10 Per-Project DB — The Unifying Layer

All SDK features above feed into a single per-project SQLite database at `{project}/.pixl/pixl.db`. This is the **trace of everything**:

```
Per-Project DB (.pixl/pixl.db)
│
├── Planning trace
│   ├── roadmaps, epics, features (what was planned)
│   ├── state_transitions (every status change with trigger)
│   └── notes (decisions, context)
│
├── Execution trace
│   ├── workflow_sessions (each run with cursor checkpoint)
│   ├── node_instances (per-node state, agent, model, tokens, cost)
│   ├── events (every event: tool use, state change, error, compact)
│   └── loop_states (iteration tracking for loops)
│
├── Agent trace
│   ├── agent_metrics (per-agent performance)
│   ├── autonomy_profiles (confidence per task type)
│   ├── autonomy_outcomes (auto-approved vs manual gates)
│   └── task_sessions (SDK session IDs for resume)
│
├── Cost trace
│   ├── cost_events (per-query: model, tokens, cache, cost_usd)
│   ├── heartbeat_runs (per-invocation windows)
│   └── quality_scores (swarm quality metrics)
│
├── Artifact trace
│   ├── artifacts (versioned, content-hashed, typed)
│   ├── artifact_chunks (large artifact storage)
│   └── artifacts_fts (full-text search)
│
├── Knowledge trace
│   ├── documents, chunks (AST-indexed code)
│   ├── chunks_fts (semantic search)
│   └── knowledge_manifest (build metadata)
│
├── Recovery trace
│   ├── incidents (errors, recovery actions, outcomes)
│   └── incidents_fts (searchable error history)
│
├── Chain/Swarm trace
│   ├── execution_chains, chain_nodes, chain_edges (parallel work)
│   ├── chain_signals (inter-agent communication)
│   └── chain_signals_fts (searchable signals)
│
└── Sandbox trace
    ├── sandbox_projects (tracked sandboxes)
    └── sandbox_operations (operation audit log)
```

**Every SDK interaction** (query, cost, hook decision, structured output, todo update) is recorded in this DB. When the future API layer is built, it simply reads from this DB to serve dashboards, analytics, and execution history.

# pixl-engine

DAG orchestration engine — workflow execution, LLM providers, SQLite storage.

## Structure

```
pixl/
├── models/             # Pydantic v2 domain models (Baton, ExecutionGraph, ExecutorCursor, etc.)
├── execution/          # Core execution: GraphExecutor, TaskExecutor, ContractValidator
│   ├── chain/          # ChainRunner for epic orchestration
│   ├── hooks/          # Stage-specific hooks (chain plan hooks)
│   ├── recovery/       # Recovery-specific logic
│   └── validation/     # Contract validation core
├── storage/            # Ports & adapters (Protocol interfaces)
│   └── db/             # SQLite implementation (WAL, FTS5, schema v37, 40+ tables)
├── orchestration/      # OrchestratorCore, concurrency, background managers
├── providers/          # Multi-LLM: Anthropic (SDK), OpenAI/Codex, Gemini
├── state/              # State machine: TransitionEngine, Guards, Effects
├── recovery/           # Incident store, recovery policy, auto-repair workflows
├── context/            # Budget-aware prompt assembly (UnifiedCompiler)
├── agents/             # AgentRegistry (parses crew markdown → SDK AgentDefinition)
├── config/             # Workflow loader, provider config resolution
├── knowledge/          # tree-sitter AST chunking, FTS5 search
├── events/             # EventBus (in-process pub/sub)
├── session/            # SessionManager (lifecycle: create, resume, cleanup)
├── routing/            # LLM-powered prompt classification
├── assets/             # Built-in YAML workflows, prompts, JSON schemas
└── utils/, loaders/, projects/, output/
tests/                  # pytest, ~50 test modules
```

## Key Invariants

- **Baton is a relay, not a store** — flows between stages carrying goal, state, decisions, constraints. Agents update via `baton_patch` (JSON merge patch), never direct mutation
- **ExecutorCursor must be serializable** — maintains sorted `ready_queue` for deterministic resumption. `last_event_id` enables precise replay
- **SessionStatus is DERIVED** — computed from `node_instances` at runtime, never stored directly
- **Protocol-based storage** — all stores are duck-typed interfaces in `storage/protocols.py`. Import protocols, never concrete implementations in domain code
- **Schema v37** — adding tables requires bumping `SCHEMA_VERSION` in `storage/db/schema.py`
- **Events are append-only** — complete audit trail, no updates or deletes
- **Guard/Effect separation** — Guards check preconditions (can block), Effects execute post-transition actions (cannot block)

## Execution Pipeline

```
WorkflowTemplate → WorkflowSnapshot (immutable)
                 → WorkflowSession (runtime state)
                 → GraphExecutor (DAG step loop)
                   → ready_queue → execute node → emit event → follow edges → update cursor → persist
                 → ChainRunnerManager (epic orchestration, one thread per chain)
                 → TaskExecutor (SDK query + validation retries + baton patching)
                 → OrchestratorCore (provider delegation, streaming, SDK client cache)
```

Node types: `TASK`, `GATE`, `HOOK`, `SUB_WORKFLOW`
Edge triggers: `SUCCESS`, `FAILURE`, `ALWAYS`, `CONDITION`

## Storage Protocols

Defined in `storage/protocols.py` — never import concrete `db/` classes in domain code:

- **BacklogStore** — roadmap → epic → feature hierarchy with dependency DAG
- **SessionStore** — workflow execution state, node instances, loop states
- **ArtifactStore** — versioned outputs with FTS5 semantic search
- **EventStore** — append-only audit log with transition tracking
- **KnowledgeStore** — FTS5 full-text search for RAG, chunked documents
- **StorageBackend** — top-level interface combining all stores

## Provider Architecture

**ProviderRegistry** resolves model strings to backends:
- `"anthropic/opus"` → AnthropicProvider + `claude-opus-4-6`
- `"opus"` → default provider (Anthropic) + resolved alias
- `"codex/gpt-5.2"` → CodexProvider (OpenAI)
- `"gemini/2.5-pro"` → GeminiProvider (Google)

Config resolution: `.pixl/providers.yaml` → `~/.pixl/projects/[PROJECT]/providers.yaml` → `~/.pixl/providers.yaml` → bundled defaults

## Recovery Subsystem

Pure-function policy in `recovery/policy.py` — no I/O in decision logic:

| Action | When |
|--------|------|
| `RETRY` | Transient errors, exponential backoff with jitter |
| `FAIL_FAST` | Terminal errors, no recovery possible |
| `FAILOVER` | Provider unavailable, switch backend |
| `CONTRACT_REPAIR` | Output failed validation, auto-fix via LLM |
| `PATCH_AND_TEST` | Code output broken, auto-patch + test |
| `REQUIRE_HUMAN` | Unrecoverable, pause for user |

IncidentStore biases future decisions based on historical patterns.

## Context Assembly (UnifiedCompiler)

Budget-aware prompt construction in `context/unified_compiler.py`:

1. Base prompt (template resolver)
2. Baton context (goal, state, decisions, constraints)
3. Stage contract summary
4. Predecessor outputs
5. Artifact handoff manifest + required/frozen artifacts (budget-gated)
6. Session state
7. Output schema (JSON schema for constrained decoding)

Token budgets: Haiku 32K, Sonnet 64K, Opus 128K.

## State Machine

`state/engine.py` — TransitionEngine for all status changes:
- Validates transition legality → runs Guards (preconditions) → persists → runs Effects (side effects)
- Guards return `HARD` (blocks) or `SOFT` (warns)
- Effects: timestamps, event emission, dependent entity updates

Session: `CREATED → RUNNING → (PAUSED | STALLED | FAILED | COMPLETED | CANCELLED)`
Node: `PENDING → RUNNING → SUCCESS | FAILED | RETRYING | REJECTED | HUMAN_PAUSED`
Staleness: heartbeat_at > 60s with no active nodes → STALLED

## Large Files

Always use `offset`/`limit` when reading these:

| File | Lines | What it does |
|------|-------|---|
| `execution/graph_executor.py` | 2,018 | Core DAG step loop |
| `execution/contract_validator.py` | 1,457 | Output quality gates (git diffs, linting) |
| `storage/workflow_session_store.py` | 1,313 | Session persistence |
| `storage/db/projections.py` | 1,171 | Materialized view queries |
| `execution/recovery_handler.py` | 1,152 | Error recovery routing |
| `execution/task_executor.py` | 1,070 | SDK query pipeline |
| `storage/db/schema.py` | 1,005 | SQLite DDL (40+ tables, v37) |
| `execution/validation/core.py` | 987 | Output schema validation |
| `execution/prompt_builder.py` | 964 | Template resolution |

## Testing

```bash
make test-engine                    # all engine tests
uv run pytest packages/engine/tests/ -x  # with early exit
uv run pytest packages/engine/tests/test_state_machine.py  # single file
```

- **conftest.py**: `_isolate_global_pixl` autouse fixture redirects `~/.pixl/` to temp dir
- Tests cover: contract validation, simulated execution, state machines, chain orchestration, providers, cost events, workflow harness
- Largest test files: `test_contract_validation.py`, `test_chain_and_utils.py` — use offset/limit

## Code Patterns

- `from __future__ import annotations` in all files
- Union syntax: `X | Y` (not `Union[X, Y]`)
- `TYPE_CHECKING` guards for circular imports
- Absolute imports: `from pixl.models.session import WorkflowSession`
- Pydantic `BaseModel` for validated domain models
- `@dataclass(frozen=True)` for immutable results (GuardResult, EffectResult)
- Typed errors: `PixlError` base with `ContractError`, `ProviderError`, `StateError`, `StorageError`, `TimeoutError`
- `raise ... from err` for exception chaining

## Dependencies

Core (always installed): pydantic, claude-agent-sdk, anthropic, openai, httpx, pyyaml, rich
Optional `[api]` extra: fastapi, redis, bcrypt, pyjwt
Knowledge: tree-sitter (AST chunking)
Testing: pytest, pytest-asyncio

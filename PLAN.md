# CTO Review — pixl Engine

> **Archive** — This CTO review was conducted 2026-03-24. Phases S1 (EventEmitter),
> S2 (ArtifactResolver), S3 (reschedule_node), and god function decomposition
> (extract_stage_output, run_validation_pass, build_execution_result) are complete.
> Remaining items (A1, B1, D1-D3) are deferred.

## Current State

| Metric | Value |
|--------|-------|
| Production files | 224 |
| Production LOC | 56,067 |
| Test coverage | 23.22% |
| God files (>1000 LOC) | 6 |
| God functions (>400 LOC) | 0 |
| Data flow clarity score | 7/10 |

### God Files

| File | LOC | Purpose |
|------|-----|---------|
| `execution/graph_executor.py` | 2133 | DAG step algorithm, cursor management, edge traversal |
| `execution/contract_validator.py` | 1457 | Output validation, stub detection, repair |
| `storage/workflow_session_store.py` | 1313 | Session CRUD, filesystem + DB, projections |
| `storage/db/projections.py` | 1171 | Reporting aggregations, timeline, burndown |
| `execution/recovery_handler.py` | 1161 | Error recovery, retry logic, contract repair |
| `storage/db/schema.py` | 1005 | DDL for 40+ tables (unavoidably large) |

### Headline Problems

1. **graph_executor.py at 2133 LOC** — 54 functions doing too many things (execution, event emission, artifact management, contract validation, session persistence)
2. **Recovery logic duplicated** — `recovery_handler.py` and `recovery/contract_repair.py` and `recovery/patch_and_test.py` all access `executor_cursor` with identical `None` guard patterns (repeated 4 times)
3. **Storage layer has 0% coverage** on 10+ modules (projections, incidents, heartbeat_runs, knowledge, metrics, quality_scores)
4. **Dual-path session storage** — WorkflowSessionStore manages both filesystem (`sessions/sess-XXXX/`) AND database, with separate code paths

---

## Root Cause: Data Flow Issues

### 1. Graph Executor as God Object (Data Flow Score: 5/10 → target 8/10)

`graph_executor.py` is the central hub where ALL data flows converge:
- Step execution → event emission → session persistence → artifact management → contract validation → recovery handling

Data zigzags: the executor calls into `prompt_builder` (down), which calls back to the executor's `_stage_configs` (up), then into `unified_compiler` (down again). The executor is passed as `self` to helpers that reach back into its internals.

**Fix**: Extract 3 focused collaborators:
- `EventEmitter` — handles `_emit_event`, `_emit_events_batch`, `_emit_error_event`, `_persist_event`, `_commit_transition` (~200 LOC)
- `ArtifactResolver` — handles `_build_artifact_handoff_manifest`, `_resolve_required_artifact_path`, `_load_artifact_row_safe`, `_check_required_inputs` (~150 LOC)
- `ContractRunner` — handles contract validation orchestration, currently embedded in `_execute_task` (~100 LOC)

### 2. Duplicated Cursor Guard Pattern

4 files have identical `executor_cursor` None-check pattern:
```python
cursor = session.executor_cursor
if cursor is not None:
    cursor.current_node_id = ...
    cursor.remove_from_ready_queue(...)
    cursor.add_to_ready_queue(...)
```

Files: `recovery_handler.py:660-663`, `recovery_handler.py:732-735`, `recovery/contract_repair.py:129-132`, `recovery/patch_and_test.py:121-124`

**Fix**: Add `WorkflowSession.reschedule_node(from_id, to_id)` method (~15 LOC) that encapsulates cursor manipulation. Eliminates 4 duplicated blocks.

### 3. Dual Session Storage

`WorkflowSessionStore` (1313 LOC) manages both filesystem sessions (`sessions/sess-XXXX/session.json`) AND database sessions (`sessions` table). Most methods have branching logic for both paths.

This isn't an immediate fix — it's architectural. The filesystem path exists for debugging/portability. But the complexity cost is ~400 LOC of parallel code paths.

---

## The Plan

### S) Data Flow Simplification

| # | Change | Lines Eliminated | Lines Added | Net | Impact |
|---|--------|-----------------|-------------|-----|--------|
| S1 | Extract `EventEmitter` from `graph_executor.py` | ~200 | ~220 (new file + wiring) | -0 | Untangles event emission from step logic |
| S2 | Extract `ArtifactResolver` from `graph_executor.py` | ~150 | ~170 | -0 | Separates artifact I/O from execution |
| S3 | Add `WorkflowSession.reschedule_node()` | ~48 (4 × 12 LOC blocks) | ~15 | -33 | Eliminates cursor guard duplication |

### A) Behavior-Preserving Structural Changes

| # | Change | Lines Eliminated | Lines Added | Net |
|---|--------|-----------------|-------------|-----|
| A1 | Split `graph_executor.py` — move hook/sub-workflow execution to separate module | ~300 | ~310 | -0 |
| A2 | Consolidate recovery files — merge `recovery/contract_repair.py` + `recovery/patch_and_test.py` into `recovery_handler.py` | ~50 (duplicated imports/setup) | 0 | -50 |

### B) Shared Pattern Extractions

| # | Change | Lines Eliminated | Lines Added | Net |
|---|--------|-----------------|-------------|-----|
| B1 | Extract `StageConfigResolver` from graph_executor + prompt_builder | ~80 | ~60 | -20 |

### C) God Function Decomposition

No god functions (>400 LOC) found. The 54 functions in graph_executor.py average ~40 LOC each — well within bounds.

### D) Dead Code Removal

| # | Target | Lines |
|---|--------|-------|
| D1 | Audit `projections.py` (1171 LOC, 0% coverage) — verify callers exist | TBD |
| D2 | Audit `heartbeat_runs.py` (158 LOC, 0% coverage) | TBD |
| D3 | Audit `incidents.py` (337 LOC, 0% coverage) | TBD |

---

## Scorecard

| Phase | Description | Lines Eliminated | Lines Added | Net | Elegance Impact | Risk |
|-------|-------------|-----------------|-------------|-----|----------------|------|
| S | Data flow simplification | ~398 | ~405 | -3 | High | Medium |
| A | Structural changes | ~350 | ~310 | -40 | Medium | Low |
| B | Pattern extraction | ~80 | ~60 | -20 | Low | Low |
| C | God function decomposition | 0 | 0 | 0 | N/A | N/A |
| D | Dead code removal | TBD | 0 | TBD | Low | Low |
| **Total** | | **~828** | **~775** | **~-63** | | |

Data flow clarity score: **7/10 → 8/10** after Phase S.

---

## What This Plan Does NOT Do

- **Does not restructure storage layer** — dual filesystem/DB in WorkflowSessionStore is an architectural decision, not a bug
- **Does not touch providers** — Anthropic/Codex/Gemini provider code is clean
- **Does not reduce file count** — file organization is cosmetic; data flow matters
- **Does not refactor models** — Pydantic models are well-structured
- **Does not touch sandbox or CLI** — different concerns, separate review
- **Does not add tests** — covered by separate T-20/T-22 tasks

## Execution Order

1. **S3** (reschedule_node) — smallest change, highest confidence, unblocks S1
2. **S1** (EventEmitter extraction) — enables cleaner graph_executor
3. **S2** (ArtifactResolver extraction) — completes graph_executor slimming
4. **A2** (recovery consolidation) — cleanup after S3
5. **A1** (split graph_executor further) — optional, depends on S1/S2 results
6. **B1** (StageConfigResolver) — independent, can be parallelized
7. **D1-D3** (dead code audit) — independent, low risk

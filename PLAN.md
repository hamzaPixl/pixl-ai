# CTO Review: Harness Engineering Improvements

## Current State

- **Branch**: `feat/harness-improvements`
- **Production lines added**: ~565 | **Test lines**: ~340
- **Data flow clarity**: 7/10 (clean module boundaries, steering uses in-band sentinel)

## Root Causes

### Steering uses in-band sentinel through error channel
`__STEER__:` prefix in `error_message` smuggles redirect instructions through the same
return slot as real errors. Caller does string parsing. A richer return type eliminates ambiguity.

### Interrupt and steer have no defined precedence
`_interrupt_event` and `_steering_queue` checked sequentially — interrupt wins, orphaning
queued steers. No coordination between signals.

## The Plan

### S) Data Flow Redesigns

| ID | Change | File | Net Lines | Risk |
|----|--------|------|-----------|------|
| S1 | Replace `__STEER__` sentinel with structured return dataclass | `core.py` | +10 | Medium |
| S2 | Define interrupt/steer precedence (interrupt drains queue) | `core.py` | +10 | Low |

### A) Structural Changes

| ID | Change | File | Net Lines | Risk |
|----|--------|------|-----------|------|
| A1 | Extract persistent-client loop into own method (kills 9 type-ignores) | `core.py` | +5 | Low |

### B) Pattern Extractions

| ID | Change | Files | Net Lines | Risk |
|----|--------|-------|-----------|------|
| B1 | Extract shared graph validation into `scripts/validate-task-graph.sh` | skills, new script | -15 | Low |

### D) Dead Code (deferred one release cycle)

| ID | Change | Files | Net Lines | Risk |
|----|--------|-------|-----------|------|
| D1 | Remove deprecated `block-destructive.sh` + `detect-secrets.sh` | hook scripts | -62 | Low |

## Scorecard

| Phase | Lines Elim | Lines Add | Net | Data Flow Impact |
|-------|-----------|-----------|-----|------------------|
| S1+S2 | 20 | 40 | +20 | 7→9 clarity |
| A1 | 0 | 5 | +5 | Kills type-ignores |
| B1 | 30 | 15 | -15 | DRY |
| D1 | 62 | 0 | -62 | Dead code |

## What This Plan Does NOT Do

- Add API endpoint for `steer_session` (needs API package)
- Refactor `backlog.py` to reuse `task_graph.py` (different domains)
- Handle chained steers (document single-steer per query)
- Remove old hook scripts immediately (deprecation cycle)

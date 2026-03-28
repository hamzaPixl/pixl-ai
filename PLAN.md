# CTO Review — v10.2.0 API + Console Integration

## Current State

| Metric | Value |
|--------|-------|
| Branch commits | 6 (637ad6f → 5c49aea) |
| Files changed | 458 |
| Total insertions | 70,445 |
| API Python LOC (non-test) | ~5,768 across 44 files |
| Console TS/TSX LOC (non-test) | ~41,271 across 321 files |
| API tests | 123 |
| API routes | 144 |
| Data flow clarity score | **6/10** |

### Headline Problems

1. **CRUD copy-paste across 3 route files** — features.py, epics.py, roadmaps.py are 95% identical (~200 duplicated lines)
2. **db.py is a 645-line god file** — users, workspaces, members, teams, invitations, API keys all in one
3. **Raw SQL in route handlers** — recovery.py does direct `conn.execute()` instead of using engine stores
4. **No workspace authorization** — workspace routes don't verify the user owns/belongs to the workspace
5. **Console type escaping** — `auth.ts` uses `unknown` 10+ times, `usage.ts` uses `any` 5 times
6. **Store-Query duplication** — auth and project state duplicated between Zustand stores and React Query cache

---

## Root Cause: Data Flow Analysis

### API Layer Data Flow

```
HTTP Request → FastAPI Route → asyncio.to_thread(engine_store.method()) → dict → JSON Response
```

**The pipeline is straight-line — good.** No zigzag, no unnecessary intermediaries. But:

1. **CRUD routes repeat the same pipeline 3x** — features/epics/roadmaps each implement identical list→get→create→update→delete→transition→history patterns. The entity name is the only difference.

2. **recovery.py breaks the pattern** — instead of calling an engine store, it opens a raw SQLite connection and runs SQL directly. This creates a second data path that bypasses the engine's store layer.

3. **dashboard.py makes 6 sequential DB calls** that could be parallelized — `get_stats()`, `summary()`, `get_active_sessions()`, `get_recent_sessions()`, `get_events()`, `breakdown_by_model()`. At least 4 of these are independent reads.

### Console Data Flow

```
API Response → lib/api/module.ts (TRANSFORM) → React Query cache → useQuery hook → Component
                                                    ↑
                                        Zustand store (DUPLICATE for auth, projects)
```

**Problem: transformation at the wrong layer.** `usage.ts` does 35 lines of dict→array conversion because the API response shape is inconsistent. `sessions.ts` normalizes field names (`event_type` → `type`). This should be handled by the API, not the client.

---

## The Plan

### S) Data Flow and Algorithmic Redesigns

#### S1. Parallelize dashboard overview queries
- **File**: `packages/api/pixl_api/routes/dashboard.py` (lines 27-103)
- **Problem**: `_build_overview()` makes 6 sequential DB calls. 4 are independent reads.
- **Fix**: Use `asyncio.gather()` for independent calls.
- **Impact**: ~2-4x faster dashboard load. ~0 lines net.
- **Risk**: Low — all calls are read-only

#### S2. Move raw SQL out of recovery.py into engine store
- **File**: `packages/api/pixl_api/routes/recovery.py` (lines 86-171)
- **Problem**: `_do_retry_node()` and `_do_skip_node()` do raw `conn.execute()` SQL.
- **Fix**: Add `retry_node()` and `skip_node()` methods to engine's SessionStore.
- **Lines eliminated**: ~82 | **Lines added**: ~40 | **Net**: -42
- **Risk**: Low — behavior identical

#### S3. Normalize API response shapes to eliminate client transformations
- **Problem**: Console `usage.ts` (35 lines) and `sessions.ts` normalizeEvent() exist because API returns inconsistent shapes.
- **Fix**: Normalize at the API layer. Then delete the client transformations.
- **Lines eliminated**: ~40 (Console) | **Lines added**: ~10 (API) | **Net**: -30
- **Risk**: Low

---

### A) Behavior-Preserving Structural Changes

#### A1. Extract generic CRUD router factory for features/epics/roadmaps
- **Files**: `routes/features.py` (176), `routes/epics.py` (168), `routes/roadmaps.py` (156) = 500 LOC
- **Problem**: 95% identical. Only entity name and create fields differ.
- **Fix**: Create `routes/_crud.py` factory. Each entity file becomes ~20 lines of config.
- **Lines eliminated**: ~350 | **Lines added**: ~160 | **Net**: -190
- **Risk**: Low — pure refactor

#### A2. Add workspace authorization checks
- **File**: `routes/workspaces.py` (264 lines)
- **Problem**: Any authenticated user can access any workspace.
- **Fix**: Add `_verify_workspace_access()` helper + 1-line call per route.
- **Lines added**: ~35 | **Net**: +35
- **Risk**: Low — additive security

---

### B) Shared Pattern Extractions

#### B1. Extract retry/skip duplication in recovery.py
- `_do_retry_node()` and `_do_skip_node()` are 90% identical. (Moot if S2 is done first.)
- **Net**: -20

#### B2. Remove stale response_model decorators
- 5 decorators in features.py, recovery.py, agents.py that don't enforce anything.
- **Net**: -10

---

### C) God File Decomposition

#### C1. Split db.py (645 lines) into domain modules
- Extract into `db/users.py` (90), `db/workspaces.py` (165), `db/teams.py` (135), `db/invitations.py` (43), `db/projects.py` (31), `db/api_keys.py` (68).
- **Net**: ~+15 (overhead)

---

### D) Dead Code Removal

#### D1. Dynamic agent loading instead of hardcoded list
- `routes/agents.py` lines 21-120: 100 lines that mirror `crew/agents/*.md`.
- **Fix**: Scan crew directory at startup, fall back to hardcoded.
- **Net**: -70

#### D2. Fix silent exception swallowing
- 7 bare `except Exception: pass` blocks across dashboard.py, agents.py, artifacts.py.
- **Fix**: Add `logger.warning()` calls.
- **Net**: +14

---

## Scorecard

| Phase | Description | Lines Out | Lines In | Net | Impact | Risk |
|-------|-------------|-----------|----------|-----|--------|------|
| S1 | Parallelize dashboard | 0 | 5 | +5 | High (perf) | Low |
| S2 | Raw SQL → engine store | 82 | 40 | -42 | High (data flow) | Low |
| S3 | Normalize response shapes | 40 | 10 | -30 | High (eliminates transforms) | Low |
| A1 | CRUD router factory | 350 | 160 | -190 | High (DRY) | Low |
| A2 | Workspace auth | 0 | 35 | +35 | Critical (security) | Low |
| B1 | Retry/skip dedup | 40 | 20 | -20 | Medium | Low |
| B2 | Stale response_model | 10 | 0 | -10 | Low | None |
| C1 | Split db.py | 645 | 660 | +15 | Medium | Low |
| D1 | Dynamic agents | 100 | 30 | -70 | Medium | Medium |
| D2 | Fix exception handling | 0 | 14 | +14 | Low | None |
| **Total** | | **1,267** | **974** | **-293** | | |

**Data flow clarity**: 6/10 → **8/10** after S1-S3

---

## What This Plan Does NOT Do

1. **Console restructuring** — DockBar (698 LOC), sidebar (783 LOC), auth.ts `unknown` types. Separate PR.
2. **Stubbed features** — GitHub, sandboxes, advanced control (rerun/rollback) remain 501. Need engine work.
3. **Multi-tenancy/RBAC** — A2 adds basic access checks, not full role-based permissions.
4. **SQLite connection pooling** — `db.py` opens/closes per call. Fine for MVP concurrency.
5. **Test code** — Not reviewed or proposed for changes.

---

## Execution Order

```
S2 + S1 + A2  (first PR)  — fix data flow, parallelize, add security
A1             (second PR) — CRUD factory (informed by S2 patterns)
S3 + B2 + D2  (third PR)  — normalize shapes, cleanup
C1 + D1        (fourth PR) — file organization, dynamic agents
```

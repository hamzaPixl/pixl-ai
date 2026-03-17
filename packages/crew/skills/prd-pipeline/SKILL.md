---
name: prd-pipeline
description: "Autonomous PRD-to-production pipeline. Takes a PRD and orchestrates the full lifecycle: spec decomposition, task planning, sprint breakdown, implementation, quality gates, and PR creation. Multi-session by design — persists state across context boundaries. Use when asked to 'execute a PRD', 'implement from spec', 'autonomous pipeline', 'PRD to production', or 'run the full project from requirements'."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion
argument-hint: "<PRD file path or 'resume'>"
context: fork
---

## Overview

Orchestrates a PRD-to-production pipeline by composing existing pixl-crew skills across multiple sessions. Each phase persists state to a pipeline state file so the next session can resume without replanning. The `session-start.sh` hook auto-injects prior session summaries and decisions on restart.

A scope guard hook (`prd-pipeline-scope-guard`) activates automatically when `pipeline-state.json` is present — it blocks accidental writes to critical infrastructure files (CI workflows, `.env`, `Makefile`, `docker-compose`, package manifests, `CLAUDE.md`) during autonomous execution. Set `PIXL_PIPELINE_BYPASS=1` to override.

## Mode Detection

| Input | `pipeline-state.json` exists? | Mode |
|-------|-------------------------------|------|
| File path or URL | No | **Init** — start new pipeline |
| File path or URL | Yes | **Reset** — restart pipeline with new PRD |
| `resume` or no argument | Yes | **Resume** — continue from last phase |
| No argument | No | **Error** — ask for PRD path |

## Pipeline State

Track progress in a `pipeline-state.json` file committed alongside the project:

```json
{
  "version": "1.0",
  "started_at": "ISO timestamp",
  "updated_at": "ISO timestamp",
  "prd_source": "<path to canonical PRD>",
  "current_phase": "planning",
  "phases": {
    "setup": { "status": "completed", "started_at": "...", "completed_at": "..." },
    "planning": { "status": "in_progress", "started_at": "..." },
    "foundation": { "status": "pending" },
    "implementation": { "status": "pending" },
    "quality": { "status": "pending" },
    "delivery": { "status": "pending" },
    "finalization": { "status": "pending" }
  },
  "sprints_completed": 0,
  "total_sprints": 4,
  "coverage_percentage": 0.0,
  "branch": "feat/prd-implementation"
}
```

## Phases

### Phase 0: Setup

**Goal**: Bootstrap the pipeline workspace and verify the project is buildable and testable.
**Inputs**: PRD file path or URL.
**Outputs**: Canonical PRD stored in the project context directory, `pipeline-state.json` initialized, test command verified.
**Constraints**: PRD must be readable before proceeding. The project must have a discoverable test command. Suggest scoped permission wildcards via `AskUserQuestion` if none are configured.

### Phase 1: Planning

**Goal**: Decompose the PRD into atomic requirements, produce a dependency-aware task plan, size it into sprints, and capture an architecture decision record. End with a mandatory human checkpoint.
**Inputs**: `pipeline-state.json`, canonical PRD.
**Outputs**: `requirements.json`, `task-state.json`, `sprint-plan.md`, architecture packet.
**Constraints**: Human approval required before Phase 2. Present the full plan summary — task count, sprint breakdown, critical path, architecture — via `AskUserQuestion`. Do not auto-approve. Persist task state and learning before pausing.

### Phase 2: Foundation

**Goal**: Scaffold the project structure and land Sprint 1 tasks that touch shared files, establishing a stable base for parallel implementation.
**Inputs**: `sprint-plan.md`, `task-state.json`, architecture packet.
**Outputs**: Scaffold and base infrastructure committed to a feature branch, full test suite passing.
**Constraints**: No feature code before the scaffold is committed. Sprint 1 tasks run sequentially — foundation work touches shared files and cannot be safely parallelized. Each task must pass tests before the next begins.

### Phase 3: Implementation

**Goal**: Execute remaining sprints autonomously, parallelizing independent tasks where file scopes do not overlap.
**Inputs**: `task-state.json` (phase=implementation), architecture packet, requirements.
**Outputs**: Features implemented, tests passing, changes committed per task.
**Constraints**: Compact context before each sprint batch — do not wait for truncation warnings. Load task state at the start of each session. Run the full test suite after each sprint; fix failures before proceeding. If context grows large mid-sprint, persist state and resume in a new session.

### Phase 4: Quality

**Goal**: Validate implementation quality, measure spec coverage, and resolve any drift between implemented behavior and the original requirements.
**Inputs**: Sprint changes, requirements baseline, `pipeline-state.json`.
**Outputs**: Review findings resolved, updated `coverage_percentage`, drift-corrected task plan if gaps are found.
**Constraints**: All HIGH+ findings from `/code-review` or `/self-review-fix-loop` must be resolved before proceeding. If P0/P1 findings persist after the review-fix loop limit, escalate to the user via `AskUserQuestion`. Update `pipeline-state.json` with the latest coverage percentage.

### Phase 5: Delivery

**Goal**: Push the feature branch and create a PR that documents what was built and why.
**Inputs**: Quality gate passed, committed changes on the feature branch.
**Outputs**: PR created, `pipeline-state.json` finalized.
**Constraints**: PR body must reference the PRD (link or inline summary), include acceptance criteria met, and a test plan. For multi-sprint projects, prefer incremental PRs per sprint over one large PR.

## Human Checkpoints

| Phase | Why |
|-------|-----|
| After Phase 1 | Validate planning before implementation begins — this is the last approval gate before autonomous execution |
| During Phase 3 | If `/spec-review` detects significant drift from the original requirements |
| During Phase 4 | If the review-fix loop cannot resolve P0/P1 findings autonomously |

## Recovery Table

| Failure | Symptom | Recovery |
|---------|---------|----------|
| Lost state | `pipeline-state.json` missing | Re-run with `--reset` flag and the original PRD path |
| Session crash | Context lost mid-phase | Run `/prd-pipeline resume` — reads state file and `git log` to find resume point |
| Context overflow | Truncated output or compaction warning | Run `/strategic-compact`, then `/task-persist save`, then start a new session with `resume` |
| Spec drift | `/spec-review` reports coverage gaps | Run `/prd-analysis` again, update task plan in drift mode, then resume |
| Sprint stall | Tasks blocked for more than one sprint | Re-evaluate scope with the user, defer low-priority items |
| Test failures | Quality gate blocked, suite red | Run `/self-review-fix-loop` before retrying; never skip to the next phase |
| Batch partial failure | Some `/batch` units report errors | Re-run only failed units — successful ones are already committed |
| Typecheck failing | Type errors block commit | Resolve type errors before committing; consult architecture packet for type contracts |

## Gotchas

- Pipeline state file must be committed — losing it means restarting from scratch. Commit after every phase transition.
- Context fills fast during implementation — use `/strategic-compact` proactively, don't wait for truncation. By the time you notice, important context is already lost.
- Human checkpoints are blocking — skipping them risks building on unvalidated assumptions. Never auto-approve the Phase 1 checkpoint.
- Resume mode re-reads all artifacts — if artifacts were manually edited between sessions, the pipeline may produce inconsistent output. Document any manual edits in the decision log.
- Sprint execution depends on `/task-plan` output — running without it causes the pipeline to re-plan from scratch, potentially diverging from prior approvals.

## Related Skills

- `/spec-review` — requirement decomposition and coverage scanning
- `/task-plan` — task decomposition with drift awareness
- `/sprint-planning` — sprint sizing and velocity tracking
- `/batch` — parallel worktree execution
- `/self-review-fix-loop` — multi-agent review and remediation
- `/ralph-loop-crew` — alternative: persistent autonomous loop per sprint
- `/task-persist` — cross-session task state
- `/strategic-compact` — context management before compaction
- `/continuous-learning` — cross-session pattern learning

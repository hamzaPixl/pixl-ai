---
name: prd-pipeline
description: "Autonomous PRD-to-production pipeline. Takes a PRD and orchestrates the full lifecycle: spec decomposition, task planning, sprint breakdown, implementation, quality gates, and PR creation. Multi-session by design — persists state across context boundaries. Use when asked to 'execute a PRD', 'implement from spec', 'autonomous pipeline', 'PRD to production', or 'run the full project from requirements'."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion
argument-hint: "<PRD file path or 'resume'>"
context: fork
---

## Overview

This skill orchestrates a full PRD-to-production pipeline by composing existing pixl-crew skills in sequence. It manages the lifecycle across multiple sessions, using `.context/` for state persistence and `.context/pipeline-state.json` for pipeline progress tracking.

**Why multi-session**: A full project exceeds a single context window. Each phase runs within one session, persists state, and the next session picks up where the previous left off. The `session-start.sh` hook auto-injects last 3 session summaries + 10 decisions on restart.

## Required References

Read `references/pipeline-runbook.md` for the detailed phase-by-phase runbook with recovery procedures.

## Mode Detection

| Input | `pipeline-state.json` exists? | Mode |
|-------|-------------------------------|------|
| File path or URL | No | **Init** — start new pipeline |
| File path or URL | Yes | **Reset** — restart pipeline with new PRD |
| `resume` or no argument | Yes | **Resume** — continue from last phase |
| No argument | No | **Error** — ask for PRD path |

## Pipeline State

Track progress in `.context/pipeline-state.json`:

```json
{
  "version": "1.0",
  "started_at": "ISO timestamp",
  "updated_at": "ISO timestamp",
  "prd_source": ".context/prd.md",
  "current_phase": "planning",
  "phases": {
    "setup": { "status": "completed", "started_at": "...", "completed_at": "..." },
    "planning": { "status": "completed", "started_at": "...", "completed_at": "..." },
    "foundation": { "status": "in_progress", "sprint": 1, "started_at": "..." },
    "implementation": { "status": "pending" },
    "quality": { "status": "pending" },
    "pr": { "status": "pending" },
    "finalization": { "status": "pending" }
  },
  "sprints_completed": 1,
  "total_sprints": 4,
  "coverage_percentage": 35.0,
  "branch": "feat/prd-implementation"
}
```

## Phase 0: Setup (automatic)

1. Create `.context/` and `.context/spec/` directories if they don't exist
2. Copy the PRD to `.context/prd.md` (canonical location)
3. Initialize `.context/pipeline-state.json` with all phases set to `pending`
4. Verify the project has a working test command (check `Makefile`, `package.json`, `pyproject.toml`)
5. If `.claude/settings.local.json` does not exist, suggest permissions for autonomous operation via AskUserQuestion:

```json
{
  "permissions": {
    "allow": [
      "Bash(make *)", "Bash(npm run *)", "Bash(npx *)", "Bash(bun run *)",
      "Bash(git add:*)", "Bash(git commit:*)", "Bash(git checkout:*)",
      "Bash(git push -u:*)", "Bash(gh pr create:*)", "Bash(gh *)",
      "Bash(pytest *)", "Bash(uv run *)"
    ]
  }
}
```

## Phase 1: Planning (interactive — human reviews before autonomy)

Execute these skills in sequence:

### Step 1.1: Spec Decomposition
Invoke `/spec-review .context/prd.md`:
- Decomposes PRD into atomic requirements in `.context/spec/requirements.json`
- Produces baseline coverage scan (starts at 0%)

### Step 1.2: Task Planning
Invoke `/task-plan .context/prd.md`:
- Creates dependency-aware vertical slices with acceptance criteria
- Assigns suggested agents per task
- Saves to `.context/task-state.json`

### Step 1.3: Sprint Breakdown
Invoke `/sprint-planning` on the task plan:
- Groups tasks into sprint iterations (S=1pt, M=2pt, L=3pt)
- Saves sprint plan to `.context/sprint-plan.md`

### Step 1.4: Architecture
Spawn an **architect** agent:
- Architecture decisions, component tree, file structure, tech stack
- Output to `.context/architecture-packet.json`

### Step 1.5: Persist
1. Invoke `/task-persist save`
2. Invoke `/continuous-learning record` — log key planning decisions
3. Update `pipeline-state.json`: set `planning` to `completed`

### Step 1.6: Human Checkpoint
Present to the user via AskUserQuestion:
- Total tasks, sprint breakdown, critical path
- Parallelizable task groups
- Architecture summary
- Ask: "Review the plan. Approve to proceed with autonomous implementation, or request changes."

**This is the last human checkpoint before autonomous execution.**

## Phase 2: Foundation Sprint (sequential)

Foundation/scaffolding touches shared files — must be sequential.

1. Create the implementation branch:
   ```
   git checkout -b feat/prd-implementation
   ```
2. Load task state: invoke `/task-persist load`
3. Read `.context/architecture-packet.json` and `.context/sprint-plan.md`
4. Execute Sprint 1 tasks **sequentially**:
   - For each task: implement → test → typecheck → commit (conventional commits)
   - Mark each task completed via TaskUpdate
5. After all Sprint 1 tasks: run full test suite
6. Invoke `/task-persist save`
7. Invoke `/continuous-learning observe`
8. Update `pipeline-state.json`: set `foundation` to `completed`, increment `sprints_completed`

## Phase 3: Implementation Sprints (autonomous, per sprint)

For each remaining sprint (2..N):

### Step 3.1: Load State
1. Invoke `/task-persist load`
2. Read `.context/architecture-packet.json` and `.context/spec/requirements.json`

### Step 3.2: Identify Parallelism
Analyze sprint tasks for parallel groups:
- Tasks with **non-overlapping file scopes** can run in parallel
- Tasks with dependencies must be sequential

### Step 3.3: Execute
- **Parallel tasks**: Use `/batch` with worktree isolation (max 10 units)
- **Sequential tasks**: Execute in dependency order, commit after each
- After each task: run relevant tests + typecheck

### Step 3.4: Integration
1. Run full test suite after all sprint tasks
2. If tests fail, fix failures before proceeding

### Step 3.5: Persist
1. Invoke `/task-persist save`
2. Update `pipeline-state.json`: increment `sprints_completed`

### Step 3.6: Context Check
If context is getting large (many tool calls):
1. Invoke `/strategic-compact`
2. Invoke `/task-persist save`
3. Tell the user to start a new session with `/prd-pipeline resume`

## Phase 4: Quality Gate (per sprint)

After each implementation sprint:

### Step 4.1: Self-Review
Invoke `/self-review-fix-loop` on sprint changes:
- 3 parallel reviewers (correctness, security, tests)
- 3 parallel fixers (non-overlapping file scopes)
- Iterates until no P0/P1 findings (max 10 rounds)

### Step 4.2: Spec Coverage
Invoke `/spec-review rescan`:
- Coverage percentage against `requirements.json`
- Detect missing features and extras (scope creep)

### Step 4.3: Plan Drift
If gaps found, invoke `/task-plan` in drift mode:
- Creates new tasks for missing requirements
- Removes tasks for dropped requirements
- Updates `.context/task-state.json`

### Step 4.4: Persist
Invoke `/task-persist save`
Update `pipeline-state.json` with latest `coverage_percentage`

## Phase 5: PR Creation (per sprint)

After quality gate passes for a sprint:

1. Push the branch: `git push -u origin feat/prd-implementation`
2. Create a PR using `gh pr create`:
   - Title: sprint goal
   - Body: PRD coverage percentage, acceptance criteria met, test plan
3. Update `pipeline-state.json`

For multi-sprint projects, create incremental PRs per sprint to keep each under 400 lines.

## Phase 6: Final Validation (last session)

When all sprints are completed and all tasks are done:

1. Invoke `/spec-review rescan` — final coverage percentage
2. Invoke `/cto-review` — architectural assessment
3. Invoke `/security-scan` — OWASP check
4. Invoke `/dependency-review` — CVE/license audit
5. Run full build + test suite
6. Invoke `/continuous-learning observe` — extract project patterns
7. Update `pipeline-state.json`: set `finalization` to `completed`

Present the final report:
- Coverage percentage (target: 100% of `must` requirements)
- Quality assessment summary
- Security findings (if any)
- Total sprints, commits, and tasks completed

## Recovery

| Failure | Recovery |
|---------|----------|
| Session crash | `/prd-pipeline resume` — reads `pipeline-state.json` + `task-state.json` + `git log` |
| `/batch` partial failure | Re-run failed units only; successful ones already merged |
| Context overflow | `/strategic-compact` → `/task-persist save` → new session with `resume` |
| Spec drift (PRD changed) | `/spec-review` Mode B → `/task-plan` drift mode |
| Quality gate stuck | Max 10 iterations; escalates to human via AskUserQuestion |
| Tests failing | Fix before proceeding; do not skip to next phase |

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

# PRD-to-Production Pipeline Runbook

Detailed reference for the `/prd-pipeline` skill. Covers multi-session orchestration, headless execution, and recovery procedures.

## Multi-Session Architecture

### Why Multi-Session?

Claude's context window fills up during a full project. The `suggest-compact.sh` hook warns at 50 tool calls, critical at 150. A full project involves hundreds of tool calls. Even with `/strategic-compact`, compaction loses nuance.

### How State Survives

| Mechanism | What it does |
|-----------|-------------|
| `pipeline-state.json` | Tracks which phase/sprint the pipeline is in |
| `/task-persist save/load` | Serializes all task state to `.context/task-state.json` |
| `session-start.sh` hook | Auto-injects last 3 session summaries + 10 decisions |
| `.context/` directory | All context packets survive across sessions |
| `.claude/memory/decisions.jsonl` | Permanent decision log |
| `/continuous-learning` | Records heuristics for future sessions |
| `git log` | Committed work survives any crash |

### Session Boundaries

Each phase naturally maps to one session:

| Session | Phase | Duration | Autonomous? |
|---------|-------|----------|-------------|
| 1 | Planning (Phase 1) | 15-30 min | Interactive — human reviews |
| 2 | Foundation (Phase 2) | 30-60 min | Semi-autonomous |
| 3..N | Implementation sprints (Phase 3) | 30-60 min each | Fully autonomous |
| N+1 | Quality + PR (Phase 4-5) | 15-30 min | Autonomous |
| Final | Validation (Phase 6) | 15-30 min | Autonomous |

## Headless Execution

### Single Sprint (Non-Interactive)

```bash
claude -p "Load /task-persist load. Execute Sprint 2 from .context/sprint-plan.md. \
  For parallel tasks: use /batch with worktree isolation. \
  For sequential tasks: execute in dependency order. \
  After each task: run tests, typecheck, commit. \
  After all tasks: full test suite. \
  Persist: /task-persist save." \
  --allowedTools "Read,Write,Edit,Bash(make *),Bash(git *),Bash(npm *),Agent" \
  --max-budget-usd 5.00
```

### Full Automation Script

The `scripts/run-prd.sh` script automates the multi-session pipeline:

```bash
# Usage:
./scripts/run-prd.sh [--sprints N] [--skip-planning]

# What it does:
# 1. Phase 1: Planning (interactive — human reviews)
# 2. Phase 2: Foundation sprint (headless)
# 3. Phase 3-5: Sprint loop (headless) — implement, quality gate, PR
# 4. Phase 6: Final validation (headless)
```

### Quality Gate Per Sprint

```bash
claude -p "Load /task-persist load. \
  Run /self-review-fix-loop on current changes. \
  Run /spec-review rescan. \
  If drift found, run /task-plan in drift mode. \
  /task-persist save." \
  --max-budget-usd 5.00
```

## Alternative Execution Modes

### Ralph Loop (Iterative Until Done)

Instead of structured sprints, use `/ralph-loop-crew` for an iterative approach:

```
/ralph-loop-crew

Task: Implement Sprint {N} tasks from .context/task-state.json
Completion criteria:
- All Sprint {N} tasks marked completed in task-state.json
- All tests pass
- Typecheck passes
- Each task has a commit
Iteration budget: 15
Verification: make test && npx tsc --noEmit
```

Ralph spawns fresh iterations with measurable exit conditions.

### Agent Teams (Experimental)

Enable in settings: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=true`

Agent teams let multiple Claude instances work in parallel with direct communication. Best for cross-layer work where frontend + backend + tests each get their own teammate.

### Batch Mode (Parallel Transformations)

For sprints with many independent tasks:

```
/batch "Implement tasks T-005 through T-012 from .context/task-state.json. Each task is independent — execute in parallel worktrees."
```

## Permissions Template

For autonomous operation, create `.claude/settings.local.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(make *)",
      "Bash(npm run *)",
      "Bash(npx *)",
      "Bash(bun run *)",
      "Bash(git add:*)",
      "Bash(git commit:*)",
      "Bash(git checkout:*)",
      "Bash(git branch:*)",
      "Bash(git push -u:*)",
      "Bash(gh pr create:*)",
      "Bash(gh *)",
      "Bash(pytest *)",
      "Bash(uv run *)"
    ]
  }
}
```

Per `.claude/rules/permissions.md` — use scoped wildcards, not blanket `--dangerously-skip-permissions`.

## Context Survival Strategy

### When Context Gets Large

1. The `suggest-compact.sh` hook tracks tool calls and warns:
   - **50 calls**: Reminder to consider `/strategic-compact`
   - **150 calls**: Critical warning — save state and start new session
2. Before compacting:
   - Run `/task-persist save` to serialize task state
   - Run `/continuous-learning observe` to capture patterns
   - State in `.context/` and `.claude/memory/` survives compaction
3. After compacting (or in new session):
   - `session-start.sh` auto-injects last 3 sessions + 10 decisions
   - Run `/task-persist load` to restore tasks
   - Read `pipeline-state.json` to resume from the right phase

### What Survives vs. What's Lost

| Survives | Lost on compaction |
|----------|-------------------|
| `.context/pipeline-state.json` | In-memory task list |
| `.context/task-state.json` | Detailed file content from reads |
| `.context/spec/requirements.json` | Search result details |
| `.context/architecture-packet.json` | Tool call history |
| `.claude/memory/decisions.jsonl` | Conversation nuance |
| Git commits | Uncommitted changes (commit first!) |

## Recovery Procedures

### Session Crash

```
# In new session:
/prd-pipeline resume

# What happens:
# 1. Reads pipeline-state.json → knows current phase
# 2. Reads task-state.json → knows which tasks are done
# 3. Checks git log → finds committed work
# 4. Resumes from the right point
```

### Batch Partial Failure

When `/batch` reports failed units:
1. Check the batch results table for failure reasons
2. Failed units can be re-run independently
3. Successful units are already merged — no need to redo them

### Spec Changed Mid-Pipeline

```
# 1. Replace the PRD
cp ~/updated-prd.md .context/prd.md

# 2. Run spec review with drift detection
/spec-review .context/prd.md

# 3. Adapt the task plan
/task-plan  (auto-detects drift from coverage report)

# 4. Resume pipeline
/prd-pipeline resume
```

### Tests Failing After Implementation

Do NOT skip failing tests. The pipeline enforces:
1. Fix the failing tests before moving to the next task
2. If a test failure reveals a design issue, escalate via AskUserQuestion
3. Use `/self-review-fix-loop` to systematically resolve test failures

### Quality Gate Stuck (Max Iterations)

After 10 review-fix iterations, the quality gate escalates:
1. Remaining P0/P1 findings are reported to the user
2. The pipeline pauses and asks for human intervention
3. After human resolves the issues, `/prd-pipeline resume` continues

## Pipeline State Transitions

```
Init → setup → planning → foundation → implementation → quality → pr → finalization
          ↑           ↑             ↑               ↑
          └───────────┴─────────────┴───────────────┘
                    (resume from any phase)
```

Each phase transition:
1. Saves task state (`/task-persist save`)
2. Updates `pipeline-state.json`
3. Logs decisions to `.claude/memory/decisions.jsonl`

## Monitoring Progress

Between sessions, check pipeline status:

```bash
# Quick status
cat .context/pipeline-state.json | jq '{phase: .current_phase, sprints: "\(.sprints_completed)/\(.total_sprints)", coverage: .coverage_percentage}'

# Remaining tasks
cat .context/task-state.json | jq '[.tasks[] | select(.status != "completed")] | length'

# Git progress
git log --oneline feat/prd-implementation | head -20
```

---
name: sprint-planning
description: "Sprint breakdown: epic decomposition → sprint cycles → velocity tracking. Use when asked to plan sprints, decompose epics, organize work into iterations, or estimate delivery timelines."
allowed-tools: Read, Glob, Grep, Write
argument-hint: "<epic or feature set to plan>"
---

## Overview

Breaks down epics into sprint-sized work packages. Integrates with `/task-plan` output for task sourcing, maps sprint items to git branches and PRs, and produces acceptance criteria that `/spec-review` can validate.

## Required References

Before starting, check for:
- `.context/task-state.json` — existing task plan from `/task-plan` or `/task-persist`
- `.context/spec/requirements.json` — decomposed requirements from `/spec-review`
- `.claude/memory/sessions/` — past session summaries for velocity calibration

## Step 1: Task Sourcing

**If `/task-plan` output exists** (`.context/task-state.json`):

1. Load the existing task breakdown — do NOT re-decompose from scratch
2. Use task IDs, sizes, dependencies, and acceptance criteria as-is
3. Group tasks into sprint-sized batches based on dependency chains
4. Flag any tasks missing size estimates or acceptance criteria

**If no task plan exists**:

1. Analyze the epic's scope and requirements
2. Identify vertical slices (each delivering user-visible value)
3. Break slices into implementable tasks
4. Estimate each task (S=1pt, M=2pt, L=3pt, XL=5pt)
5. Map dependencies between tasks
6. Suggest running `/task-plan` first for a more detailed breakdown

## Step 2: Velocity Calibration

1. **Check past sessions**: Scan `.claude/memory/sessions/` for completed sprint data
2. **Calculate historical velocity**: If past data exists, use actual points completed per sprint
3. **Default velocity**: If no history, use conservative estimates:
   - Solo agent: 8-12 points per sprint
   - Multi-agent (orchestrated): 20-30 points per sprint
4. **Adjust for unknowns**: Reduce velocity by 20% for greenfield work, new tech stacks, or unclear requirements

## Step 3: Sprint Assignment

1. Assign tasks to sprints respecting:
   - Dependency ordering (blocked tasks go to later sprints)
   - Capacity limits per sprint (based on calibrated velocity)
   - Agent skill matching (frontend tasks to frontend-engineer, etc.)
2. Each sprint must deliver a coherent, testable increment
3. Front-load risky or uncertain work into Sprint 1
4. Include a 20% buffer in each sprint for unplanned work and integration issues

### Branch and PR Mapping

For each sprint, define the git strategy:

| Sprint | Branch | PR target |
|--------|--------|-----------|
| Sprint 1 | `feat/sprint-1-<goal-slug>` | `main` |
| Sprint 2 | `feat/sprint-2-<goal-slug>` | `main` (or stacked on Sprint 1) |

Within each sprint, individual tasks map to commits (small tasks) or sub-branches (large tasks):
- S/M tasks: single commit on the sprint branch
- L/XL tasks: separate branch `feat/<task-id>-<slug>` merged into sprint branch

## Step 4: Sprint Plan Output

For each sprint, produce:

- **Goal**: One-sentence description of what the sprint delivers
- **Branch**: Git branch name for this sprint's work
- **Tasks**: Ordered list with task IDs (from `/task-plan` when available), estimates, assignees, dependencies
- **Acceptance criteria**: Testable checkboxes that `/spec-review` can validate against
- **Risks**: Known unknowns and mitigation plans
- **Velocity note**: Planned points vs. calibrated capacity

### Acceptance Criteria Format

Write acceptance criteria as testable assertions that map to requirement IDs when `/spec-review` data exists:

```markdown
- [ ] User can sign up with email/password (R-001)
- [ ] Dashboard loads in <2s on 3G connection (R-015)
- [ ] All API endpoints return proper error codes (R-008)
```

## Step 5: Velocity Tracking

1. After each sprint, record actual points completed
2. Calculate velocity (average points per sprint over last 3 sprints)
3. Update remaining sprint estimates based on actual velocity
4. Flag scope changes and their impact on timeline

## Output Format

Write the sprint plan to `.context/sprint-plan.md`:

```markdown
## Sprint 1: [Goal]

Branch: `feat/sprint-1-[slug]`
Capacity: [X] points | Planned: [Y] points (buffer: [Z] points)
Velocity basis: [historical avg / default estimate]

| #   | Task ID | Task                | Size | Agent            | Depends On | Status  |
| --- | ------- | ------------------- | ---- | ---------------- | ---------- | ------- |
| 1   | T-001   | Setup auth scaffold | M    | backend-engineer | —          | pending |
| 2   | T-002   | Login page UI       | S    | frontend-engineer| T-001      | pending |

### Acceptance Criteria
- [ ] Auth flow works end-to-end (R-001, R-002)
- [ ] Tests pass for all new endpoints

### Risks
- OAuth provider SDK may require additional config
```

## Gotchas

1. **Don't plan more than 2 sprints ahead in detail** — Requirements drift makes distant sprints unreliable. Plan Sprint 1 in full detail, Sprint 2 in moderate detail, and Sprint 3+ as rough outlines only.
2. **Include a 20% buffer for unplanned work** — Integration issues, bug fixes from previous sprints, and requirement clarifications always consume capacity. A sprint planned at 100% capacity will always slip.
3. **Each sprint item must have testable acceptance criteria** — "Improve performance" is not testable. "Dashboard loads in <2s on 3G" is. If you can't write a test for it, the scope is not clear enough.
4. **Link sprint items to `/task-plan` task IDs when available** — This preserves traceability from PRD requirements through task decomposition to sprint execution. Without IDs, drift detection and progress tracking break down.
5. **Front-load risk, not features** — The first sprint should tackle the hardest unknowns (new API integrations, unfamiliar tech, architectural decisions), not the easiest wins. Easy wins in Sprint 1 feel productive but hide risk that explodes in Sprint 3.

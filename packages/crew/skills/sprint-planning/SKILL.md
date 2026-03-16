---
name: sprint-planning
description: "Sprint breakdown: epic decomposition → sprint cycles → velocity tracking. Use when asked to plan sprints, decompose epics, organize work into iterations, or estimate delivery timelines."
allowed-tools: Read, Glob, Grep, Write
argument-hint: "<epic or feature set to plan>"
---

## Overview

Breaks down epics into sprint-sized work packages. Decomposes large features, assigns to sprints based on dependencies and capacity, and tracks velocity for estimation.

## Step 1: Epic Decomposition

1. Analyze the epic's scope and requirements
2. Identify user stories within the epic
3. Break stories into implementable tasks
4. Estimate each task (S=1pt, M=2pt, L=3pt, XL=5pt)
5. Map dependencies between tasks

## Step 2: Sprint Sizing

1. Determine sprint duration (default: 2 weeks)
2. Estimate team capacity (available agent-hours per sprint)
3. Account for overhead (reviews, testing, deployment)
4. Target 70-80% capacity utilization (leave room for unknowns)

## Step 3: Sprint Assignment

1. Assign tasks to sprints respecting:
   - Dependency ordering (blocked tasks go to later sprints)
   - Capacity limits per sprint
   - Skill matching (frontend tasks to frontend agent, etc.)
2. Ensure each sprint delivers a coherent increment
3. Front-load risky or uncertain work

## Step 4: Sprint Plan Output

For each sprint, produce:

- **Goal**: One-sentence description of what the sprint delivers
- **Tasks**: Ordered list with estimates, assignees, dependencies
- **Acceptance criteria**: How to verify the sprint goal is met
- **Risks**: Known unknowns and mitigation plans

## Step 5: Velocity Tracking

1. After each sprint, record actual points completed
2. Calculate velocity (average points per sprint)
3. Update remaining sprint estimates based on actual velocity
4. Flag scope changes and their impact on timeline

## Output Format

```markdown
## Sprint 1: [Goal]

Duration: [dates]
Capacity: [X] points | Planned: [Y] points

| #   | Task | Size | Agent            | Depends On | Status  |
| --- | ---- | ---- | ---------------- | ---------- | ------- |
| 1   | ...  | S    | backend-engineer | —          | pending |
```

---
name: harness
description: "GAN-inspired generate-evaluate-iterate harness for autonomous application development. Separates generation from evaluation using Playwright-based QA with 4-axis grading (design quality, originality, craft, functionality). Use when building full applications autonomously, running quality loops on generated code, or producing polished MVPs."
allowed-tools: Bash, Read, Write, Edit, Agent, Glob, Grep, WebFetch
argument-hint: "A 1-4 sentence product description (e.g., 'Build a task management app with kanban boards and AI prioritization')"
---

# Harness

GAN-inspired generate-evaluate-iterate loop. A generator agent builds the application, then an independent evaluator agent grades the output on four axes. If any score falls below threshold, the evaluator's critique feeds back into the generator for another pass. The loop continues until all scores pass or max iterations are reached.

## Required References

Before evaluating, read:
- `references/grading-rubric.md` -- 4-axis scoring criteria (design quality, originality, craft, functionality)
- `references/anti-rationalization.md` -- rules for honest evaluation, common rationalization traps

## Step 1: Input & Configuration

Accept a 1-4 sentence product description as the skill argument.

Ask the user (via AskUserQuestion) for optional configuration overrides. Use these defaults if the user skips:

| Parameter            | Default   | Description                                         |
| -------------------- | --------- | --------------------------------------------------- |
| Threshold            | 7/10      | Minimum score on each axis to pass                  |
| Max iterations       | 5         | Maximum generate-evaluate cycles before hard stop   |
| Budget cap           | $150      | Total spend limit across all iterations             |
| Aesthetic direction  | (none)    | Optional style guidance (e.g., "museum quality", "minimal dark mode") |

## Step 2: Execute via Engine Workflow (preferred path)

If the pixl CLI is available, delegate to the engine DAG:

```bash
pixl workflow run harness --prompt "<user prompt>" --yes
```

This runs the full DAG: plan -> generate -> evaluate -> score-gate -> (loop on failure).

Use `--stream` for real-time progress output. Monitor cost with `pixl cost summary` after completion.

If the engine workflow succeeds, skip to Step 4 (report).

## Step 3: Fallback -- Direct Agent Loop (when pixl CLI unavailable)

If pixl CLI is NOT available, run the loop directly using subagents.

### 3a: Plan

Spawn an **architect** agent to produce `harness-spec.md`:
- Feature list derived from the product description
- Component architecture (pages, API routes, data model)
- Technology choices (framework, styling, deployment)
- Acceptance criteria for each feature

If the user provided an aesthetic direction, include it in the spec as a design constraint.

### 3b: Generate

Spawn a **fullstack-engineer** agent to build the application:
- Input: `harness-spec.md` + any prior evaluator feedback (from previous iterations)
- Output: working application code, committed to the repo
- The generator should run the dev server and verify basic functionality before handing off

### 3c: Evaluate

Spawn a **qa-engineer** agent with the evaluator prompt:

1. Read `references/grading-rubric.md` for the full scoring criteria
2. Read `references/anti-rationalization.md` and apply all 7 rules
3. Launch the application and test with Playwright (or manual browser inspection via agent-browser)
4. Score each of the 4 axes independently (1-10):
   - **Design Quality** -- visual hierarchy, spacing, typography, color
   - **Originality** -- distinctiveness, avoidance of generic/template aesthetics
   - **Craft** -- attention to detail, polish, micro-interactions, edge cases
   - **Functionality** -- features work correctly, responsive, accessible
5. Write a structured critique with specific, actionable feedback per axis
6. DO NOT rationalize low scores upward -- see anti-rationalization rules

### 3d: Score Gate

Check the evaluator's scores:
- If ALL four axes >= threshold: PASS. Proceed to Step 4.
- If ANY axis < threshold: FAIL. Feed the critique back to the generator (Step 3b) for another iteration.
- If max_iterations reached: STOP. Proceed to Step 4 with current scores.
- If budget_cap exceeded (check via `pixl cost summary` or estimate from token counts): STOP.

## Step 4: Report Results

Output a summary table to the user:

```
+--------------------+---------+
| Axis               | Score   |
+--------------------+---------+
| Design Quality     | 8/10    |
| Originality        | 7/10    |
| Craft              | 8/10    |
| Functionality      | 9/10    |
+--------------------+---------+
| Status             | PASS    |
| Iterations         | 3       |
| Total time         | 12m 34s |
| Artifacts created  | 47      |
+--------------------+---------+
```

If the harness failed (max iterations or budget cap hit), include the final evaluator critique and specific recommendations for what a human should address.

## Gotchas

- The evaluator and generator must be separate agents with separate contexts -- the evaluator must not have access to the generator's reasoning or excuses
- Never let the generator self-evaluate -- this defeats the adversarial structure
- The anti-rationalization protocol exists because LLM evaluators tend to be too generous; enforce it strictly
- Budget tracking is approximate when running in fallback mode (no pixl CLI) -- err on the side of stopping early
- If Playwright is not available, fall back to visual inspection via `/agent-browser` but note this in the report

---
name: ralph-loop-crew
description: "Enhanced ralph-loop with pixl-crew patterns. Use when asked to 'loop until done', 'iterate until passing', 'keep going until complete', or run persistent autonomous tasks with verification. Wraps ralph-loop with structured completion criteria, agent-based verification, and context packet output."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
argument-hint: "<task description>"
disable-model-invocation: true
---

## Overview

This skill wraps the `ralph-loop` plugin with pixl-crew conventions: structured completion criteria, crew agent verification, and context packet output. Instead of raw iteration prompts, it sets up a disciplined loop with measurable exit conditions.

## Step 1: Parse Task & Define Completion Criteria

From the user's task description (passed as argument or asked interactively):

1. **Extract the task** — what needs to be done
2. **Define measurable completion criteria** — concrete checks that prove the task is done
3. **Set iteration budget** — default 5, max 15 (ask user if ambiguous)

Examples of completion criteria:

- "fix all lint errors" → `npx eslint . --max-warnings 0` exits 0
- "make all tests pass" → `npm test` exits 0
- "refactor to DDD" → no lint errors + tests pass + reviewer agent finds no issues
- "build the feature" → builds + tests pass + type-check passes

## Step 2: Detect Project Tooling

Scan the project for available verification commands:

- **package.json** → `npm test`, `npm run lint`, `npm run build`, `npm run typecheck`
- **Makefile** → `make test`, `make lint`, `make check`
- **pyproject.toml** → `pytest`, `ruff check`, `mypy`
- **Cargo.toml** → `cargo test`, `cargo clippy`

Build a verification command list from what's available.

## Step 3: Write Ralph Loop Configuration

Create `.claude/ralph-loop.local.md` with the following structure:

````markdown
---
iteration: 0
max_iterations: { budget }
task: "{task summary}"
---

## Task

{Full task description from user}

## Completion Promise

The loop is complete when ALL of the following pass:

{Numbered list of completion criteria with exact commands}

## Verification Commands

Run these after each iteration to check progress:

```bash
{verification commands, one per line}
```
````

## Instructions

1. Read this file at the start of each iteration to get current state
2. Work on the task — make meaningful progress each iteration
3. Run all verification commands
4. Update the `iteration` count in frontmatter
5. If all completion criteria pass, announce completion
6. If not, note what remains and continue next iteration

````

## Step 4: Start the Loop

Tell the user:

- The ralph-loop configuration has been written to `.claude/ralph-loop.local.md`
- They should now invoke `/ralph-loop` to start the loop with the configured task
- The loop will use the completion criteria to know when to stop
- On completion, results will be available in the ralph-loop config

## Step 5: Generate Results Context Packet

After the loop completes (or when asked), write `.context/ralph-loop-results.json`:

```json
{
  "type": "ralph-loop-result",
  "task": "{task summary}",
  "iterations": {count},
  "max_iterations": {budget},
  "status": "completed | max_iterations_reached | cancelled",
  "completion_criteria": [
    { "criterion": "...", "passed": true/false }
  ],
  "summary": "{what was accomplished}",
  "remaining": ["{any unresolved items}"]
}
````

Create the `.context/` directory if it doesn't exist.

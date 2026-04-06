---
name: task-plan
description: "Structured task planning pipeline: discovery → decompose → detail → output. Breaks features and projects into dependency-aware, ordered task lists with acceptance criteria and execution strategy. Also adapts existing plans when requirements change (consumes /spec-review drift reports). Use when asked to 'plan tasks', 'break down a feature', 'create a roadmap', 'adapt the plan', or 'update tasks from spec changes'. Produces a task list that /sprint-planning can schedule into iterations."
allowed-tools: Read, Glob, Grep, Write, WebFetch, AskUserQuestion
argument-hint: "<description, file path to PRD, or URL>"
---

## Overview

This skill creates structured task plans for implementation work. Given a feature, project, or change request, it analyzes the scope, decomposes work into atomic tasks, adds acceptance criteria and dependency relationships, and outputs a complete execution plan.

**Why vertical slices over horizontal layers**: Vertical slices (each delivering user-visible value) provide faster feedback than horizontal layers (build all DB first, then all API, then all UI). If a vertical slice fails, you learn early; if a horizontal layer fails, you've built foundations for features that may never ship.

## Required References

Before starting, read `references/methodology/vertical-slice.md` for vertical slice decomposition patterns.

## Step 0: Input Parsing (conditional)

If the argument appears to be a file path (contains `/` or `.md` or `.txt` or `.pdf`):

1. Read the file using the Read tool
2. Extract requirements, user stories, and acceptance criteria from the document
3. Summarize the key features and scope before proceeding to Step 1

If the argument appears to be a URL:

1. Fetch the URL content using WebFetch
2. Extract requirements from the page content
3. Summarize before proceeding

Otherwise, treat the argument as a direct feature description and proceed to Step 0.5 (if applicable) or Step 1.

## Step 0.5: Drift-Aware Replanning (conditional)

If `.context/spec/coverage-<latest>.json` exists (produced by `/spec-review`):

1. **Load coverage report**: Read the most recent `coverage-*.json` from `.context/spec/`
2. **Load existing task plan**: Read `.context/task-state.json` if it exists
3. **Cross-reference**: Match coverage results against existing tasks:
   - `missing` requirements with no corresponding task → **new tasks needed**
   - `added` drift entries (from `drift-log.jsonl`) → **new tasks needed**
   - `removed` drift entries → **existing tasks may be irrelevant**
   - `reprioritized` drift entries → **existing tasks may need reordering**
4. **Present adaptation summary** to the user via AskUserQuestion:
   - New tasks to add (from missing/added requirements)
   - Tasks to remove or deprioritize (from removed requirements)
   - Tasks to reorder (from reprioritized requirements)
   - User confirms before changes are applied
5. **Merge into existing plan**: Update `.context/task-state.json` with adaptations, then proceed to Step 1 for any new work

Skip this step if no coverage report exists.

## Step 1: Discovery

Analyze the feature or project scope:

1. Understand requirements from the user's description (or parsed PRD)
2. Explore affected codebase areas
3. Identify external dependencies and constraints
4. Establish the boundaries of the work
5. Note existing patterns and conventions to follow

## Step 2: Decompose

Break the work into atomic, ordered tasks:

1. Identify vertical slices (each delivers user-visible value)
2. Estimate size for each task (S = <1hr, M = 1-3hr, L = 3-8hr)
3. Split any L tasks into smaller pieces
4. Identify parallelizable groups
5. Establish rough ordering by dependency

## Step 3: Detail

Enrich each task with:

- **Acceptance criteria** — Testable checkboxes
- **Implementation hints** — Key patterns, files to modify, approach notes
- **Dependencies** — blocks/blockedBy relationships
- **Suggested agent** — Which crew agent should handle this
- **Verification steps** — How to confirm the task is done

## Step 4: Output

Generate the final plan:

- Structured task list with IDs, titles, descriptions, sizes, and acceptance criteria
- Dependency graph showing blocks/blockedBy relationships
- **Critical path** (algorithmically computed when pixl engine is available):
  ```bash
  python3 -c "
  import json
  try:
      from pixl.utils.task_graph import validate_task_graph, compute_critical_path, compute_execution_order
      tasks = json.load(open('.context/task-state.json'))['tasks']
      result = validate_task_graph(tasks)
      if not result.valid:
          for err in result.errors: print(f'ERROR: {err}')
      else:
          path = compute_critical_path(tasks)
          order = compute_execution_order(tasks)
          print(f'Critical path: {\" -> \".join(path)}')
          print(f'Execution order: {order}')
  except ImportError:
      print('pixl engine not installed — use LLM-inferred critical path.')
  except (FileNotFoundError, KeyError):
      print('task-state.json not found — use LLM-inferred critical path.')
  "
  ```
  Fall back to LLM-inferred critical path if engine unavailable.
- Suggested execution order optimized for parallelism
- Summary statistics: total tasks, size distribution, estimated effort

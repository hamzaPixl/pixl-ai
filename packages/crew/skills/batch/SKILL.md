---
name: batch
description: "Decompose a transformation into independent units, execute each in a worktree-isolated agent, merge results or create per-unit PRs. Use when applying the same change across many files/modules, running parallel migrations, or batch-processing independent tasks."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
argument-hint: "<transformation description + target scope>"
context: fork
---

## Overview

Parallel worktree execution engine. Takes a transformation (refactor, migration, code mod, style change) and a target scope (files, modules, services), decomposes into N independent units, executes each in its own git worktree via isolated agents, then merges results.

**Why worktree isolation matters**: Each agent gets its own copy of the repo. No file conflicts during execution. Merge conflicts only surface at the explicit merge step — where they can be resolved intelligently instead of causing mid-execution failures.

## Step 1: Analyze Scope

Identify the transformation and target scope:

1. Parse the user's description to extract:
   - **Transformation**: What change to apply (e.g., "migrate from Jest to Vitest", "add error boundaries to all pages")
   - **Target scope**: Which files/modules to transform (e.g., `src/modules/*/`, `**/*.test.ts`)
2. Scan the target scope with Glob/Grep to enumerate candidate files
3. Verify each candidate is a valid transformation target

## Step 2: Decompose

Split the scope into N independent units (max 10):

1. Group files by natural boundaries (module, directory, feature area)
2. Verify independence — units must NOT share files (a file belongs to exactly one unit)
3. For each unit, define:
   - **Files**: List of files in this unit
   - **Prompt**: Focused transformation instruction for this unit
   - **Success criteria**: How to verify the transformation worked (tests pass, type-checks, lint clean)

Present the decomposition table to the user:

```
Unit | Files        | Description
-----|-------------|------------------------------------------
1    | src/auth/*  | Migrate auth module tests from Jest to Vitest
2    | src/billing/*| Migrate billing module tests from Jest to Vitest
...
```

Ask for confirmation before proceeding. The user may adjust units, exclude files, or modify the transformation.

## Step 3: Execute in Parallel

Spawn up to 10 agents in parallel, each with `isolation: "worktree"`:

```
For each unit:
  Agent(
    isolation: "worktree",
    prompt: "Transform these files: [file list]. Apply: [transformation]. Success: [criteria]. Do NOT modify files outside your scope."
  )
```

Key rules:
- Each agent gets a focused, self-contained prompt — no ambient context
- Each agent must run verification (tests, typecheck) within its worktree before completing
- Failed agents do NOT block successful ones
- Use `references/methodology/parallel-execution.md` wave sizing: 2-3 agents per wave for large batches

## Step 4: Collect Results

Wait for all agents to complete. Build a results table:

```
Unit | Status  | Files Changed | Tests | Notes
-----|---------|---------------|-------|------------------
1    | pass    | 4             | 12/12 | Clean migration
2    | partial | 3             | 8/10  | 2 snapshot tests need manual update
3    | fail    | 0             | -     | Circular dependency blocked transform
```

## Step 5: Merge Strategy

Present the results and ask the user to choose a merge strategy:

- **(a) One PR per unit** — Each successful unit gets its own branch + PR via `gh pr create`
- **(b) Merge all into single branch** — Cherry-pick all successful units into one branch + one PR
- **(c) Apply to current branch** — Apply changes directly to the working tree (no PRs)

For options (a) and (b), use `git` to manage branches and `gh` for PR creation.

Failed units are reported but not merged. The user can re-run `/batch` on failed units after manual investigation.

## Step 6: Report

Output a final summary:

```
Batch Complete
==============
Transformation: [description]
Units: [N total] | [passed] passed | [failed] failed | [partial] partial
Files changed: [total across all successful units]
Merge strategy: [chosen strategy]
PRs created: [list of PR URLs, if applicable]

Failed units (manual attention needed):
- Unit 3: [reason]
```

## Constraints

| Parameter   | Value | Rationale                                   |
|-------------|-------|---------------------------------------------|
| Max units   | 10    | Claude Code worktree concurrency limit       |
| Wave size   | 2-3   | Per `parallel-execution.md` recommendations  |
| Scope guard | strict| Each unit's files must be non-overlapping    |

## Related Skills

- **`/self-review-fix-loop`** — Run after batch to review all changes across units
- **`/pr-creation`** — Used internally for PR creation when merge strategy is (a) or (b)
- **`/migration-plan`** — Plan the migration first, then execute with `/batch`

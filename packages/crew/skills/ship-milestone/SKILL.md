---
name: ship-milestone
description: "End-to-end milestone shipping: gap analysis → implementation → user testing → docs → commits → push. Use when asked to 'ship this milestone', 'close these gaps', 'implement and release', 'take this from analysis to production', or 'finish and ship the remaining work'."
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, Agent, Task]
argument-hint: "<spec-or-analysis-file> or description of what to ship"
---

## Overview

Ship a body of work from analysis through implementation, testing, documentation, and release. Orchestrates the full lifecycle: assess what exists, plan what remains, implement in parallel, test as a user, update all docs, commit in logical groups, and push.

Read `references/workflow.md` for the detailed phase checklist.

## Step 1: Assess Current State

Parse the input (spec file, architecture analysis, or description) to build a gap inventory.

1. Read the spec/analysis document
2. Launch Explore agents to deep-scan what is **actually implemented** vs. what the doc claims
3. Reassess each item — real completion is often higher than documented
4. Produce a revised status table: done / partial / not started / dropped

**Output**: Status table with accurate completion percentages.

## Step 2: Plan Remaining Work

Use `/task-plan` methodology for remaining items:

1. Group work into vertical slices (each delivers testable value)
2. Size tasks (S < 1hr, M = 1-3hr)
3. Split any L tasks
4. Map dependencies and identify parallel groups
5. Determine wave execution order

**Output**: Task list with IDs, sizes, dependencies, and wave assignments.

## Step 3: Implement (Parallel Waves)

Execute implementation wave by wave:

1. Start all independent tasks in Wave 1 simultaneously
2. Use background agents for test-heavy or cross-boundary tasks
3. Handle engine/CLI/infra changes directly for surgical edits
4. Mark tasks complete as they finish
5. Run `make test` (or equivalent) after each wave to catch regressions
6. Start Wave 2+ only after dependencies from prior waves complete

## Step 4: User-Flow Testing

Test every feature **as documented in USAGE.md** (or equivalent user guide):

1. Run `--help` for every new command group
2. Test CRUD cycles (create → list → get → update → delete)
3. Test JSON output mode (`--json`)
4. Test error paths (missing config, connection refused, invalid input)
5. Test streaming/real-time features if applicable
6. Verify simulated/dry-run modes work

**Critical**: Do not skip this step. Document test results.

## Step 5: Update Documentation

Update **all** project documentation to reflect the new state:

1. **CHANGELOG.md** — comprehensive release notes grouped by feature area
2. **README.md** — component descriptions, CLI reference table, architecture sections
3. **USAGE.md** — version bump, new sections for every new user-facing feature
4. **CLAUDE.md** — structure tree, storage layer, CLI reference
5. **Package READMEs** — engine, CLI, sandbox, or whichever packages changed

Scan for all `README.md` and doc files in the repo. Update any that reference changed components.

## Step 6: Commit and Push

Create logical commits grouped by feature area (not one per file):

1. Group related changes into 4-8 commits (not 20+)
2. Use conventional commit format: `type(scope): description`
3. Include `Co-Authored-By` trailer
4. Verify no temp files committed (plan files, memory, build artifacts)
5. Run full test suite one final time before push
6. Push to remote

## Step 7: Summary

Output a final shipping report:

- Items closed vs. deferred (with reasons)
- Test count and status
- Commit list with short descriptions
- Doc files updated
- Any known issues or follow-ups

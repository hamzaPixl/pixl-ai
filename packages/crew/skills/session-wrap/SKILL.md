---
name: session-wrap
description: "End-of-session wrap-up: extract key decisions to .claude/memory/decisions.jsonl AND generate a portable handoff document. Use when ending a session, preserving decisions, or handing off work."
allowed-tools: Read, Write, Bash, Glob, Grep
argument-hint: "[optional output path for handoff]"
disable-model-invocation: true
---

## Overview

Combines decision capture and session handoff into a single end-of-session workflow. Produces two outputs:
1. Decisions appended to `.claude/memory/decisions.jsonl`
2. Handoff document at `.context/session-handoff-{date}.md`

## Step 1: Gather Context

### Git State

1. Run `git status` to get current branch and working tree state
2. Run `git diff --stat` for a summary of changed files
3. Run `git log --oneline -20` for recent commit history

### Task State

4. Call `TaskList` to get current task state
5. For each in-progress or pending task, call `TaskGet` for full details

### Memory Context

6. Check if `.claude/memory/decisions.jsonl` exists — create if missing
7. Read last 5 entries from `decisions.jsonl` (if any) to avoid duplicates
8. Check if `.claude/memory/sessions/` has recent summaries — read the latest

### Key Files

9. Identify the most important files from the git diff and task descriptions

## Step 2: Extract Decisions

Review the session and identify decisions in these categories:

| Category | Examples |
|----------|----------|
| **Architecture** | Chose pattern X over Y, added new module, restructured |
| **Technology** | Added dependency, chose library, configured tool |
| **Convention** | Established naming rule, coding standard, file structure |
| **Trade-off** | Accepted limitation, deferred work, chose simpler approach |
| **Bug fix** | Root cause identified, fix strategy chosen |

For each decision, capture:
- **what**: One-line summary (under 80 characters)
- **why**: Rationale (1-2 sentences, under 200 characters)
- **context**: Files or areas affected
- **category**: One of architecture, technology, convention, trade-off, bugfix

Append each as a single JSON line to `.claude/memory/decisions.jsonl`:

```jsonl
{"date":"2026-03-08","category":"architecture","what":"Added schema-audit skill","why":"Prompt analysis showed DB schema review as top uncovered workflow","context":"skills/schema-audit/"}
```

If pixl is available (`command -v pixl`), also persist each decision as a pixl artifact:
```bash
pixl artifact put --name "decision-<category>-$(date +%s)" --type decision --content '<json>'
```

## Step 3: Generate Handoff Document

Write the handoff to `.context/session-handoff-{date}.md` (or the user-specified path):

```markdown
# Session Handoff — {date}

## Current State

- Branch: {branch}
- Status: {clean/dirty}

## What's Been Done

{git log summary of session commits}

## What's In Progress

{current task list with status}

## Changed Files

{git diff --stat output}

## Key Decisions

{decisions captured in Step 2}

## How to Continue

1. {next steps based on open tasks}
2. {any blockers or notes}

## Important Files

{list of key files with brief descriptions}
```

## Step 4: Summary

Output a combined summary:

```
## Session Wrap-Up

### Decisions
Captured N decisions → `.claude/memory/decisions.jsonl`

| # | Category | Decision |
|---|----------|----------|
| 1 | arch     | Added schema-audit skill |
| 2 | tech     | Chose Prisma index analysis approach |

Total decisions in memory: M (N new + P existing)

### Handoff
Written to `.context/session-handoff-{date}.md`
Paste this into a new session's first message to restore context.
```

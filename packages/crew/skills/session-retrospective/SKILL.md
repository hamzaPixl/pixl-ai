---
name: session-retrospective
description: "Extract decisions from the current session and append to .claude/memory/decisions.jsonl. Finally populates the cross-session memory infrastructure. Use at the end of a session to capture what was decided, what was changed, and why."
allowed-tools: Read, Write, Bash, Glob, Grep
argument-hint: "[optional: specific decisions to capture]"
disable-model-invocation: true
---

## Overview

Captures session decisions into the persistent memory system. Reviews what was done in the current session, extracts key decisions, and appends them to `.claude/memory/decisions.jsonl` in the standard format.

## Step 1: Gather Session Context

1. Run `git log --oneline -20` to see recent commits in this session
2. Run `git diff --stat HEAD~5` (or appropriate range) to see what changed
3. Check if `.claude/memory/decisions.jsonl` exists — create if missing
4. Read the last 5 entries from `decisions.jsonl` (if any) to avoid duplicates

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
- **what**: One-line summary of the decision
- **why**: Rationale (1-2 sentences)
- **context**: Files or areas affected
- **category**: One of architecture, technology, convention, trade-off, bugfix

## Step 3: Format & Append

Each decision is a single JSON line appended to `.claude/memory/decisions.jsonl`:

```jsonl
{"date":"2026-03-08","category":"architecture","what":"Added schema-audit skill","why":"Prompt analysis showed DB schema review as top uncovered workflow","context":"skills/schema-audit/"}
```

If pixl is available (`command -v pixl`), also persist each decision as a pixl artifact:
```bash
pixl artifact put --name "decision-<category>-$(date +%s)" --type decision --content '<json>'
```
This makes decisions queryable across sessions via `pixl artifact search --query "decision" --type decision`.

Rules:
- One JSON object per line (JSONL format)
- Always include `date` in ISO format (YYYY-MM-DD)
- Keep `what` under 80 characters
- Keep `why` under 200 characters
- `context` is a comma-separated list of paths or areas

## Step 4: Summary

Output a summary of captured decisions:

```
## Session Retrospective

Captured N decisions → `.claude/memory/decisions.jsonl`

| # | Category | Decision |
|---|----------|----------|
| 1 | arch     | Added schema-audit skill |
| 2 | tech     | Chose Prisma index analysis approach |
| ...

Total decisions in memory: M (N new + P existing)
```

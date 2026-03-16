---
name: session-export
description: "Export current session context into a portable markdown handoff file. Use when handing off work to another person, resuming on another machine, or preserving session state for later."
allowed-tools: Read, Write, Bash, Glob, Grep
argument-hint: "[optional output path]"
disable-model-invocation: true
---

## Overview

Creates a self-contained session handoff document that captures everything needed to continue work in a new session or share context with a collaborator.

## Step 1: Gather Context

Collect the following information:

### Git State

1. Run `git status` to get current branch and working tree state
2. Run `git diff --stat` for a summary of changed files
3. Run `git log --oneline -10` for recent commit history

### Task State

4. Call `TaskList` to get current task state
5. For each in-progress or pending task, call `TaskGet` for full details

### Memory Context

6. Check if `.claude/memory/decisions.jsonl` exists — if so, read last 10 entries
7. Check if `.claude/memory/sessions/` has recent summaries — read the latest

### Key Files

8. Identify the most important files from the git diff and task descriptions

## Step 2: Generate Handoff Document

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

{recent decisions from memory log}

## How to Continue

1. {next steps based on open tasks}
2. {any blockers or notes}

## Important Files

{list of key files with brief descriptions}
```

## Step 3: Confirm

Report the handoff file path and its size. Remind the user they can paste this into a new session's first message to restore context.

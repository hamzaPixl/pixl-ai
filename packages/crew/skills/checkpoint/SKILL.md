---
name: checkpoint
description: "Save and restore full working context: branch, uncommitted changes, task state, decisions, and remaining work. Use when switching tasks, ending a session, pausing work, or resuming from where you left off."
allowed-tools: Read, Bash, Glob, Grep, Write
argument-hint: "<save [name] | restore [name] | list>"
---

## Overview

Unified state capture that saves everything needed to resume work exactly where you left off. Combines git state, task progress, and session decisions into a single checkpoint.

**How this differs from other skills**:
- `/task-persist` — saves task list only. This skill saves full working context (git + tasks + decisions).
- `/session-wrap` — captures session summary for handoff. This skill saves restorable state, not just a narrative.
- `/strategic-compact` — manages context window. This skill manages cross-session state.

## Mode Detection

```
/checkpoint save            → save checkpoint with auto-generated name
/checkpoint save billing    → save checkpoint named "billing"
/checkpoint restore         → restore most recent checkpoint
/checkpoint restore billing → restore checkpoint named "billing"
/checkpoint list            → list all saved checkpoints
```

## Save Mode

### Step 1: Capture Git State

```bash
BRANCH=$(git branch --show-current)
COMMIT=$(git rev-parse --short HEAD)
STATUS=$(git status --porcelain)
STASH_NEEDED=$([ -n "$STATUS" ] && echo "true" || echo "false")
```

If there are uncommitted changes:
```bash
git stash push -m "checkpoint: ${NAME:-auto}-$(date +%s)"
STASH_REF=$(git stash list | head -1 | cut -d: -f1)
```

### Step 2: Capture Task State

```bash
# From task-state.json if it exists
TASK_STATE=""
if [ -f ".context/task-state.json" ]; then
  TASK_STATE=$(cat .context/task-state.json)
fi
```

### Step 3: Capture Decisions

```bash
# Recent decisions from memory
DECISIONS=""
if [ -f ".claude/memory/decisions.jsonl" ]; then
  DECISIONS=$(tail -20 .claude/memory/decisions.jsonl)
fi
```

### Step 4: Capture Remaining Work

Summarize what's left to do based on:
- Open tasks in task state
- Uncommitted changes context
- Current branch purpose (from branch name)

### Step 5: Write Checkpoint

```bash
CHECKPOINT_DIR="${CLAUDE_PLUGIN_DATA:-${HOME}/.pixl/plugin-data}/checkpoints"
mkdir -p "$CHECKPOINT_DIR"

NAME="${1:-$(date +%Y%m%d-%H%M%S)}"

cat > "$CHECKPOINT_DIR/${NAME}.json" <<EOF
{
  "name": "${NAME}",
  "created": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "git": {
    "branch": "${BRANCH}",
    "commit": "${COMMIT}",
    "stash_ref": "${STASH_REF:-null}",
    "has_uncommitted": ${STASH_NEEDED}
  },
  "tasks": ${TASK_STATE:-null},
  "decisions": [${DECISIONS}],
  "remaining_work": "<summarized by Claude>",
  "project_dir": "$(pwd)"
}
EOF
```

Output:
```
Checkpoint saved: ${NAME}
  Branch: ${BRANCH} @ ${COMMIT}
  Stashed: ${STASH_NEEDED}
  Tasks: X pending, Y in progress, Z completed
  Location: ${CHECKPOINT_DIR}/${NAME}.json
```

## Restore Mode

### Step 1: Load Checkpoint

```bash
CHECKPOINT_DIR="${CLAUDE_PLUGIN_DATA:-${HOME}/.pixl/plugin-data}/checkpoints"
NAME="${1:-$(basename "$(ls -t "$CHECKPOINT_DIR"/*.json | head -1)" .json)}"
cat "$CHECKPOINT_DIR/${NAME}.json"
```

### Step 2: Restore Git State

```bash
# Switch to the checkpoint branch
git checkout "${BRANCH}"

# Restore stashed changes if any
if [ "${STASH_REF}" != "null" ]; then
  git stash pop "${STASH_REF}" 2>/dev/null || git stash apply "${STASH_REF}"
fi
```

### Step 3: Restore Context

Present to Claude/user:
- Branch and commit context
- Remaining work items
- Key decisions made before checkpoint
- Open tasks and their status

Output:
```
Checkpoint restored: ${NAME}
  Branch: ${BRANCH} @ ${COMMIT}
  Uncommitted changes: restored
  
  Remaining work:
  - <item 1>
  - <item 2>
  
  Key decisions:
  - <decision 1>
  - <decision 2>
```

## List Mode

```bash
CHECKPOINT_DIR="${CLAUDE_PLUGIN_DATA:-${HOME}/.pixl/plugin-data}/checkpoints"
ls -t "$CHECKPOINT_DIR"/*.json 2>/dev/null | while read f; do
  jq -r '"\(.name)\t\(.created)\t\(.git.branch)\t\(.git.commit)"' "$f"
done | column -t -s$'\t'
```

Output:
```
Name         Created              Branch           Commit
billing      2026-04-09T14:30:00Z feat/billing     a1b2c3d
auth-fix     2026-04-08T10:15:00Z fix/auth-race    e4f5g6h
```

## Gotchas

- Stash refs can become invalid after branch operations — checkpoint stores the stash message for recovery
- Restoring to a branch that was force-pushed will fail — checkpoint warns if commit no longer exists
- Large uncommitted changes (>1000 lines) should be committed instead of stashed — warn the user
- Checkpoint files are plain JSON — no secrets should be stored in them
- Multiple stashes from different checkpoints can collide — use unique stash messages

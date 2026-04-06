---
name: task-persist
description: "Save and restore task progress across sessions. Use when a multi-step task needs to survive context resets, session boundaries, or /compact operations."
allowed-tools: Read, Write, Bash, Glob
argument-hint: "<save | load>"
disable-model-invocation: true
---

## Overview

This skill persists task state to `.context/task-state.json` so work can resume across sessions.

## Step 1: Determine Mode

If argument is `save` (or no tasks exist in TaskList):
→ Go to Step 2 (Save)

If argument is `load` (or `.context/task-state.json` exists):
→ Go to Step 3 (Load)

## Step 2: Save Task State

1. Call `TaskList` to get all current tasks
2. For each task, call `TaskGet` to get full details
3. Write the complete task state to `.context/task-state.json`:

```json
{
  "savedAt": "ISO timestamp",
  "sessionId": "auto-generated",
  "tasks": [
    {
      "id": "original-id",
      "subject": "...",
      "description": "...",
      "status": "pending|in_progress|completed",
      "blockedBy": ["id1", "id2"],
      "blocks": ["id3"]
    }
  ]
}
```

4. **Validate dependency graph** before saving:
   ```bash
   python3 -c "
   import json, sys
   try:
       from pixl.utils.task_graph import validate_task_graph
       tasks = json.load(open('.context/task-state.json'))['tasks']
       result = validate_task_graph(tasks)
       if not result.valid:
           for err in result.errors:
               print(f'WARNING: {err}', file=sys.stderr)
           sys.exit(1)
       print(f'Graph valid: {len(tasks)} tasks, no cycles or orphan refs.')
   except ImportError:
       print('pixl engine not installed — skipping graph validation.')
   "
   ```
   - If cycles or orphan refs detected: warn the user with the specific errors and ask whether to save anyway
   - If pixl engine not installed: skip validation gracefully
5. If pixl is available, also persist task state to the DB:
   ```bash
   pixl artifact put --name task-state --type task_state --content "$(cat .context/task-state.json)"
   ```
6. Report how many tasks were saved

## Step 3: Load Task State

1. Read `.context/task-state.json`
2. Filter to only `pending` and `in_progress` tasks (skip completed)
3. For each task, call `TaskCreate` with the original subject, description, and activeForm
4. After all tasks are created, restore dependency relationships using `TaskUpdate` with `addBlockedBy`
5. Report how many tasks were restored
6. Show the user which tasks are ready to work on (not blocked)

## Notes

- The save file location `.context/task-state.json` is checked by session-start.sh to remind users
- Old save files are overwritten — only the latest state matters
- Completed tasks are not restored to avoid clutter

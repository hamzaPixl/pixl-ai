---
name: task-persist
description: "Save and restore task state across sessions. On save: serializes current TaskList to .context/task-state.json. On load: reads the file and recreates tasks via TaskCreate. Use when ending a session with unfinished tasks or resuming work from a previous session."
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

4. If pixl is available, also persist task state to the DB:
   ```bash
   pixl artifact put --name task-state --type task_state --content "$(cat .context/task-state.json)"
   ```
5. Report how many tasks were saved

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

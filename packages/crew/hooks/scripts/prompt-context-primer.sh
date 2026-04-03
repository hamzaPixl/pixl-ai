#!/usr/bin/env bash
# UserPromptSubmit hook: inject active task context when user submits a prompt.
# Reads .context/task-state.json and emits in-progress tasks as system context.
# Advisory (non-blocking) — always exits 0.

source "$(dirname "$0")/_common.sh"

read_stdin
require_jq

# Find task-state.json
TASK_STATE=""
for candidate in ".context/task-state.json" ".claude/task-state.json"; do
  if [[ -f "$candidate" ]]; then
    TASK_STATE="$candidate"
    break
  fi
done

if [[ -z "$TASK_STATE" ]]; then
  exit 0
fi

# Extract in-progress and pending tasks
IN_PROGRESS=$(jq -r '.tasks[]? | select(.status == "in_progress") | "  [active] \(.subject)"' "$TASK_STATE" 2>/dev/null)
PENDING=$(jq -r '.tasks[]? | select(.status == "pending") | "  [next] \(.subject)"' "$TASK_STATE" 2>/dev/null | head -3)

if [[ -z "$IN_PROGRESS" && -z "$PENDING" ]]; then
  exit 0
fi

# Emit as system message context
{
  echo "### Pending Task State"
  if [[ -n "$IN_PROGRESS" ]]; then
    echo "$IN_PROGRESS"
  fi
  if [[ -n "$PENDING" ]]; then
    echo "$PENDING"
  fi
  echo "Run \`/task-persist\` to reload tasks from the previous session."
} >&2

exit 0

#!/usr/bin/env bash
# PostToolUse hook: periodically remind agent of active tasks to prevent drift.
# Fires every ~25 tool calls. Reads .context/task-state.json for in-progress tasks.
# Advisory (non-blocking) — emits to stderr only.

source "$(dirname "$0")/_common.sh"

read_stdin
require_jq

# Track call count via a temp file
COUNTER_FILE="/tmp/pixl-goal-check-counter-$$"
if [[ -z "${PIXL_SESSION_ID:-}" ]]; then
  COUNTER_FILE="/tmp/pixl-goal-check-counter"
fi

COUNT=0
if [[ -f "$COUNTER_FILE" ]]; then
  COUNT=$(cat "$COUNTER_FILE" 2>/dev/null || echo 0)
fi
COUNT=$((COUNT + 1))
echo "$COUNT" > "$COUNTER_FILE"

# Only fire every 25 tool calls
INTERVAL="${PIXL_GOAL_CHECK_INTERVAL:-25}"
if (( COUNT % INTERVAL != 0 )); then
  exit 0
fi

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

# Extract in-progress task subjects
IN_PROGRESS=$(jq -r '.tasks[]? | select(.status == "in_progress") | .subject' "$TASK_STATE" 2>/dev/null | head -5)

if [[ -z "$IN_PROGRESS" ]]; then
  exit 0
fi

TASK_COUNT=$(echo "$IN_PROGRESS" | wc -l | tr -d ' ')
echo "Goal check ($COUNT tool calls) — $TASK_COUNT active task(s):" >&2
echo "$IN_PROGRESS" | while read -r task; do
  echo "  - $task" >&2
done

exit 0

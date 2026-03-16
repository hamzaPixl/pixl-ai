#!/usr/bin/env bash
# PostToolUse hook: warn when context is likely getting large.
# Counts tool invocations via a session counter file.
# Advisory — suggests /strategic-compact or /clear.

source "$(dirname "$0")/_common.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
MEMORY_DIR="$PROJECT_DIR/.claude/memory"

if [[ ! -d "$MEMORY_DIR" ]]; then
  exit 0
fi

COUNTER_FILE="$MEMORY_DIR/.session-tool-count"

# Increment counter
COUNT=0
if [[ -f "$COUNTER_FILE" ]]; then
  COUNT=$(cat "$COUNTER_FILE" 2>/dev/null || echo "0")
fi
COUNT=$((COUNT + 1))
echo "$COUNT" > "$COUNTER_FILE"

# Warn at thresholds
case "$COUNT" in
  50)
    echo "Context budget reminder: 50 tool calls this session. Consider using /strategic-compact or /clear if switching tasks." >&2
    ;;
  100)
    echo "Context budget warning: 100 tool calls this session. Strongly recommend /strategic-compact to preserve key context before compaction." >&2
    ;;
  150)
    echo "Context budget critical: 150 tool calls. Run /strategic-compact now or delegate remaining work to a subagent." >&2
    ;;
esac

exit 0

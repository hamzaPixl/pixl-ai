#!/usr/bin/env bash
# PostToolUse hook: log PR URLs created via gh CLI.
# Captures PR URLs from Bash tool output for session history.

source "$(dirname "$0")/_common.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
MEMORY_DIR="$PROJECT_DIR/.claude/memory"

# Skip if neither memory directory nor pixl is available
if [[ ! -d "$MEMORY_DIR" ]] && ! $PIXL_AVAILABLE; then
  exit 0
fi

# Read tool output from stdin
read_stdin
require_jq

TOOL_OUTPUT=$(jq_input -r '.tool_output // empty')

if [[ -z "$TOOL_OUTPUT" ]]; then
  exit 0
fi

# Check if output contains a GitHub PR URL
PR_URL=$(echo "$TOOL_OUTPUT" | grep -oE 'https://github\.com/[^/]+/[^/]+/pull/[0-9]+' | head -1)

if [[ -n "$PR_URL" ]]; then
  TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  ENTRY="{\"timestamp\":\"$TIMESTAMP\",\"type\":\"pr_created\",\"url\":\"$PR_URL\"}"
  if $PIXL_AVAILABLE; then
    pixl_put "decision-pr-$(date +%s)" "decision" "$ENTRY"
  else
    echo "$ENTRY" >> "$MEMORY_DIR/decisions.jsonl"
  fi
  echo "PR logged: $PR_URL" >&2
fi

exit 0

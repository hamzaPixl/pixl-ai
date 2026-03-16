#!/usr/bin/env bash
# PostToolUse observer: track tool usage patterns for continuous learning.
# Appends lightweight observations to .claude/memory/tool-usage.jsonl

source "$(dirname "$0")/_common.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
MEMORY_DIR="$PROJECT_DIR/.claude/memory"

# Skip if neither memory directory nor pixl is available
if [[ ! -d "$MEMORY_DIR" ]] && ! $PIXL_AVAILABLE; then
  exit 0
fi

USAGE_FILE="$MEMORY_DIR/tool-usage.jsonl"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Read tool name and input from stdin (single capture fixes double-stdin bug)
read_stdin
require_jq

TOOL_NAME=$(jq_input -r '.tool_name // empty')
FILE_PATH=$(jq_input -r '.tool_input.file_path // empty')

if [[ -z "$TOOL_NAME" ]]; then
  exit 0
fi

# Determine file extension for pattern tracking
EXT=""
if [[ -n "$FILE_PATH" ]]; then
  EXT="${FILE_PATH##*.}"
fi

# Log lightweight usage entry (no content, just metadata)
ENTRY="{\"ts\":\"$TIMESTAMP\",\"tool\":\"$TOOL_NAME\",\"ext\":\"$EXT\"}"
if $PIXL_AVAILABLE; then
  pixl_put "tool-usage-$(date +%s)" "tool_usage" "$ENTRY"
else
  echo "$ENTRY" >> "$USAGE_FILE"
fi

# Keep file from growing unbounded (max 1000 entries)
if [[ -f "$USAGE_FILE" ]]; then
  LINE_COUNT=$(wc -l < "$USAGE_FILE")
  if [[ "$LINE_COUNT" -gt 1000 ]]; then
    tail -500 "$USAGE_FILE" > "$USAGE_FILE.tmp" && mv "$USAGE_FILE.tmp" "$USAGE_FILE"
  fi
fi

exit 0

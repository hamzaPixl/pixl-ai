#!/usr/bin/env bash
# PreCompact hook: save session state before context compaction.
# Captures current task context, modified files, and recent decisions
# so they survive the compaction window.

source "$(dirname "$0")/_common.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
MEMORY_DIR="$PROJECT_DIR/.claude/memory"

# Skip if neither memory directory nor pixl is available
if [[ ! -d "$MEMORY_DIR" ]] && ! $PIXL_AVAILABLE; then
  exit 0
fi

TIMESTAMP=$(date +"%Y-%m-%d-%H-%M-%S")
COMPACT_FILE="$MEMORY_DIR/pre-compact-$TIMESTAMP.md"

# Gather current git state
BRANCH=$(cd "$PROJECT_DIR" && git branch --show-current 2>/dev/null || echo "unknown")
STAGED=$(cd "$PROJECT_DIR" && git diff --cached --name-only 2>/dev/null || echo "")
MODIFIED=$(cd "$PROJECT_DIR" && git diff --name-only 2>/dev/null || echo "")
UNTRACKED=$(cd "$PROJECT_DIR" && git ls-files --others --exclude-standard 2>/dev/null | head -20 || echo "")

# Build compact snapshot content
COMPACT_CONTENT="# Pre-Compact Snapshot — $TIMESTAMP

**Branch**: $BRANCH

## Staged Files
$STAGED

## Modified Files
$MODIFIED

## Untracked Files (first 20)
$UNTRACKED"

# Append recent decisions if available
if [[ -f "$MEMORY_DIR/decisions.jsonl" ]]; then
  RECENT=$(tail -5 "$MEMORY_DIR/decisions.jsonl" 2>/dev/null)
  if [[ -n "$RECENT" ]]; then
    COMPACT_CONTENT="$COMPACT_CONTENT

## Recent Decisions
\`\`\`jsonl
$RECENT
\`\`\`"
  fi
fi

# Append task state if available
TASK_STATE="$PROJECT_DIR/.context/task-state.json"
if [[ -f "$TASK_STATE" ]]; then
  TASK_JSON=$(cat "$TASK_STATE")
  COMPACT_CONTENT="$COMPACT_CONTENT

## Task State
\`\`\`json
$TASK_JSON
\`\`\`"
fi

# Write to pixl DB (primary) or file (fallback) — not both
if $PIXL_AVAILABLE; then
  pixl_put "pre-compact-$TIMESTAMP" "compact_snapshot" "$COMPACT_CONTENT"
else
  echo "$COMPACT_CONTENT" > "$COMPACT_FILE"
fi

# Output reminder for Claude
echo "Context compaction detected. Session state saved. Review pre-compact snapshot after compaction to restore context."

exit 0

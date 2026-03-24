#!/usr/bin/env bash
# Stop hook: write session summary deterministically (no Claude involvement)
# Captures git diff stats, modified files, and preserves task state

source "$(dirname "$0")/_common.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
MEMORY_DIR="$PROJECT_DIR/.claude/memory"
SESSIONS_DIR="$MEMORY_DIR/sessions"

# Skip if neither memory directory nor pixl is available
if [[ ! -d "$MEMORY_DIR" ]] && ! $PIXL_AVAILABLE; then
  exit 0
fi

# Ensure sessions directory exists (for file-based fallback)
mkdir -p "$SESSIONS_DIR" 2>/dev/null || true

TIMESTAMP=$(date +"%Y-%m-%d-%H-%M")
SUMMARY_FILE="$SESSIONS_DIR/$TIMESTAMP.md"

# Gather git info (silently fail if not a git repo)
DIFF_STAT=$(cd "$PROJECT_DIR" && git diff --stat HEAD~1 2>/dev/null || echo "No recent commits")
MODIFIED_FILES=$(cd "$PROJECT_DIR" && git diff --name-only HEAD~1 2>/dev/null || echo "unknown")
BRANCH=$(cd "$PROJECT_DIR" && git branch --show-current 2>/dev/null || echo "unknown")
LAST_COMMITS=$(cd "$PROJECT_DIR" && git log --oneline -5 2>/dev/null || echo "No commits")

# Build summary content
SUMMARY_CONTENT="# Session Summary — $TIMESTAMP

**Branch**: $BRANCH

## Recent Commits
\`\`\`
$LAST_COMMITS
\`\`\`

## Files Changed (vs previous commit)
\`\`\`
$DIFF_STAT
\`\`\`

## Modified Files
$MODIFIED_FILES"

# Preserve task state if it exists
TASK_STATE="$PROJECT_DIR/.context/task-state.json"
if [[ -f "$TASK_STATE" ]]; then
  SUMMARY_CONTENT="$SUMMARY_CONTENT

## Task State
Task state preserved at \`.context/task-state.json\`"
fi

# Write to pixl DB (primary) or file (fallback) — not both
if $PIXL_AVAILABLE; then
  pixl_put "session-summary-$TIMESTAMP" "session_summary" "$SUMMARY_CONTENT"
  pixl knowledge build 2>/dev/null || true
else
  echo "$SUMMARY_CONTENT" > "$SUMMARY_FILE"
fi

exit 0

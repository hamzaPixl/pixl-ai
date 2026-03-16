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

cat > "$SUMMARY_FILE" << EOF
# Session Summary — $TIMESTAMP

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
$MODIFIED_FILES
EOF

# Store in pixl DB as the primary location
if $PIXL_AVAILABLE; then
  pixl_put "session-summary-$TIMESTAMP" "session_summary" "$(cat "$SUMMARY_FILE")"
fi

# Preserve task state if it exists
TASK_STATE="$PROJECT_DIR/.context/task-state.json"
if [[ -f "$TASK_STATE" ]]; then
  echo "" >> "$SUMMARY_FILE"
  echo "## Task State" >> "$SUMMARY_FILE"
  echo "Task state preserved at \`.context/task-state.json\`" >> "$SUMMARY_FILE"
fi

# Rebuild pixl knowledge index for changed files
if $PIXL_AVAILABLE; then
  pixl knowledge build 2>/dev/null || true
fi

exit 0

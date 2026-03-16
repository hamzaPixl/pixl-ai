#!/usr/bin/env bash
# _pixl-detect.sh — shared pixl CLI detection and helpers.
# Source this after _common.sh. Provides:
#   PIXL_AVAILABLE    (bool) — whether `pixl` binary is on PATH
#   PIXL_IN_WORKFLOW  (bool) — whether we're inside a pixl workflow stage
#   pixl_put          — store artifact (graceful no-op if pixl unavailable)
#   pixl_get          — retrieve artifact content (graceful no-op)
#   pixl_search       — search artifacts (graceful no-op)

PIXL_AVAILABLE=false
PIXL_IN_WORKFLOW=false
_PIXL_PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"

if command -v pixl &>/dev/null; then
  PIXL_AVAILABLE=true
  # Auto-init .pixl/ if missing
  if [ ! -d "$_PIXL_PROJECT_DIR/.pixl" ]; then
    pixl --project "$_PIXL_PROJECT_DIR" project init 2>/dev/null || true
  fi
fi

if [ -n "${PIXL_SESSION_ID:-}" ]; then
  PIXL_IN_WORKFLOW=true
fi

# Helper: store artifact (graceful no-op if pixl unavailable)
# Usage: pixl_put <name> <type> <content>
pixl_put() {
  if $PIXL_AVAILABLE; then
    pixl --json artifact put --name "$1" --type "$2" --content "$3" 2>/dev/null || true
  fi
}

# Helper: retrieve artifact content
# Usage: pixl_get <name> → outputs content or empty
pixl_get() {
  if $PIXL_AVAILABLE; then
    pixl --json artifact get --name "$1" 2>/dev/null | jq -r '.content // empty' 2>/dev/null || true
  fi
}

# Helper: search artifacts
# Usage: pixl_search <query> <type> <limit>
pixl_search() {
  if $PIXL_AVAILABLE; then
    pixl --json artifact search --query "$1" --type "${2:-}" --limit "${3:-5}" 2>/dev/null || echo '[]'
  fi
}

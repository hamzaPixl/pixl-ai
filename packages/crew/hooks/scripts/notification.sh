#!/usr/bin/env bash
# Cross-platform notification when Claude needs attention.
# macOS: osascript, Linux: notify-send, fallback: terminal bell.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_common.sh
source "${SCRIPT_DIR}/_common.sh"

read_stdin

# Extract notification message from stdin (if available)
MESSAGE="Claude needs your attention"
if [ -n "${STDIN_INPUT:-}" ]; then
  CONTEXT=$(echo "$STDIN_INPUT" | jq -r '.message // empty' 2>/dev/null || true)
  if [ -n "$CONTEXT" ]; then
    MESSAGE="$CONTEXT"
  fi
fi

TITLE="pixl-crew"

if [[ "$OSTYPE" == "darwin"* ]]; then
  osascript -e "display notification \"${MESSAGE}\" with title \"${TITLE}\"" 2>/dev/null || true
elif command -v notify-send &>/dev/null; then
  notify-send "$TITLE" "$MESSAGE" 2>/dev/null || true
else
  # Terminal bell fallback
  printf '\a' 2>/dev/null || true
fi

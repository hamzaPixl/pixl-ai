#!/usr/bin/env bash
# Cross-platform notification when Claude needs attention.
# macOS: osascript, Linux: notify-send, fallback: terminal bell.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_common.sh
source "${SCRIPT_DIR}/_common.sh"

read_stdin

# Notification style: "alert" (permission prompts) or "subtle" (idle/other)
STYLE="${1:-subtle}"

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
  if [ "$STYLE" = "alert" ]; then
    # Alert: notification with sound for permission prompts
    osascript -e "display notification \"${MESSAGE}\" with title \"${TITLE}\" sound name \"Ping\"" 2>/dev/null || true
  else
    # Subtle: silent notification for idle prompts
    osascript -e "display notification \"${MESSAGE}\" with title \"${TITLE}\"" 2>/dev/null || true
  fi
elif command -v notify-send &>/dev/null; then
  if [ "$STYLE" = "alert" ]; then
    notify-send -u critical "$TITLE" "$MESSAGE" 2>/dev/null || true
  else
    notify-send -u low "$TITLE" "$MESSAGE" 2>/dev/null || true
  fi
else
  # Terminal bell fallback
  printf '\a' 2>/dev/null || true
fi

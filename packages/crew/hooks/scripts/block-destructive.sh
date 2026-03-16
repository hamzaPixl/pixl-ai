#!/usr/bin/env bash
# PreToolUse hook: block destructive commands deterministically
# Exit 0 = allow, Exit 2 = block

source "$(dirname "$0")/_common.sh"

read_stdin
require_jq

COMMAND=$(jq_input -r '.tool_input.command // empty')

if [ -z "$COMMAND" ]; then
  exit 0
fi

if echo "$COMMAND" | grep -iEq 'rm\s+-rf\s+/|rm\s+-rf\s+\.|rm\s+-rf\s+\*|git\s+push\s+--force|git\s+push\s+-f|git\s+branch\s+-D\s+(main|master)|DROP\s+TABLE|DROP\s+DATABASE|TRUNCATE|git\s+reset\s+--hard\s*$|git\s+clean\s+-fd|>\s*/dev/sda'; then
  echo "Destructive command blocked: pattern matched in '$COMMAND'" >&2
  exit 2
fi

exit 0

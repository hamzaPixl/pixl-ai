#!/usr/bin/env bash
# PreToolUse hook: declarative permission tiers from permissions.yaml.
# Reads config/permissions.yaml and evaluates always_deny / always_allow / ask_user.
# Exit 0 = allow, Exit 2 = block.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/_common.sh"

read_stdin
require_jq

TOOL_NAME=$(jq_input -r '.tool_name // empty')
COMMAND=$(jq_input -r '.tool_input.command // empty')
CONTENT=$(jq_input -r '(.tool_input.content // .tool_input.new_string // .tool_input.path // "")')

# Determine the text to check based on tool type.
case "$TOOL_NAME" in
  Bash)     CHECK_TEXT="$COMMAND" ;;
  Write|Edit) CHECK_TEXT="$CONTENT" ;;
  Read)     CHECK_TEXT=$(jq_input -r '.tool_input.file_path // .tool_input.path // ""') ;;
  *)        CHECK_TEXT="$COMMAND$CONTENT" ;;
esac

if [ -z "$CHECK_TEXT" ]; then
  exit 0
fi

# Locate permissions.yaml — check project-local first, then crew config.
PERMISSIONS_FILE=""
for candidate in \
  ".claude/permissions.yaml" \
  "config/permissions.yaml" \
  "$SCRIPT_DIR/../../config/permissions.yaml"; do
  if [ -f "$candidate" ]; then
    PERMISSIONS_FILE="$candidate"
    break
  fi
done

if [ -z "$PERMISSIONS_FILE" ]; then
  # No config found — fall back to legacy behavior (allow).
  exit 0
fi

# Use python3 to parse YAML and evaluate rules.
RESULT=$(python3 -c "
import yaml, re, sys, json

tool = '$TOOL_NAME'
check = sys.stdin.read()
config_path = '$PERMISSIONS_FILE'

with open(config_path) as f:
    config = yaml.safe_load(f) or {}

def matches(rules, text, tool_name):
    for rule in (rules or []):
        tools_filter = rule.get('tools')
        if tools_filter and tool_name not in tools_filter:
            continue
        try:
            if re.search(rule['pattern'], text, re.IGNORECASE):
                return rule.get('reason', 'Rule matched')
        except re.error:
            pass
    return None

# Tier 1: always_deny (checked first)
reason = matches(config.get('always_deny'), check, tool)
if reason:
    print(json.dumps({'action': 'deny', 'reason': reason}))
    sys.exit(0)

# Tier 2: always_allow
reason = matches(config.get('always_allow'), check, tool)
if reason:
    print(json.dumps({'action': 'allow', 'reason': reason}))
    sys.exit(0)

# Tier 3: ask_user
reason = matches(config.get('ask_user'), check, tool)
if reason:
    print(json.dumps({'action': 'ask', 'reason': reason}))
    sys.exit(0)

# No rule matched — allow by default.
print(json.dumps({'action': 'allow', 'reason': 'no rule matched'}))
" <<< "$CHECK_TEXT" 2>/dev/null) || {
  # Python failed (missing yaml, etc.) — allow to avoid breaking sessions.
  exit 0
}

ACTION=$(echo "$RESULT" | jq -r '.action // "allow"' 2>/dev/null || echo "allow")
REASON=$(echo "$RESULT" | jq -r '.reason // ""' 2>/dev/null || echo "")

case "$ACTION" in
  deny)
    echo "Blocked: $REASON" >&2
    exit 2
    ;;
  ask)
    # In non-interactive mode (no TTY), auto-deny.
    if [ ! -t 0 ] && [ ! -t 1 ]; then
      echo "Permission required (non-interactive, auto-denied): $REASON" >&2
      exit 2
    fi
    # Interactive — the hook system will handle prompting via exit code.
    # Exit 0 to allow, as Claude Code's own permission system handles ask_user.
    # We log the reason so the user knows why they're being prompted.
    echo "Permission check: $REASON" >&2
    exit 0
    ;;
  *)
    exit 0
    ;;
esac

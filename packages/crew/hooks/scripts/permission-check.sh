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
# Pass tool name and config path via env vars (not string interpolation) to
# avoid shell injection if tool names contain special characters.
RESULT=$(PERM_TOOL="$TOOL_NAME" PERM_CONFIG="$PERMISSIONS_FILE" python3 -c "
import os, re, sys, json

try:
    import yaml
except ImportError:
    print(json.dumps({'action': 'allow', 'reason': 'PyYAML not installed'}))
    sys.exit(0)

tool = os.environ['PERM_TOOL']
check = sys.stdin.read()
config_path = os.environ['PERM_CONFIG']

with open(config_path) as f:
    config = yaml.safe_load(f) or {}

def matches(rules, text, tool_name):
    for rule in (rules or []):
        tools_filter = rule.get('tools')
        if tools_filter and tool_name not in tools_filter:
            continue
        try:
            flags = re.IGNORECASE if rule.get('case_insensitive', False) else 0
            if re.search(rule['pattern'], text, flags):
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
  # Python failed — allow to avoid breaking sessions.
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
    # In non-interactive contexts (CI, background agents, SDK bypassPermissions),
    # auto-deny. Hooks run with piped stdin so TTY detection is unreliable —
    # check PIXL_HOOK_PROFILE instead (minimal profile = non-interactive).
    if [ "${PIXL_HOOK_PROFILE:-standard}" = "minimal" ] || [ -n "${CI:-}" ]; then
      echo "Permission required (non-interactive, auto-denied): $REASON" >&2
      exit 2
    fi
    # Standard/strict profile: log the reason and allow — Claude Code's own
    # permission system will handle the actual user prompt for ask_user rules.
    echo "Permission check ($REASON) — Claude Code will prompt for approval" >&2
    exit 0
    ;;
  *)
    exit 0
    ;;
esac

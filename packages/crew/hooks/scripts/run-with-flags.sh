#!/bin/bash
# Hook profile orchestrator — wraps all hooks with profile-based filtering.
# Supports PIXL_HOOK_PROFILE=minimal|standard|strict and PIXL_DISABLED_HOOKS=id1,id2
#
# Usage in hooks.json:
#   "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/run-with-flags.sh <hook-id> <profile-level> <actual-script> [args...]"
#
# Profile levels:
#   minimal  — only critical hooks (destructive command blocking, secret detection)
#   standard — default: critical + quality (formatting, TDD, skill enforcement)
#   strict   — all hooks including advisory ones (console.log audit, typecheck)
#
# Hook levels (assigned per hook):
#   critical  — runs in minimal, standard, strict
#   quality   — runs in standard, strict
#   advisory  — runs in strict only

set -euo pipefail

HOOK_ID="${1:-}"
HOOK_LEVEL="${2:-quality}"
SCRIPT="${3:-}"
shift 3 2>/dev/null || true

if [[ -z "$HOOK_ID" || -z "$SCRIPT" ]]; then
  echo "run-with-flags: missing hook-id or script" >&2
  exit 0
fi

PROFILE="${PIXL_HOOK_PROFILE:-standard}"
DISABLED="${PIXL_DISABLED_HOOKS:-}"

# Check if hook is explicitly disabled
if [[ -n "$DISABLED" ]]; then
  IFS=',' read -ra DISABLED_LIST <<< "$DISABLED"
  for disabled_id in "${DISABLED_LIST[@]}"; do
    if [[ "${disabled_id// /}" == "$HOOK_ID" ]]; then
      exit 0
    fi
  done
fi

# Check if hook level is allowed by current profile
case "$PROFILE" in
  minimal)
    [[ "$HOOK_LEVEL" != "critical" ]] && exit 0
    ;;
  standard)
    [[ "$HOOK_LEVEL" == "advisory" ]] && exit 0
    ;;
  strict)
    # All levels run
    ;;
  *)
    # Unknown profile defaults to standard
    [[ "$HOOK_LEVEL" == "advisory" ]] && exit 0
    ;;
esac

# Execute the actual hook script, passing through stdin and remaining args
exec bash "$SCRIPT" "$@"

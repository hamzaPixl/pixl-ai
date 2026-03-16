#!/usr/bin/env bash
# _common.sh — shared preamble for pixl-crew hook scripts.
# Source this at the top of every hook script.
#
# Provides:
#   set -euo pipefail     (strict mode)
#   read_stdin             (captures stdin once into $STDIN_INPUT)
#   require_jq             (exits 0 if jq is missing — graceful skip)
#   jq_input               (pipes $STDIN_INPUT to jq with all args forwarded)
#
# Ordering contract: scripts that read stdin MUST call read_stdin BEFORE
# require_jq, ensuring stdin is always consumed even if jq is absent.

set -euo pipefail

# ─── Stdin Capture ─────────────────────────────────────────────────────────
# Captures stdin once into $STDIN_INPUT. Idempotent — safe to call multiple times.
STDIN_INPUT=""
_STDIN_READ=false

read_stdin() {
  if [[ "$_STDIN_READ" == "false" ]]; then
    STDIN_INPUT=$(cat)
    _STDIN_READ=true
  fi
}

# ─── jq Helpers ────────────────────────────────────────────────────────────
# Exits 0 (graceful skip) if jq is not available.
require_jq() {
  if ! command -v jq &>/dev/null; then
    exit 0
  fi
}

# Pipes $STDIN_INPUT to jq. Accepts all jq arguments.
jq_input() {
  echo "$STDIN_INPUT" | jq "$@"
}

# ─── Pixl CLI Detection ──────────────────────────────────────────────────
# Defaults (safe if _pixl-detect.sh is missing)
PIXL_AVAILABLE=false
PIXL_IN_WORKFLOW=false

# Source pixl detection helpers if available
_PIXL_DETECT="$(dirname "$0")/_pixl-detect.sh"
if [[ -f "$_PIXL_DETECT" ]]; then
  source "$_PIXL_DETECT"
fi

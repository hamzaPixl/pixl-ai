#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

CREW_ROOT_DEFAULT="__PIXL_CREW_ROOT__"
CREW_ROOT="${PIXL_CREW_ROOT:-}"

if [ -z "$CREW_ROOT" ] && [ -n "$CREW_ROOT_DEFAULT" ] && [ "$CREW_ROOT_DEFAULT" != "__PIXL_CREW_ROOT__" ] && [ -d "$CREW_ROOT_DEFAULT" ]; then
  CREW_ROOT="$CREW_ROOT_DEFAULT"
fi

if [ -z "$CREW_ROOT" ]; then
  CREW_ROOT="$ROOT/packages/crew"
fi

if [ ! -d "$CREW_ROOT" ]; then
  if command -v python3 >/dev/null 2>&1; then
    CREW_ROOT="$(python3 - <<'PY'
from pixl_cli.crew import get_crew_root
print(get_crew_root())
PY
)" || CREW_ROOT=""
  fi
fi

if [ -z "$CREW_ROOT" ] || [ ! -d "$CREW_ROOT" ]; then
  echo "pixl crew root not found; hooks disabled" >&2
  exit 0
fi

export CLAUDE_PLUGIN_ROOT="$CREW_ROOT"
export CLAUDE_PROJECT_DIR="$ROOT"

# Allow callers to override hook profile via env.
export PIXL_HOOK_PROFILE="${PIXL_HOOK_PROFILE:-standard}"

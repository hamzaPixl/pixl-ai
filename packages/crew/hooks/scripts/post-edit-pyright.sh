#!/usr/bin/env bash
# PostToolUse hook: run pyright or ruff check on edited .py files.
# Advisory (non-blocking) — reports errors to stderr, always exits 0.

source "$(dirname "$0")/_common.sh"

read_stdin
require_jq

FILE_PATH=$(jq_input -r '.tool_input.file_path // empty')

if [[ -z "$FILE_PATH" ]]; then
  exit 0
fi

# Only check Python files
case "$FILE_PATH" in
  *.py) ;;
  *) exit 0 ;;
esac

# Skip non-source files (tests, inits, migrations, skill/agent definitions)
if echo "$FILE_PATH" | grep -qE '(test_.*\.py$|_test\.py$|conftest\.py$|__init__\.py$|/migrations?/|/skills/|/agents/|/hooks/|/references/|\.tmpl$)'; then
  exit 0
fi

# Try pyright first, then ruff
CHECKER=""
CHECKER_NAME=""

if command -v pyright &>/dev/null; then
  CHECKER="pyright"
  CHECKER_NAME="pyright"
elif command -v ruff &>/dev/null; then
  CHECKER="ruff"
  CHECKER_NAME="ruff"
fi

if [[ -z "$CHECKER" ]]; then
  exit 0
fi

if [[ "$CHECKER" == "pyright" ]]; then
  ERRORS=$(pyright --outputjson "$FILE_PATH" 2>/dev/null | jq -r '.generalDiagnostics[]? | select(.severity == "error") | "\(.file):\(.range.start.line): \(.message)"' 2>/dev/null | head -5)
  if [[ -n "$ERRORS" ]]; then
    ERROR_COUNT=$(echo "$ERRORS" | wc -l | tr -d ' ')
    echo "Pyright errors in $(basename "$FILE_PATH") ($ERROR_COUNT):" >&2
    echo "$ERRORS" >&2
  fi
elif [[ "$CHECKER" == "ruff" ]]; then
  ERRORS=$(ruff check --quiet "$FILE_PATH" 2>/dev/null | head -5)
  if [[ -n "$ERRORS" ]]; then
    ERROR_COUNT=$(echo "$ERRORS" | wc -l | tr -d ' ')
    echo "Ruff errors in $(basename "$FILE_PATH") ($ERROR_COUNT):" >&2
    echo "$ERRORS" >&2
  fi
fi

# Blocking mode: exit non-zero if PIXL_STRICT_TYPECHECK is set and errors found
if [[ "${PIXL_STRICT_TYPECHECK:-}" == "1" && -n "${ERRORS:-}" ]]; then
  exit 1
fi

exit 0

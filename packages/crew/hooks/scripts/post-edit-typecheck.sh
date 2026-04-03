#!/usr/bin/env bash
# PostToolUse hook: run tsc --noEmit on edited .ts/.tsx files.
# Only triggers when a tsconfig.json exists in the project.

source "$(dirname "$0")/_common.sh"

read_stdin
require_jq

FILE_PATH=$(jq_input -r '.tool_input.file_path // empty')

if [[ -z "$FILE_PATH" ]]; then
  exit 0
fi

# Only check TypeScript files
case "$FILE_PATH" in
  *.ts|*.tsx) ;;
  *) exit 0 ;;
esac

# Skip non-source files (tests, configs, declarations, skill/agent definitions)
if echo "$FILE_PATH" | grep -qE '(\.(test|spec|config|d)\.(ts|tsx)$|/skills/|/agents/|/hooks/|/references/|\.tmpl$)'; then
  exit 0
fi

# Find nearest tsconfig.json
DIR=$(dirname "$FILE_PATH")
TSCONFIG=""
while [[ "$DIR" != "/" && "$DIR" != "." ]]; do
  if [[ -f "$DIR/tsconfig.json" ]]; then
    TSCONFIG="$DIR/tsconfig.json"
    break
  fi
  DIR=$(dirname "$DIR")
done

if [[ -z "$TSCONFIG" ]]; then
  exit 0
fi

TSCONFIG_DIR=$(dirname "$TSCONFIG")

# Run tsc --noEmit (quick type check, no output files)
# Use npx to find local tsc installation
TSC=""
if [[ -x "$TSCONFIG_DIR/node_modules/.bin/tsc" ]]; then
  TSC="$TSCONFIG_DIR/node_modules/.bin/tsc"
elif command -v tsc &>/dev/null; then
  TSC="tsc"
fi

if [[ -z "$TSC" ]]; then
  exit 0
fi

# Run type check on just the edited file (faster than full project)
ERRORS=$("$TSC" --noEmit --pretty false "$FILE_PATH" 2>&1 | head -10)

if [[ -n "$ERRORS" && "$ERRORS" != *"error TS"*"Cannot find"* ]]; then
  # Only report actual type errors, not missing module errors (which may be expected during development)
  REAL_ERRORS=$(echo "$ERRORS" | grep -c "error TS" || true)
  if [[ "$REAL_ERRORS" -gt 0 ]]; then
    echo "TypeScript errors in $(basename "$FILE_PATH"):" >&2
    echo "$ERRORS" | grep "error TS" | head -5 >&2

    # Blocking mode: exit non-zero if PIXL_STRICT_TYPECHECK is set
    if [[ "${PIXL_STRICT_TYPECHECK:-}" == "1" ]]; then
      exit 1
    fi
  fi
fi

exit 0

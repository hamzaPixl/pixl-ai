#!/usr/bin/env bash
# PreToolUse hook: warn when writing implementation code without corresponding test file.
# Exit 0 = allow (always), just outputs a warning message to stderr if no test found.

source "$(dirname "$0")/_common.sh"

read_stdin
require_jq

FILE_PATH=$(jq_input -r '.tool_input.file_path // empty')

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

# Only check source files (not tests, configs, templates, skills, agents, etc.)
if echo "$FILE_PATH" | grep -qE '\.(test|spec)\.(ts|tsx|js|jsx)$'; then
  exit 0  # Already a test file
fi

if ! echo "$FILE_PATH" | grep -qE '\.(ts|tsx|js|jsx)$'; then
  exit 0  # Not a code file
fi

# Skip non-implementation files
if echo "$FILE_PATH" | grep -qE '(\.config\.|\.tmpl$|/skills/|/agents/|/hooks/|/references/|/scripts/|__mocks__|\.d\.ts$)'; then
  exit 0
fi

# Check for corresponding test file
DIR=$(dirname "$FILE_PATH")
BASENAME=$(basename "$FILE_PATH" | sed 's/\.\(ts\|tsx\|js\|jsx\)$//')

TEST_EXISTS=false
for ext in test.ts test.tsx spec.ts spec.tsx test.js test.jsx; do
  # Check same directory
  if [ -f "$DIR/$BASENAME.$ext" ]; then
    TEST_EXISTS=true
    break
  fi
  # Check __tests__ subdirectory
  if [ -f "$DIR/__tests__/$BASENAME.$ext" ]; then
    TEST_EXISTS=true
    break
  fi
  # Check tests/ sibling directory
  PARENT=$(dirname "$DIR")
  if [ -f "$PARENT/tests/$BASENAME.$ext" ]; then
    TEST_EXISTS=true
    break
  fi
done

if [ "$TEST_EXISTS" = false ]; then
  echo "TDD reminder: No test file found for $(basename "$FILE_PATH"). Consider writing tests first." >&2
fi

exit 0

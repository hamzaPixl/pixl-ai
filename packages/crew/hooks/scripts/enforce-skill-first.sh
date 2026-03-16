#!/usr/bin/env bash
# enforce-skill-first.sh — PreToolUse(Write|Edit) hook
#
# Hard-blocks writes to domain/infra/api directories unless a pixl-crew
# skill has already been invoked in this session (tracked via flag file).
#
# Exit codes: 0 = allow, 2 = block

source "$(dirname "$0")/_common.sh"

read_stdin
require_jq

# Extract file_path from the tool input
FILE_PATH=$(jq_input -r '.file_path // empty')
if [[ -z "$FILE_PATH" ]]; then
  exit 0  # No file path (shouldn't happen), allow
fi

# Patterns that require a skill to be invoked first
DOMAIN_PATTERNS=(
  "*/domain/*"
  "*/entities/*"
  "*/aggregates/*"
  "*/value_objects/*"
  "*/routes/*"
  "*/api/*"
  "*/endpoints/*"
  "*/infrastructure/*"
)

# Check if file matches any protected pattern
MATCHED=false
for pattern in "${DOMAIN_PATTERNS[@]}"; do
  # Use bash pattern matching (convert glob to regex-like check)
  if [[ "$FILE_PATH" == $pattern ]]; then
    MATCHED=true
    break
  fi
done

if [[ "$MATCHED" != "true" ]]; then
  exit 0  # Not a protected path, allow
fi

# Check if a skill was already invoked this session
# The PostToolUse(Skill) hook or session tracking creates this flag
FLAG_DIR="${CLAUDE_PROJECT_DIR:-.}/.claude"
FLAG_FILE="$FLAG_DIR/.skill-invoked"

if [[ -f "$FLAG_FILE" ]]; then
  exit 0  # Skill was invoked, allow
fi

# Block the write
echo "BLOCKED: You must invoke a pixl-crew skill before writing to domain/infrastructure code." >&2
echo "" >&2
echo "Recommended skills for this path:" >&2
echo "  /ddd-pattern           — for domain entities, aggregates, value objects" >&2
echo "  /pydantic-api-endpoint — for API routes and endpoints" >&2
echo "  /fastapi-service       — for FastAPI service scaffolding" >&2
echo "" >&2
echo "Run the appropriate skill first, then retry your edit." >&2
exit 2

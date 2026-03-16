#!/usr/bin/env bash
# audit-skill-usage.sh — Stop hook
#
# Audits the session for pixl-crew skill/agent usage. Emits a warning
# if files were modified but no pixl-crew skills or agents were used.

set -euo pipefail

# Check if any files were modified in this session
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
MODIFIED_COUNT=$(git -C "$PROJECT_DIR" diff --name-only HEAD 2>/dev/null | wc -l | tr -d ' ')

if [[ "$MODIFIED_COUNT" == "0" ]]; then
  exit 0  # No files modified, nothing to audit
fi

# Check if the skill-invoked flag exists (set by Skill tool tracking)
FLAG_FILE="$PROJECT_DIR/.claude/.skill-invoked"

if [[ -f "$FLAG_FILE" ]]; then
  # Clean up the flag for next session
  rm -f "$FLAG_FILE"
  exit 0
fi

# Emit warning — files were modified without any skill usage
echo "" >&2
echo "⚠ Session completed without using any pixl-crew skills or agents." >&2
echo "  ${MODIFIED_COUNT} file(s) were modified." >&2
echo "" >&2
echo "  Consider whether a skill could have handled this work:" >&2
echo "    /ddd-pattern           — domain modeling" >&2
echo "    /pydantic-api-endpoint — API endpoints" >&2
echo "    /fastapi-service       — service scaffolding" >&2
echo "    /self-review-fix-loop  — quality review" >&2
echo "" >&2

# Clean up flag file if it exists from a previous session
rm -f "$FLAG_FILE"
exit 0

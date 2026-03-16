#!/usr/bin/env bash
# Stop hook: scan modified files for leftover console.log statements.
# Advisory — warns but doesn't block.

source "$(dirname "$0")/_common.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
cd "$PROJECT_DIR" 2>/dev/null || exit 0

# Get modified files (staged + unstaged)
MODIFIED=$(git diff --name-only HEAD 2>/dev/null || true; git diff --cached --name-only 2>/dev/null || true)

if [[ -z "$MODIFIED" ]]; then
  exit 0
fi

FOUND=""
while IFS= read -r file; do
  [[ -z "$file" ]] && continue
  # Only check JS/TS source files
  case "$file" in
    *.ts|*.tsx|*.js|*.jsx) ;;
    *) continue ;;
  esac
  # Skip test files and configs
  echo "$file" | grep -qE '\.(test|spec|config)\.' && continue
  # Check for console.log (not console.error/warn which may be intentional)
  if [[ -f "$file" ]] && grep -n 'console\.log(' "$file" 2>/dev/null | grep -v '// keep' | grep -v '// eslint-disable' > /dev/null; then
    LINES=$(grep -n 'console\.log(' "$file" 2>/dev/null | grep -v '// keep' | grep -v '// eslint-disable' | head -3 || true)
    FOUND="$FOUND\n  $file:\n$LINES\n"
  fi
done <<< "$MODIFIED"

if [[ -n "$FOUND" ]]; then
  echo "console.log audit — leftover statements found:" >&2
  echo -e "$FOUND" >&2
  echo "Remove or replace with structured logging before committing." >&2
fi

exit 0

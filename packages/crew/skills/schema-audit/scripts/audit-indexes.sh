#!/usr/bin/env bash
# audit-indexes.sh — Audit indexes in Prisma schema or SQL files
# Usage: ./audit-indexes.sh [schema-file]
set -euo pipefail

SCHEMA="${1:-}"

# Auto-detect schema file
if [[ -z "$SCHEMA" ]]; then
  if [[ -f "prisma/schema.prisma" ]]; then
    SCHEMA="prisma/schema.prisma"
  else
    SCHEMA=$(find . -name "schema.prisma" -not -path "*/node_modules/*" 2>/dev/null | head -1)
  fi
fi

if [[ -z "$SCHEMA" || ! -f "$SCHEMA" ]]; then
  echo "No schema file found. Pass path as argument: ./audit-indexes.sh prisma/schema.prisma"
  exit 1
fi

echo "Auditing indexes in: $SCHEMA"
echo "==============================="

# Extract models
MODELS=$(grep -E "^model " "$SCHEMA" | sed 's/model \([A-Za-z]*\) .*/\1/')
echo "Models found: $(echo "$MODELS" | wc -l | tr -d ' ')"

echo ""
echo "## Defined Indexes"
grep -n "@@index\|@@unique\|@id\|@unique" "$SCHEMA" || echo "(none)"

echo ""
echo "## Foreign Key Fields (should be indexed)"
grep -n "@relation\|_id\b" "$SCHEMA" | grep -v "@@\|//" || echo "(none)"

echo ""
echo "## Missing Index Candidates"
echo "Fields ending in Id or _id without explicit @@index:"
grep -n "[a-z]Id\s\|_id\s" "$SCHEMA" | grep -v "@@index\|@@unique\|@id\b\|@unique" || echo "(none obvious)"

echo ""
echo "## Composite Indexes"
grep -n "@@index(\[" "$SCHEMA" || echo "(none)"

echo ""
echo "Run /schema-audit for full analysis with severity scores."

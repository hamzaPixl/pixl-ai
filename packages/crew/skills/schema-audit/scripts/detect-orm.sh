#!/usr/bin/env bash
# detect-orm.sh — Detect ORM/schema type in the project
# Usage: ./detect-orm.sh [path]
# Output: prints detected ORM name(s), one per line
set -euo pipefail

SCAN_PATH="${1:-.}"

detect_prisma() {
  [[ -f "$SCAN_PATH/prisma/schema.prisma" ]] && echo "prisma" && return
  find "$SCAN_PATH" -name "schema.prisma" -not -path "*/node_modules/*" 2>/dev/null | head -1 | grep -q . && echo "prisma"
}

detect_sqlalchemy() {
  find "$SCAN_PATH" -name "*.py" -not -path "*/__pycache__/*" -not -path "*/venv/*" \
    -exec grep -l "from sqlalchemy\|import sqlalchemy\|declarative_base\|Base = " {} \; 2>/dev/null | head -1 | grep -q . && echo "sqlalchemy"
}

detect_drizzle() {
  find "$SCAN_PATH" -name "*.ts" -not -path "*/node_modules/*" \
    -exec grep -l "from 'drizzle-orm\|pgTable\|mysqlTable\|sqliteTable" {} \; 2>/dev/null | head -1 | grep -q . && echo "drizzle"
}

detect_raw_sql() {
  find "$SCAN_PATH" \( -name "*.sql" -o -name "*.migration" \) -not -path "*/node_modules/*" 2>/dev/null | head -1 | grep -q . && echo "raw-sql"
}

detect_sqlite() {
  find "$SCAN_PATH" -name "*.db" -o -name "*.sqlite" -o -name "*.sqlite3" 2>/dev/null | head -1 | grep -q . && echo "sqlite"
}

FOUND=false
detect_prisma && FOUND=true
detect_sqlalchemy && FOUND=true
detect_drizzle && FOUND=true
detect_raw_sql && FOUND=true
detect_sqlite && FOUND=true

if [[ "$FOUND" == "false" ]]; then
  echo "unknown"
fi

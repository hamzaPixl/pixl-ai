#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${1:-/workspace}"
cd "$PROJECT_DIR"

# Idempotency guard — skip if already initialized
if [ -f "$PROJECT_DIR/.pixl/config.json" ]; then
  echo "pixl already initialized at $PROJECT_DIR"
  pixl --version
  claude --version
  exit 0
fi

# If repo was cloned via gitCheckout, .git/ already exists — skip git init
if [ ! -d "$PROJECT_DIR/.git" ]; then
  git init -b main
  git config user.name "pixl-sandbox"
  git config user.email "sandbox@pixl.dev"
fi

# Initialize pixl project (creates .pixl/, config.json, SQLite DB on first access)
pixl project init

# Register crew plugin with Claude Code
pixl setup --skip-plugins --skip-lsp --skip-security

# Copy test workflow if not present
cp -n /opt/pixl/test-workflow.yaml "$PROJECT_DIR/.pixl/workflows/" 2>/dev/null || true

echo "pixl initialized at $PROJECT_DIR"
pixl --version
claude --version

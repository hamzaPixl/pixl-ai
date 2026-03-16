#!/usr/bin/env bash
# PostToolUse hook: smart quality gate — detect and run the right formatter per file extension.
# Replaces format-on-write.sh with multi-language support.

source "$(dirname "$0")/_common.sh"

read_stdin
require_jq

FILE_PATH=$(jq_input -r '.tool_input.file_path // empty')

if [[ -z "$FILE_PATH" || ! -f "$FILE_PATH" ]]; then
  exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"

# Determine formatter based on file extension
case "$FILE_PATH" in
  *.ts|*.tsx|*.js|*.jsx|*.css|*.json|*.md|*.html)
    # Check for Biome first (faster), then Prettier
    if [[ -x "$PROJECT_DIR/node_modules/.bin/biome" ]]; then
      "$PROJECT_DIR/node_modules/.bin/biome" format --write "$FILE_PATH" &>/dev/null || true
    elif [[ -x "$PROJECT_DIR/node_modules/.bin/prettier" ]]; then
      "$PROJECT_DIR/node_modules/.bin/prettier" --write "$FILE_PATH" &>/dev/null || true
    elif command -v prettier &>/dev/null; then
      prettier --write "$FILE_PATH" &>/dev/null || true
    fi
    ;;
  *.py)
    # Check for ruff (fast), then black
    if command -v ruff &>/dev/null; then
      ruff format "$FILE_PATH" &>/dev/null || true
    elif command -v black &>/dev/null; then
      black --quiet "$FILE_PATH" &>/dev/null || true
    fi
    ;;
  *.go)
    if command -v gofmt &>/dev/null; then
      gofmt -w "$FILE_PATH" &>/dev/null || true
    fi
    ;;
  *.swift)
    # Check for swift-format (bundled with Xcode 16+)
    if command -v swift-format &>/dev/null; then
      swift-format format --in-place "$FILE_PATH" &>/dev/null || true
    elif command -v swiftformat &>/dev/null; then
      swiftformat "$FILE_PATH" &>/dev/null || true
    fi
    ;;
  *.rs)
    if command -v rustfmt &>/dev/null; then
      rustfmt "$FILE_PATH" &>/dev/null || true
    fi
    ;;
  *)
    # No formatter for this extension
    ;;
esac

exit 0

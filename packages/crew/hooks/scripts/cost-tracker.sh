#!/usr/bin/env bash
# Stop hook: append per-session cost estimate to .claude/memory/costs.jsonl
# Reads CLAUDE_SESSION_TOKENS_* env vars if available, otherwise estimates from session duration.

source "$(dirname "$0")/_common.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
MEMORY_DIR="$PROJECT_DIR/.claude/memory"

# Skip if neither memory directory nor pixl is available
if [[ ! -d "$MEMORY_DIR" ]] && ! $PIXL_AVAILABLE; then
  exit 0
fi

COSTS_FILE="$MEMORY_DIR/costs.jsonl"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
SESSION_ID="${CLAUDE_SESSION_ID:-$(date +%s)}"

# Try to get token counts from environment (set by Claude Code if available)
INPUT_TOKENS="${CLAUDE_SESSION_INPUT_TOKENS:-0}"
OUTPUT_TOKENS="${CLAUDE_SESSION_OUTPUT_TOKENS:-0}"
CACHE_READ_TOKENS="${CLAUDE_SESSION_CACHE_READ_TOKENS:-0}"
CACHE_WRITE_TOKENS="${CLAUDE_SESSION_CACHE_WRITE_TOKENS:-0}"

# Cost rates (per 1M tokens, USD) — Claude Opus 4
INPUT_RATE="15.00"
OUTPUT_RATE="75.00"
CACHE_READ_RATE="1.50"
CACHE_WRITE_RATE="18.75"

# Calculate cost estimate (using awk for floating point)
COST=$(awk "BEGIN {
  input_cost = $INPUT_TOKENS / 1000000 * $INPUT_RATE
  output_cost = $OUTPUT_TOKENS / 1000000 * $OUTPUT_RATE
  cache_read_cost = $CACHE_READ_TOKENS / 1000000 * $CACHE_READ_RATE
  cache_write_cost = $CACHE_WRITE_TOKENS / 1000000 * $CACHE_WRITE_RATE
  total = input_cost + output_cost + cache_read_cost + cache_write_cost
  printf \"%.4f\", total
}")

# Only log if we have actual token data
if [[ "$INPUT_TOKENS" != "0" || "$OUTPUT_TOKENS" != "0" ]]; then
  COST_ENTRY="{\"timestamp\":\"$TIMESTAMP\",\"session\":\"$SESSION_ID\",\"input_tokens\":$INPUT_TOKENS,\"output_tokens\":$OUTPUT_TOKENS,\"cache_read_tokens\":$CACHE_READ_TOKENS,\"cache_write_tokens\":$CACHE_WRITE_TOKENS,\"estimated_cost_usd\":$COST}"

  if $PIXL_AVAILABLE; then
    pixl_put "cost-$SESSION_ID" "cost_log" "$COST_ENTRY"
  else
    echo "$COST_ENTRY" >> "$COSTS_FILE"
  fi
fi

exit 0

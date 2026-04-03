#!/usr/bin/env bash
# Stop hook: append per-session cost estimate to .claude/memory/costs.jsonl
# Parses the most recently modified session JSONL to extract actual token usage.

source "$(dirname "$0")/_common.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
MEMORY_DIR="$PROJECT_DIR/.claude/memory"

# Skip if neither memory directory nor pixl is available
if [[ ! -d "$MEMORY_DIR" ]] && ! $PIXL_AVAILABLE; then
  exit 0
fi

COSTS_FILE="$MEMORY_DIR/costs.jsonl"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Resolve the Claude projects directory for this project
# Claude Code stores sessions at ~/.claude/projects/<encoded-path>/*.jsonl
PROJECTS_BASE="$HOME/.claude/projects"
ENCODED_PATH=$(echo "$PROJECT_DIR" | sed 's|/|-|g')
SESSION_DIR="$PROJECTS_BASE/$ENCODED_PATH"

if [[ ! -d "$SESSION_DIR" ]]; then
  exit 0
fi

# Find the most recently modified JSONL (= current session)
LATEST_JSONL=$(ls -t "$SESSION_DIR"/*.jsonl 2>/dev/null | head -1)
if [[ -z "$LATEST_JSONL" ]]; then
  exit 0
fi

SESSION_ID=$(basename "$LATEST_JSONL" .jsonl)

# Parse token usage from assistant messages (fast python one-liner)
# No `timeout` on macOS — the parent hook has a 30s timeout guard
USAGE=$(python3 -c "
import json, sys
ti = to = cr = cc = 0
with open('$LATEST_JSONL') as f:
    for line in f:
        try:
            d = json.loads(line)
            if d.get('type') == 'assistant':
                u = d.get('message', {}).get('usage', {})
                ti += u.get('input_tokens', 0)
                to += u.get('output_tokens', 0)
                cr += u.get('cache_read_input_tokens', 0)
                cc += u.get('cache_creation_input_tokens', 0)
        except: pass
if to > 0:
    cost = ti/1e6*15 + to/1e6*75 + cr/1e6*1.5 + cc/1e6*18.75
    print(json.dumps({'timestamp':'$TIMESTAMP','session':'$SESSION_ID','input_tokens':ti,'output_tokens':to,'cache_read_tokens':cr,'cache_write_tokens':cc,'estimated_cost_usd':round(cost,4)}))
" 2>/dev/null)

if [[ -z "$USAGE" ]]; then
  exit 0
fi

# Write to pixl DB (primary) or file (fallback) — not both
if $PIXL_AVAILABLE; then
  pixl_put "cost-$SESSION_ID" "cost_log" "$USAGE"
else
  echo "$USAGE" >> "$COSTS_FILE"
fi

exit 0

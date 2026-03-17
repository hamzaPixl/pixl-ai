#!/usr/bin/env bash
# prd-pipeline-scope-guard.sh
# On-demand PreToolUse:Write|Edit hook — only active when prd-pipeline is running.
# Prevents writes to critical infrastructure files during autonomous pipeline execution.
#
# Activation: hook checks for .context/pipeline-state.json with status != "complete"
# Usage: integrated via hooks.json PreToolUse matcher for Write|Edit

source "$(dirname "$0")/_common.sh"
read_stdin
require_jq

# --- Activation check ---
# Only engage if a pipeline is actively running
PIPELINE_STATE="${PWD}/.context/pipeline-state.json"
if [[ ! -f "$PIPELINE_STATE" ]]; then
  exit 0  # Not in a pipeline session — pass through
fi

PIPELINE_STATUS=$(jq -r '.status // "unknown"' "$PIPELINE_STATE" 2>/dev/null || echo "unknown")
if [[ "$PIPELINE_STATUS" == "complete" || "$PIPELINE_STATUS" == "unknown" ]]; then
  exit 0  # Pipeline finished or state unreadable — pass through
fi

# --- Extract tool info ---
FILE_PATH=$(jq_input -r '.tool_input.file_path // ""' 2>/dev/null || echo "")

if [[ -z "$FILE_PATH" ]]; then
  exit 0  # No file path — pass through
fi

# --- Scope guard: block writes to critical infrastructure files during pipeline ---
BLOCKED_PATTERNS=(
  "^\.github/workflows/"         # CI/CD pipelines — shouldn't change mid-run
  "^\.env$"                      # Root env — use .env.local or service-specific
  "^Makefile$"                   # Build orchestration — plan change first
  "^docker-compose\.ya?ml$"      # Infrastructure definition
  "^pyproject\.toml$"            # Package manifest — requires version bump
  "^package\.json$"              # Package manifest — requires version bump
  "^CLAUDE\.md$"                 # Project instructions — changes affect all agents
)

RELATIVE_PATH="${FILE_PATH#${PWD}/}"

for pattern in "${BLOCKED_PATTERNS[@]}"; do
  if echo "$RELATIVE_PATH" | grep -qE "$pattern"; then
    CURRENT_PHASE=$(jq -r '.current_phase // "unknown"' "$PIPELINE_STATE" 2>/dev/null || echo "unknown")

    # Check bypass flag before printing the block message
    if [[ "${PIXL_PIPELINE_BYPASS:-0}" == "1" ]]; then
      exit 0  # Bypass active — allow write silently
    fi

    cat <<EOF
prd-pipeline scope guard: blocked write to critical file during pipeline execution.

  File:    $RELATIVE_PATH
  Phase:   $CURRENT_PHASE
  Pattern: $pattern

This file is typically set up before the pipeline starts, not during implementation.
If this change is intentional:
  1. Pause the pipeline: update .context/pipeline-state.json status to "paused"
  2. Make the change manually
  3. Resume: set status back to "running" and re-run /prd-pipeline with resume

To bypass for this file only, set PIXL_PIPELINE_BYPASS=1 in your shell.
EOF
    exit 2  # Block the write
  fi
done

exit 0  # File not in blocked list — allow

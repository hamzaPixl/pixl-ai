#!/usr/bin/env bash
# PreToolUse hook: validates that Agent tool's subagent_type is a known pixl-crew agent.
# Reads tool input JSON from stdin. Exits 0 (allow) or 2 (block).

source "$(dirname "$0")/_common.sh"

# Known pixl-crew agent names
VALID_AGENTS=(
  orchestrator
  architect
  product-owner
  tech-lead
  frontend-engineer
  backend-engineer
  fullstack-engineer
  qa-engineer
  devops-engineer
  security-engineer
  explorer
  onboarding-agent
  build-error-resolver
  doc-updater
)

read_stdin
require_jq

# Extract subagent_type
AGENT=$(jq_input -r '.tool_input.subagent_type // empty')

# If no subagent_type found, allow
if [ -z "$AGENT" ]; then
  exit 0
fi

# Only validate agents that use the pixl-crew: prefix
# Allow all non-prefixed agents (built-in Claude Code agents like Explore, Plan, etc.)
if [[ "$AGENT" != pixl-crew:* ]]; then
  exit 0
fi

# Validate the pixl-crew agent name
UNPREFIXED="${AGENT#pixl-crew:}"
for valid in "${VALID_AGENTS[@]}"; do
  if [ "$UNPREFIXED" = "$valid" ]; then
    exit 0
  fi
done

# Unknown pixl-crew agent — block with message
echo "Unknown pixl-crew agent: '$AGENT'. Valid agents: ${VALID_AGENTS[*]}"
exit 2

#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/_env.sh"

bash "$CLAUDE_PLUGIN_ROOT/hooks/scripts/run-with-flags.sh" \
  prompt-context-primer \
  advisory \
  "$CLAUDE_PLUGIN_ROOT/hooks/scripts/prompt-context-primer.sh"

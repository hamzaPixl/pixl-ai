#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/_env.sh"

bash "$CLAUDE_PLUGIN_ROOT/hooks/scripts/run-with-flags.sh" \
  block-destructive \
  critical \
  "$CLAUDE_PLUGIN_ROOT/hooks/scripts/block-destructive.sh"

#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/_env.sh"

bash "$CLAUDE_PLUGIN_ROOT/hooks/session-start.sh"

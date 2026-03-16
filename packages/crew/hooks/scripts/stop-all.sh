#!/usr/bin/env bash
# Consolidated Stop hook: runs all stop-time tasks sequentially.
# Replaces 4 separate Stop hooks to reduce process spawning overhead.

set -euo pipefail

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-.}"
SCRIPTS="$PLUGIN_ROOT/hooks/scripts"

# Save stdin for scripts that need it
INPUT=$(cat)

# 1. Session summary (critical — always runs)
echo "$INPUT" | bash "$SCRIPTS/run-with-flags.sh" stop-summary critical "$SCRIPTS/stop-summary.sh" 2>/dev/null || true

# 2. Skill usage audit (quality)
echo "$INPUT" | bash "$SCRIPTS/run-with-flags.sh" audit-skill quality "$SCRIPTS/audit-skill-usage.sh" 2>/dev/null || true

# 3. Cost tracker (quality)
echo "$INPUT" | bash "$SCRIPTS/run-with-flags.sh" cost-tracker quality "$SCRIPTS/cost-tracker.sh" 2>/dev/null || true

# 4. Console.log audit (advisory)
echo "$INPUT" | bash "$SCRIPTS/run-with-flags.sh" console-log-audit advisory "$SCRIPTS/check-console-log.sh" 2>/dev/null || true

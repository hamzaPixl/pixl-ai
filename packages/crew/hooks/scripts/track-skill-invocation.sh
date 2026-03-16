#!/usr/bin/env bash
# track-skill-invocation.sh — PostToolUse(Skill) hook
#
# Creates a session-level flag file when a Skill tool is invoked,
# so enforce-skill-first.sh knows a skill was used.

set -euo pipefail

FLAG_DIR="${CLAUDE_PROJECT_DIR:-.}/.claude"
mkdir -p "$FLAG_DIR"
date -u +%Y-%m-%dT%H:%M:%SZ > "$FLAG_DIR/.skill-invoked"
exit 0

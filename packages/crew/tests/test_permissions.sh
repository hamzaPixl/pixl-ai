#!/usr/bin/env bash
# Tests for permission-check.sh — run with: bash packages/crew/tests/test_permissions.sh
set -uo pipefail

SCRIPT="packages/crew/hooks/scripts/permission-check.sh"
PASS=0
FAIL=0

assert_exit() {
  local label="$1" expected="$2" input="$3"
  actual=$(echo "$input" | bash "$SCRIPT" >/dev/null 2>&1; echo $?)
  if [ "$actual" = "$expected" ]; then
    echo "  PASS: $label (exit=$actual)"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: $label (expected=$expected, got=$actual)"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== Permission Tier Tests ==="

# always_deny: DROP TABLE
assert_exit "deny: DROP TABLE" "2" \
  '{"tool_name":"Bash","tool_input":{"command":"DROP TABLE users"}}'

# always_deny: git clean
assert_exit "deny: git clean -fd" "2" \
  '{"tool_name":"Bash","tool_input":{"command":"git clean -fd"}}'

# always_allow: git status
assert_exit "allow: git status" "0" \
  '{"tool_name":"Bash","tool_input":{"command":"git status"}}'

# always_allow: ls
assert_exit "allow: ls -la" "0" \
  '{"tool_name":"Bash","tool_input":{"command":"ls -la"}}'

# always_allow: pytest
assert_exit "allow: pytest" "0" \
  '{"tool_name":"Bash","tool_input":{"command":"pytest tests/ -q"}}'

# always_allow: ruff
assert_exit "allow: ruff check" "0" \
  '{"tool_name":"Bash","tool_input":{"command":"ruff check src/"}}'

# no rule: normal command
assert_exit "allow: echo hello" "0" \
  '{"tool_name":"Bash","tool_input":{"command":"echo hello"}}'

# no rule: empty command
assert_exit "allow: empty" "0" \
  '{"tool_name":"Bash","tool_input":{"command":""}}'

# ask_user: pip install (non-interactive = deny)
assert_exit "ask/deny: pip install" "2" \
  '{"tool_name":"Bash","tool_input":{"command":"pip install requests"}}'

echo ""
echo "Results: $PASS passed, $FAIL failed"
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi

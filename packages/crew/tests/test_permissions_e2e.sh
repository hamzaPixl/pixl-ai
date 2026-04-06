#!/usr/bin/env bash
# End-to-end tests for permission-check.sh with the actual permissions.yaml
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

assert_exit_env() {
  local label="$1" expected="$2" env_var="$3" env_val="$4" input="$5"
  actual=$(echo "$input" | env "$env_var=$env_val" bash "$SCRIPT" >/dev/null 2>&1; echo $?)
  if [ "$actual" = "$expected" ]; then
    echo "  PASS: $label (exit=$actual)"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: $label (expected=$expected, got=$actual)"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== Permission Tiers (always_deny) ==="
assert_exit "deny: DROP TABLE" "2" '{"tool_name":"Bash","tool_input":{"command":"DROP TABLE users"}}'
assert_exit "deny: drop table (case)" "2" '{"tool_name":"Bash","tool_input":{"command":"drop table users"}}'
assert_exit "deny: git clean -fd" "2" '{"tool_name":"Bash","tool_input":{"command":"git clean -fd"}}'
assert_exit "deny: git reset --hard" "2" '{"tool_name":"Bash","tool_input":{"command":"git reset --hard HEAD~3"}}'
assert_exit "deny: TRUNCATE" "2" '{"tool_name":"Bash","tool_input":{"command":"TRUNCATE table orders"}}'

echo ""
echo "=== Permission Tiers (always_allow) ==="
assert_exit "allow: git status" "0" '{"tool_name":"Bash","tool_input":{"command":"git status"}}'
assert_exit "allow: git log" "0" '{"tool_name":"Bash","tool_input":{"command":"git log --oneline -5"}}'
assert_exit "allow: ls" "0" '{"tool_name":"Bash","tool_input":{"command":"ls -la"}}'
assert_exit "allow: pytest" "0" '{"tool_name":"Bash","tool_input":{"command":"pytest tests/ -q"}}'
assert_exit "allow: ruff" "0" '{"tool_name":"Bash","tool_input":{"command":"ruff check src/"}}'
assert_exit "allow: python --version" "0" '{"tool_name":"Bash","tool_input":{"command":"python --version"}}'

echo ""
echo "=== Permission Tiers (ask_user) ==="
assert_exit "ask/allow: pip install (standard)" "0" '{"tool_name":"Bash","tool_input":{"command":"pip install requests"}}'
assert_exit "ask/allow: git push (standard)" "0" '{"tool_name":"Bash","tool_input":{"command":"git push origin main"}}'
assert_exit_env "ask/deny: pip install (minimal)" "2" "PIXL_HOOK_PROFILE" "minimal" '{"tool_name":"Bash","tool_input":{"command":"pip install requests"}}'
assert_exit_env "ask/deny: git push (CI)" "2" "CI" "true" '{"tool_name":"Bash","tool_input":{"command":"git push origin main"}}'

echo ""
echo "=== No Match (default allow) ==="
assert_exit "allow: echo hello" "0" '{"tool_name":"Bash","tool_input":{"command":"echo hello"}}'
assert_exit "allow: uv sync" "0" '{"tool_name":"Bash","tool_input":{"command":"uv sync"}}'
assert_exit "allow: empty" "0" '{"tool_name":"Bash","tool_input":{"command":""}}'

echo ""
echo "=== Tool Scoping ==="
assert_exit "allow: DROP TABLE in Write (tool filter)" "0" '{"tool_name":"Write","tool_input":{"content":"DROP TABLE users","path":"schema.sql"}}'

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1

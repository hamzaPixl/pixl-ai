#!/usr/bin/env bash
set -euo pipefail

# --- Configuration ---
BASE_URL="${BASE_URL:-http://localhost:8787}"
API_KEY="${SANDBOX_API_KEY:?Set SANDBOX_API_KEY}"
PROJECT_ID="e2e-$(date +%s)"

PASS=0
FAIL=0

# --- Helpers ---
auth_header="Authorization: Bearer $API_KEY"
json_type="Content-Type: application/json"

check() {
  local name="$1" expected="$2" actual="$3"
  if echo "$actual" | grep -q "$expected"; then
    echo "  PASS: $name"
    ((PASS++))
  else
    echo "  FAIL: $name (expected '$expected', got '$actual')"
    ((FAIL++))
  fi
}

api_get() {
  curl -sf -H "$auth_header" "$BASE_URL$1" 2>/dev/null || echo '{"error":"request failed"}'
}

api_post() {
  curl -sf -H "$auth_header" -H "$json_type" -d "$2" "$BASE_URL$1" 2>/dev/null || echo '{"error":"request failed"}'
}

api_delete() {
  curl -sf -H "$auth_header" -X DELETE "$BASE_URL$1" 2>/dev/null || echo '{"error":"request failed"}'
}

# --- Tests ---

echo "=== pixl-sandbox E2E Tests ==="
echo "URL: $BASE_URL"
echo "Project: $PROJECT_ID"
echo ""

# 1. Health check (no auth)
echo "1. Health check"
result=$(curl -sf "$BASE_URL/health")
check "health endpoint" '"status":"ok"' "$result"

# 2. Auth rejection
echo "2. Auth rejection"
result=$(curl -sf -o /dev/null -w "%{http_code}" "$BASE_URL/sandboxes" -X POST -H "$json_type" -d '{"projectId":"test"}' 2>/dev/null || echo "401")
check "rejects without token" "401" "$result"

# 3. Create sandbox (single-call setup)
echo "3. Create sandbox"
result=$(api_post "/sandboxes" "{\"projectId\":\"$PROJECT_ID\"}")
check "sandbox created" '"status":"ready"' "$result"
check "has versions" '"pixl"' "$result"
check "has git info" '"branch"' "$result"

# 4. Status
echo "4. Status"
result=$(api_get "/sandboxes/$PROJECT_ID/status")
check "status returns versions" '"pixl"' "$result"
check "status returns git" '"branch"' "$result"
check "status returns project" '"initialized"' "$result"
check "status returns envKeys" '"envKeys"' "$result"

# 5. Exec command
echo "5. Exec command"
result=$(api_post "/sandboxes/$PROJECT_ID/exec" '{"command":"pixl --version"}')
check "exec success" '"success":true' "$result"

# 6. Write file
echo "6. Write file"
result=$(api_post "/sandboxes/$PROJECT_ID/files" '{"path":"/workspace/test.txt","content":"hello e2e"}')
check "file written" '"success":true' "$result"

# 7. Read file back
echo "7. Read file"
result=$(api_get "/sandboxes/$PROJECT_ID/files/workspace/test.txt")
check "file content matches" 'hello e2e' "$result"

# 8. Path traversal rejection
echo "8. Path traversal"
result=$(curl -sf -o /dev/null -w "%{http_code}" -H "$auth_header" "$BASE_URL/sandboxes/$PROJECT_ID/files/../../../etc/passwd" 2>/dev/null || echo "400")
check "rejects path traversal" "400" "$result"

# 9. SSE streaming exec
echo "9. SSE stream"
result=$(curl -sf -H "$auth_header" -H "$json_type" -d '{"command":"echo streaming"}' -o /dev/null -w "%{http_code}" "$BASE_URL/sandboxes/$PROJECT_ID/exec/stream" 2>/dev/null || echo "200")
check "SSE returns 200" "200" "$result"

# 10. Workflow run (short test)
echo "10. Workflow"
result=$(api_post "/sandboxes/$PROJECT_ID/workflow" '{"prompt":"List files in /workspace and report versions","workflowId":"sandbox-test","autoApprove":true}')
check "workflow completed" '"success":true' "$result"

# 11. Sessions
echo "11. Sessions"
result=$(api_get "/sandboxes/$PROJECT_ID/sessions")
check "sessions returned" '"success":true' "$result"

# 12. Events
echo "12. Events"
result=$(api_get "/sandboxes/$PROJECT_ID/events")
check "events returned" '"success":true' "$result"

# 13. Git status
echo "13. Git"
result=$(api_get "/sandboxes/$PROJECT_ID/git")
check "git info returned" '"branch"' "$result"

# 14. Usage
echo "14. Usage"
result=$(api_get "/sandboxes/$PROJECT_ID/usage")
check "usage returned" '"total_operations"' "$result"

# 15. Env update
echo "15. Env update"
result=$(api_post "/sandboxes/$PROJECT_ID/env" '{"TEST_VAR":"test_value"}')
check "env updated" '"success":true' "$result"

# 16. Git config
echo "16. Git config"
result=$(api_post "/sandboxes/$PROJECT_ID/git/config" '{"userName":"test-user","userEmail":"test@example.com"}')
check "git config set" '"success":true' "$result"

# 17. Destroy
echo "17. Destroy"
result=$(api_delete "/sandboxes/$PROJECT_ID")
check "sandbox destroyed" '"success":true' "$result"

# --- Summary ---
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
exit $((FAIL > 0 ? 1 : 0))

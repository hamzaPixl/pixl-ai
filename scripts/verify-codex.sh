#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

echo "== Codex CLI =="
if ! command -v codex >/dev/null 2>&1; then
  echo "codex not found. Install with: npm install -g @openai/codex"
  exit 1
fi
codex --version

echo ""
echo "== Pixl CLI =="
if ! command -v pixl >/dev/null 2>&1; then
  echo "pixl not found. Install with: uv tool install pixl"
  exit 1
fi
pixl --version

echo ""
echo "== Project Scaffolding =="
for path in "AGENTS.md" ".codex/config.toml" ".codex/hooks.json" ".codex/rules/default.rules" ".agents/skills"; do
  if [ -e "$path" ]; then
    echo "OK: $path"
  else
    echo "MISSING: $path"
  fi
done

echo ""
echo "== Codex Exec (non-interactive, read-only) =="
if [ -f "$HOME/.codex/auth.json" ] || [ -n "${OPENAI_API_KEY:-}" ]; then
  OUT="${ROOT}/.codex-verify.jsonl"
  codex exec -s read-only --json -C "$ROOT" \
    "Can you list the available skills (just the names) and confirm that task-plan exists? Also summarize the repo layout. If subagents are supported, try the orchestrator. Please do not modify any files." \
    > "$OUT"
  echo "Wrote Codex exec output to $OUT"
  if command -v rg >/dev/null 2>&1; then
    HAS_TASK_PLAN=$(rg -q "task-plan" "$OUT" && echo "yes" || echo "no")
  else
    HAS_TASK_PLAN=$(grep -q "task-plan" "$OUT" && echo "yes" || echo "no")
  fi
  if [ "$HAS_TASK_PLAN" = "yes" ]; then
    echo "OK: task-plan skill discovered in Codex exec output"
  else
    echo "WARN: task-plan not found in Codex exec output"
  fi
  if command -v rg >/dev/null 2>&1; then
    rg -q "can't spawn subagents|cannot spawn subagents|subagents not supported" "$OUT" && \
      echo "NOTE: Codex exec mode does not support subagents; verify in interactive mode."
  else
    grep -Eq "can't spawn subagents|cannot spawn subagents|subagents not supported" "$OUT" && \
      echo "NOTE: Codex exec mode does not support subagents; verify in interactive mode."
  fi
else
  echo "SKIP: No Codex auth found (~/.codex/auth.json or OPENAI_API_KEY)."
fi

echo ""
echo "== Pixl Engine Codex Provider (real run) =="
if [ -f "$HOME/.codex/auth.json" ] || [ -n "${OPENAI_API_KEY:-}" ]; then
  PROVIDERS_FILE=".pixl/providers.yaml"
  BACKUP_FILE=".pixl/providers.yaml.bak"
  if [ -f "$PROVIDERS_FILE" ]; then
    cp "$PROVIDERS_FILE" "$BACKUP_FILE"
  fi
  cat > "$PROVIDERS_FILE" <<'YAML'
default_provider: codex
default_model: codex/gpt-5.2-codex
YAML

  RESULT_JSON=$(pixl --json workflow run --workflow codex-verify --yes --prompt "Verify Codex integration for this repo. Do not modify files.")
  SESSION_ID=$(python3 - <<'PY'
import re,sys,json
raw=sys.stdin.read()
try:
    data=json.loads(raw)
    print(data.get("session_id",""))
except json.JSONDecodeError:
    m=re.search(r'"session_id"\\s*:\\s*"([^"]+)"', raw)
    print(m.group(1) if m else "")
PY
<<<"$RESULT_JSON")

  if [ -n "$SESSION_ID" ]; then
    echo "Session: $SESSION_ID"
    echo "Model usage check:"
    pixl --json session get "$SESSION_ID" | python3 - <<'PY'
import json,sys
data=json.loads(sys.stdin.read())
models={v.get("model_name") for v in data.get("node_instances",{}).values() if v.get("model_name")}
print("Session models:", sorted(models))
if any("codex" in m or "gpt-5" in m for m in models):
    print("OK: Codex model detected")
else:
    print("WARN: Codex model not detected")
PY
  else
    echo "WARN: Could not parse session_id from workflow output."
  fi

  if [ -f "$BACKUP_FILE" ]; then
    mv "$BACKUP_FILE" "$PROVIDERS_FILE"
  else
    rm -f "$PROVIDERS_FILE"
  fi
else
  echo "SKIP: No Codex auth found (~/.codex/auth.json or OPENAI_API_KEY)."
fi

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
  if rg -q "\"task-plan\"" "$OUT"; then
    echo "OK: task-plan skill discovered in Codex exec output"
  else
    echo "WARN: task-plan not found in Codex exec output"
  fi
  if rg -q "can't spawn subagents|cannot spawn subagents|subagents not supported" "$OUT"; then
    echo "NOTE: Codex exec mode does not support subagents; verify in interactive mode."
  fi
else
  echo "SKIP: No Codex auth found (~/.codex/auth.json or OPENAI_API_KEY)."
fi

echo ""
echo "== Pixl Engine Codex Provider (real run) =="
if [ -f "$HOME/.codex/auth.json" ] || [ -n "${OPENAI_API_KEY:-}" ]; then
  pixl config set default_model codex/gpt-5.2-codex
  pixl workflow run --workflow codex-verify --yes --prompt "Verify Codex integration for this repo. Do not modify files."
  echo "Model usage check (recent codex entries):"
  pixl cost summary --json | rg "codex|gpt-5" || true
else
  echo "SKIP: No Codex auth found (~/.codex/auth.json or OPENAI_API_KEY)."
fi

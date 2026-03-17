#!/usr/bin/env bash
# scan-secrets.sh — Detect secrets and credentials in the codebase
# Usage: ./scan-secrets.sh [path] [--json]
set -euo pipefail

SCAN_PATH="${1:-.}"
OUTPUT_FORMAT="${2:-text}"

echo "Scanning for secrets in: $SCAN_PATH"

# Check for common secret patterns
PATTERNS=(
  'AKIA[0-9A-Z]{16}'                          # AWS Access Key
  'sk-[a-zA-Z0-9]{32,}'                        # OpenAI / Stripe keys
  'ghp_[a-zA-Z0-9]{36}'                        # GitHub personal token
  'xoxb-[0-9]+-[a-zA-Z0-9]+'                   # Slack bot token
  'postgresql://[^@]+:[^@]+@'                   # Postgres connection string with password
  'mysql://[^@]+:[^@]+@'                        # MySQL connection string with password
  'PRIVATE KEY'                                 # PEM private key
  'password\s*=\s*["\x27][^\s"]+["\x27]'       # Inline password assignment
  'secret\s*=\s*["\x27][^\s"]+["\x27]'         # Inline secret assignment
  'api[_-]?key\s*=\s*["\x27][^\s"]+["\x27]'    # Inline API key assignment
)

FINDINGS=()

for pattern in "${PATTERNS[@]}"; do
  while IFS= read -r line; do
    FINDINGS+=("$line")
  done < <(grep -rn --include="*.{js,ts,py,env,json,yaml,yml,sh,tf}" \
    -E "$pattern" \
    --exclude-dir="{node_modules,.git,.next,dist,__pycache__,venv}" \
    "$SCAN_PATH" 2>/dev/null || true)
done

if [[ "$OUTPUT_FORMAT" == "--json" ]]; then
  echo '{"findings":['
  for i in "${!FINDINGS[@]}"; do
    echo "  $(printf '%s' "${FINDINGS[$i]}" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')"
    [[ $i -lt $((${#FINDINGS[@]}-1)) ]] && echo ","
  done
  echo ']}'
else
  if [[ ${#FINDINGS[@]} -eq 0 ]]; then
    echo "✓ No secrets detected"
  else
    echo "⚠ Found ${#FINDINGS[@]} potential secret(s):"
    printf '%s\n' "${FINDINGS[@]}"
  fi
fi

# Check git history for removed secrets
echo ""
echo "Checking git log for historical secret patterns..."
git log --all --full-history -S "AKIA" -- . 2>/dev/null | head -20 || true

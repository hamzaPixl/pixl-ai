#!/usr/bin/env bash
# scan-owasp.sh — Check for common OWASP Top 10 patterns
# Usage: ./scan-owasp.sh [path]
set -euo pipefail

SCAN_PATH="${1:-.}"
LANG="${2:-auto}"

echo "OWASP Top 10 pattern scan: $SCAN_PATH"
echo "======================================="

# Detect language if auto
if [[ "$LANG" == "auto" ]]; then
  if find "$SCAN_PATH" -name "*.py" -not -path "*/node_modules/*" | head -1 | grep -q .; then
    LANG="python"
  elif find "$SCAN_PATH" -name "*.ts" -not -path "*/node_modules/*" | head -1 | grep -q .; then
    LANG="typescript"
  else
    LANG="unknown"
  fi
  echo "Detected language: $LANG"
fi

# A1: Injection
echo ""
echo "## A1: Injection"
if [[ "$LANG" == "python" ]]; then
  grep -rn --include="*.py" -E "execute\(['\"]|raw\(['\"]|format_map|% .*WHERE" \
    --exclude-dir="{__pycache__,venv,.git}" "$SCAN_PATH" 2>/dev/null | head -20 || echo "✓ No obvious injection patterns"
else
  grep -rn --include="*.{ts,js}" -E "query\(['\"\`].*\$|\.raw\(|String\.raw" \
    --exclude-dir="{node_modules,.git,.next}" "$SCAN_PATH" 2>/dev/null | head -20 || echo "✓ No obvious injection patterns"
fi

# A2: Broken Authentication
echo ""
echo "## A2: Broken Authentication"
grep -rn --include="*.{ts,js,py}" -E "jwt\.sign|jwt\.verify|bcrypt\.|hashlib\.md5|hashlib\.sha1" \
  --exclude-dir="{node_modules,.git,.next,__pycache__}" "$SCAN_PATH" 2>/dev/null | head -20 || echo "✓ No auth patterns found"

# A3: Sensitive Data Exposure
echo ""
echo "## A3: Sensitive Data Exposure"
grep -rn --include="*.{ts,js,py}" -E "console\.log.*password|print.*password|logger.*token" \
  --exclude-dir="{node_modules,.git,.next,__pycache__}" "$SCAN_PATH" 2>/dev/null | head -20 || echo "✓ No obvious data exposure"

# A5: Security Misconfiguration
echo ""
echo "## A5: Security Misconfiguration"
grep -rn --include="*.{ts,js,py}" -E "debug\s*=\s*True|DEBUG\s*=\s*true|cors\(\)" \
  --exclude-dir="{node_modules,.git,.next,__pycache__}" "$SCAN_PATH" 2>/dev/null | head -20 || echo "✓ No obvious misconfigurations"

# A7: XSS
echo ""
echo "## A7: XSS"
grep -rn --include="*.{ts,tsx,js,jsx}" -E "dangerouslySetInnerHTML|\.innerHTML\s*=|document\.write" \
  --exclude-dir="{node_modules,.git,.next}" "$SCAN_PATH" 2>/dev/null | head -20 || echo "✓ No obvious XSS vectors"

echo ""
echo "Scan complete. Review findings above — false positives expected."
echo "Run /security-scan for full OWASP audit with severity classification."

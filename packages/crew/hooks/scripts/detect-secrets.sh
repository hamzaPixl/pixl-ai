#!/usr/bin/env bash
# PreToolUse hook: regex-based secret detection for Write/Edit operations.
# Reads tool input JSON from stdin. Exits 0 (clean) or 2 (blocked).

source "$(dirname "$0")/_common.sh"

read_stdin
require_jq

# Extract the content being written (new_string for Edit, content for Write)
CONTENT=$(jq_input -r '(.tool_input.content // .tool_input.new_string // "")')

# If no content to check, allow
if [ -z "$CONTENT" ]; then
  exit 0
fi

# Regex patterns for common secrets (POSIX ERE only — no grep -P)
PATTERNS=(
  'sk_live_[a-zA-Z0-9]{24,}'                        # Stripe live secret key
  'sk_test_[a-zA-Z0-9]{24,}'                        # Stripe test secret key
  'AKIA[A-Z0-9]{16}'                                 # AWS access key ID
  'ghp_[a-zA-Z0-9]{36}'                             # GitHub personal access token
  'gho_[a-zA-Z0-9]{36}'                             # GitHub OAuth token
  'xox[bpas]-[a-zA-Z0-9-]+'                         # Slack tokens
  '-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----'     # Private keys
  'PRIVATE_KEY[[:space:]]*=[[:space:]]*"[^"]{20,}'  # Private key in env var
  'password[[:space:]]*[:=][[:space:]]*"[^"]{8,}'   # Plaintext password assignment
  'secret[[:space:]]*[:=][[:space:]]*"[^"]{8,}'     # Plaintext secret assignment
)

for pattern in "${PATTERNS[@]}"; do
  if echo "$CONTENT" | grep -qEi "$pattern" 2>/dev/null; then
    echo "Potential secret detected matching pattern: $pattern. Review the content before committing."
    exit 2
  fi
done

exit 0

#!/usr/bin/env bash
# scaffold-interactive.sh — Interactive wrapper around scaffold.sh.
# Usage: ./scripts/scaffold-interactive.sh <stack-dir>
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <stack-dir>"; exit 1
fi

STACK_DIR="$1"
[[ ! -d "$STACK_DIR" ]] && echo "Error: stack directory '$STACK_DIR' does not exist" && exit 1

MANIFEST="$STACK_DIR/manifest.yaml"
[[ ! -f "$MANIFEST" ]] && echo "Error: manifest.yaml not found in '$STACK_DIR'" && exit 1

# ─── Parse tokens from manifest.yaml ────────────────────────────────
# Supports both token_registry: (nextjs) and tokens: (saas) sections.
declare -a TOKEN_NAMES=()
declare -A TOKEN_EXAMPLES=() TOKEN_FALLBACKS=() TOKEN_HAS_FALLBACK=()
in_tokens=false
current_token=""

while IFS= read -r line; do
  if [[ "$line" =~ ^(token_registry|tokens):$ ]]; then
    in_tokens=true; continue
  fi
  if $in_tokens && [[ "$line" =~ ^[a-z_] && ! "$line" =~ ^[[:space:]] ]]; then
    in_tokens=false; continue
  fi
  $in_tokens || continue

  # Token name (indented UPPER_CASE key)
  if [[ "$line" =~ ^[[:space:]]{2}([A-Z][A-Z0-9_]+):$ ]]; then
    current_token="${BASH_REMATCH[1]}"
    [[ "$current_token" == "ENTITIES" ]] && { current_token=""; continue; }
    TOKEN_NAMES+=("$current_token")
    TOKEN_HAS_FALLBACK["$current_token"]=false
    continue
  fi
  [[ -z "$current_token" ]] && continue

  # Example value
  if [[ "$line" =~ ^[[:space:]]+(example):[[:space:]]*(.+)$ ]]; then
    val="${BASH_REMATCH[2]}"; val="${val#\"}"; val="${val%\"}"
    TOKEN_EXAMPLES["$current_token"]="$val"
  fi
  # Fallback or default value
  if [[ "$line" =~ ^[[:space:]]+(fallback|default):[[:space:]]*(.+)$ ]]; then
    val="${BASH_REMATCH[2]}"; val="${val#\"}"; val="${val%\"}"
    TOKEN_FALLBACKS["$current_token"]="$val"
    TOKEN_HAS_FALLBACK["$current_token"]=true
  fi
done < "$MANIFEST"

[[ ${#TOKEN_NAMES[@]} -eq 0 ]] && echo "Error: no tokens found in manifest" && exit 1

echo ""
echo "=== Pixl Crew — Interactive Scaffold ==="
echo "Stack: $STACK_DIR  |  Tokens: ${#TOKEN_NAMES[@]}"

# ─── Prompt for each token ───────────────────────────────────────────
TOKENS_FILE=$(mktemp /tmp/scaffold-XXXX-tokens.txt)

for token in "${TOKEN_NAMES[@]}"; do
  example="${TOKEN_EXAMPLES[$token]:-}"
  has_fallback="${TOKEN_HAS_FALLBACK[$token]}"
  fallback="${TOKEN_FALLBACKS[$token]:-}"

  prompt="  ${token}"
  [[ "$has_fallback" == "false" ]] && prompt="$prompt [REQUIRED]"
  [[ -n "$example" ]] && prompt="$prompt (e.g. ${example})"
  [[ "$has_fallback" == "true" ]] && prompt="$prompt [default: ${fallback}]"
  prompt="$prompt: "

  while true; do
    read -rp "$prompt" value
    [[ -z "$value" && "$has_fallback" == "true" ]] && value="$fallback"
    if [[ -z "$value" && "$has_fallback" == "false" ]]; then
      echo "    ^ required — please enter a value"; continue
    fi
    break
  done
  echo "${token}=${value}" >> "$TOKENS_FILE"
done
echo ""
# ─── Target directory ────────────────────────────────────────────────
read -rp "  Target directory: " TARGET_DIR
if [[ -z "$TARGET_DIR" ]]; then
  echo "Error: target directory is required"; rm -f "$TOKENS_FILE"; exit 1
fi

# ─── Optional features ──────────────────────────────────────────────
FEATURES_FILE=""
echo ""
echo "  Optional features:"
read -rp "    Enable stripe? [y/N] " feat_stripe
read -rp "    Enable supabase? [y/N] " feat_supabase
read -rp "    Enable blog? [y/N] " feat_blog

for pair in "stripe:$feat_stripe" "supabase:$feat_supabase" "blog:$feat_blog"; do
  name="${pair%%:*}"; answer="${pair#*:}"
  if [[ "$answer" =~ ^[yY] ]]; then
    [[ -z "$FEATURES_FILE" ]] && FEATURES_FILE=$(mktemp /tmp/scaffold-XXXX-features.txt)
    echo "$name" >> "$FEATURES_FILE"
  fi
done

# ─── Run scaffold ───────────────────────────────────────────────────
echo ""
echo "Running scaffold..."
CMD=("bash" "$SCRIPT_DIR/scaffold.sh" "$STACK_DIR" "$TARGET_DIR" "$TOKENS_FILE")
[[ -n "$FEATURES_FILE" ]] && CMD+=("$FEATURES_FILE")

"${CMD[@]}"

# Clean up features file (tokens file is cleaned by scaffold.sh)
[[ -n "$FEATURES_FILE" ]] && rm -f "$FEATURES_FILE"

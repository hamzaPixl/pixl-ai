#!/usr/bin/env bash
# scaffold.sh — Bulk token replacement for studio stack templates.
#
# Usage:
#   ./scripts/scaffold.sh <source-stack-dir> <target-dir> <tokens-file> [features-file]
#
# tokens-file: KEY=VALUE per line (e.g., PROJECT_NAME=Acme Corp)
# features-file: one feature name per line (e.g., stripe, supabase, blog)
# Lines starting with # are ignored.
#
# .tmpl files get token replacement ({{TOKEN}} → value) and .tmpl stripped.
# Static files are copied verbatim.
# Files with `condition` in manifest.yaml are only copied if the matching feature is enabled.

set -euo pipefail

if [[ $# -lt 3 || $# -gt 4 ]]; then
  echo "Usage: $0 <source-stack-dir> <target-dir> <tokens-file> [features-file]"
  exit 1
fi

SOURCE_DIR="$1"
TARGET_DIR="$2"
TOKENS_FILE="$3"
FEATURES_FILE="${4:-}"

if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "Error: source directory '$SOURCE_DIR' does not exist"
  exit 1
fi

if [[ ! -f "$TOKENS_FILE" ]]; then
  echo "Error: tokens file '$TOKENS_FILE' does not exist"
  exit 1
fi

# ─── Load enabled features ───────────────────────────────────────
declare -A FEATURES
if [[ -n "$FEATURES_FILE" && -f "$FEATURES_FILE" ]]; then
  while IFS= read -r line; do
    [[ -z "$line" || "$line" == \#* ]] && continue
    FEATURES["$line"]=1
  done < "$FEATURES_FILE"
  echo "Loaded ${#FEATURES[@]} features from $FEATURES_FILE"
fi

# ─── Parse manifest conditions ────────────────────────────────────
MANIFEST="$SOURCE_DIR/manifest.yaml"
declare -A CONDITIONS
if [[ -f "$MANIFEST" ]]; then
  # Simple YAML parser: extract file→condition mappings
  # Looks for patterns like:  - path: some/file.tmpl
  #                             condition: stripe
  current_path=""
  while IFS= read -r line; do
    if [[ "$line" =~ ^[[:space:]]*-[[:space:]]*path:[[:space:]]*(.+)$ ]]; then
      current_path="${BASH_REMATCH[1]}"
      current_path="${current_path%\"}"
      current_path="${current_path#\"}"
    elif [[ "$line" =~ ^[[:space:]]*condition:[[:space:]]*(.+)$ && -n "$current_path" ]]; then
      cond="${BASH_REMATCH[1]}"
      cond="${cond%\"}"
      cond="${cond#\"}"
      CONDITIONS["$current_path"]="$cond"
      current_path=""
    fi
  done < "$MANIFEST"
  echo "Loaded ${#CONDITIONS[@]} conditional files from manifest"
fi

# ─── Parse ENTITIES token (comma-separated PascalCase:PluralPascalCase pairs) ─
# Format: "Article,Category:Categories,Tag" — plural defaults to ${name}s
ENTITIES=()        # PascalCase names
ENTITIES_PLURAL=() # PascalCase plurals

# ─── Build sed script from tokens file ─────────────────────────────
SED_SCRIPT=""
token_count=0
while IFS= read -r line; do
  [[ -z "$line" || "$line" == \#* ]] && continue
  key="${line%%=*}"
  value="${line#*=}"

  # Collect entity list for multi-entity expansion
  if [[ "$key" == "ENTITIES" ]]; then
    IFS=',' read -ra _raw_entities <<< "$value"
    for _entry in "${_raw_entities[@]}"; do
      if [[ "$_entry" == *:* ]]; then
        ENTITIES+=("${_entry%%:*}")
        ENTITIES_PLURAL+=("${_entry#*:}")
      else
        ENTITIES+=("$_entry")
        ENTITIES_PLURAL+=("${_entry}s")
      fi
    done
    continue
  fi

  # Escape sed special chars in value (& / \ newline)
  escaped_value=$(printf '%s' "$value" | sed 's/[&/\]/\\&/g')
  SED_SCRIPT="${SED_SCRIPT}s/{{${key}}}/${escaped_value}/g;"
  token_count=$((token_count + 1))
done < "$TOKENS_FILE"

echo "Loaded $token_count tokens from $TOKENS_FILE"
if [[ ${#ENTITIES[@]} -gt 0 ]]; then
  echo "Entities to scaffold: ${ENTITIES[*]}"
fi

# ─── Token validation against manifest ───────────────────────────────
# Parse manifest for required/optional tokens and verify they are present
# in the loaded tokens file. Required = no fallback/default field.
if [[ -f "$MANIFEST" ]]; then
  in_tokens=false
  current_token=""
  has_fallback=false
  missing_required=()
  missing_optional=()

  while IFS= read -r mline; do
    # Detect start of token section (token_registry: or tokens:)
    if [[ "$mline" =~ ^(token_registry|tokens):$ ]]; then
      in_tokens=true
      continue
    fi
    # Detect end of token section (next top-level key)
    if $in_tokens && [[ "$mline" =~ ^[a-z_] && ! "$mline" =~ ^[[:space:]] ]]; then
      # Flush last token
      if [[ -n "$current_token" ]]; then
        if ! grep -q "^${current_token}=" "$TOKENS_FILE" 2>/dev/null; then
          if $has_fallback; then
            missing_optional+=("$current_token")
          else
            missing_required+=("$current_token")
          fi
        fi
      fi
      in_tokens=false
      current_token=""
      continue
    fi

    if ! $in_tokens; then continue; fi

    # New token key
    if [[ "$mline" =~ ^[[:space:]]{2}([A-Z][A-Z0-9_]+):$ ]]; then
      # Flush previous token
      if [[ -n "$current_token" ]]; then
        if ! grep -q "^${current_token}=" "$TOKENS_FILE" 2>/dev/null; then
          if $has_fallback; then
            missing_optional+=("$current_token")
          else
            missing_required+=("$current_token")
          fi
        fi
      fi
      current_token="${BASH_REMATCH[1]}"
      # Skip ENTITIES — handled separately
      [[ "$current_token" == "ENTITIES" ]] && { current_token=""; continue; }
      has_fallback=false
      continue
    fi

    # Detect fallback or default field
    if [[ "$mline" =~ ^[[:space:]]+(fallback|default):[[:space:]]* ]]; then
      has_fallback=true
    fi
  done < "$MANIFEST"

  # Flush final token
  if [[ -n "$current_token" ]]; then
    if ! grep -q "^${current_token}=" "$TOKENS_FILE" 2>/dev/null; then
      if $has_fallback; then
        missing_optional+=("$current_token")
      else
        missing_required+=("$current_token")
      fi
    fi
  fi

  # Report warnings for optional tokens
  if [[ ${#missing_optional[@]} -gt 0 ]]; then
    echo "Warning: missing optional tokens (will use fallback): ${missing_optional[*]}"
  fi

  # Fail for missing required tokens
  if [[ ${#missing_required[@]} -gt 0 ]]; then
    echo "Error: missing required tokens (no fallback defined): ${missing_required[*]}"
    exit 1
  fi
fi

# ─── Process files ─────────────────────────────────────────────────
count=0
tmpl_count=0
static_count=0
skipped_count=0

while IFS= read -r -d '' src_file; do
  rel_path="${src_file#"$SOURCE_DIR"/}"

  # Skip manifest and readme
  [[ "$rel_path" == "manifest.yaml" || "$rel_path" == "README.md" ]] && continue

  # Check condition gate — skip file if its feature is not enabled
  if [[ -n "${CONDITIONS[$rel_path]:-}" ]]; then
    required_feature="${CONDITIONS[$rel_path]}"
    if [[ -z "${FEATURES[$required_feature]:-}" ]]; then
      skipped_count=$((skipped_count + 1))
      continue
    fi
  fi

  target_path="$TARGET_DIR/$rel_path"
  mkdir -p "$(dirname "$target_path")"

  if [[ "$rel_path" == *.tmpl ]]; then
    target_path="${target_path%.tmpl}"
    sed "$SED_SCRIPT" "$src_file" > "$target_path"
    tmpl_count=$((tmpl_count + 1))
  else
    rsync -a --exclude='node_modules' --exclude='.turbo' --exclude='dist' "$src_file" "$target_path"
    static_count=$((static_count + 1))
  fi

  count=$((count + 1))
done < <(find "$SOURCE_DIR" -type f -print0 | sort -z)

# ─── Multi-entity expansion ───────────────────────────────────────────
# If ENTITIES token was provided, duplicate entity-specific files for each entity.
# Only files whose *filename* contains the primary entity slug are duplicated.
# Content replacement is scoped to {{ENTITY_*}} tokens only (no raw slug replacement).
entity_count=0
if [[ ${#ENTITIES[@]} -gt 1 ]]; then
  # Read primary entity tokens for reference
  primary_name=$(grep -m1 'ENTITY_NAME=' "$TOKENS_FILE" 2>/dev/null | cut -d= -f2 || true)
  primary_slug=$(grep -m1 'ENTITY_SLUG=' "$TOKENS_FILE" 2>/dev/null | cut -d= -f2 || true)
  primary_plural=$(grep -m1 'ENTITY_PLURAL=' "$TOKENS_FILE" 2>/dev/null | cut -d= -f2 || true)
  primary_plural_slug=$(grep -m1 'ENTITY_PLURAL_SLUG=' "$TOKENS_FILE" 2>/dev/null | cut -d= -f2 || true)

  # The first entity is already scaffolded via the primary ENTITY_* tokens.
  # For additional entities, duplicate entity-specific files with token replacement.
  for (( i=1; i<${#ENTITIES[@]}; i++ )); do
    entity_pascal="${ENTITIES[$i]}"
    entity_plural_pascal="${ENTITIES_PLURAL[$i]}"

    # Validate entity name is PascalCase alphanumeric
    if [[ ! "$entity_pascal" =~ ^[A-Z][a-zA-Z0-9]*$ ]]; then
      echo "Warning: skipping invalid entity name '$entity_pascal' (must match ^[A-Z][a-zA-Z0-9]*$)"
      continue
    fi

    # Derive slug variants (BSD sed compatible — no \L)
    entity_slug=$(printf '%s' "$entity_pascal" | sed 's/\([A-Z]\)/-\1/g' | sed 's/^-//' | tr '[:upper:]' '[:lower:]')
    entity_plural_slug=$(printf '%s' "$entity_plural_pascal" | sed 's/\([A-Z]\)/-\1/g' | sed 's/^-//' | tr '[:upper:]' '[:lower:]')

    if [[ -n "$primary_slug" ]]; then
      while IFS= read -r -d '' efile; do
        # Replace primary slug in *filename* only
        new_file="${efile//$primary_slug/$entity_slug}"
        if [[ "$new_file" != "$efile" ]]; then
          mkdir -p "$(dirname "$new_file")"
          # Replace only {{ENTITY_*}} tokens and the primary entity identifiers in content
          sed \
            -e "s|${primary_name}|${entity_pascal}|g" \
            -e "s|${primary_slug}|${entity_slug}|g" \
            -e "s|${primary_plural}|${entity_plural_pascal}|g" \
            -e "s|${primary_plural_slug}|${entity_plural_slug}|g" \
            "$efile" > "$new_file"
          entity_count=$((entity_count + 1))
        fi
      done < <(find "$TARGET_DIR" -type f -name "*${primary_slug}*" -print0)
    fi
  done
fi

# ─── Selective foundation pruning ────────────────────────────────────────
# If FOUNDATION_DEPS is specified in tokens file, remove unused foundation packages.
pruned_count=0
foundation_deps=$(grep -m1 'FOUNDATION_DEPS=' "$TOKENS_FILE" 2>/dev/null | cut -d= -f2 || true)
if [[ -n "$foundation_deps" && -d "$TARGET_DIR/foundation" ]]; then
  IFS=',' read -ra _wanted_deps <<< "$foundation_deps"
  declare -A WANTED_DEPS
  for dep in "${_wanted_deps[@]}"; do
    dep=$(echo "$dep" | xargs)  # trim whitespace
    WANTED_DEPS["$dep"]=1
  done

  for pkg_dir in "$TARGET_DIR/foundation"/*/; do
    pkg_name=$(basename "$pkg_dir")
    if [[ -z "${WANTED_DEPS[$pkg_name]:-}" ]]; then
      rm -rf "$pkg_dir"
      pruned_count=$((pruned_count + 1))
    fi
  done
fi

echo ""
echo "Scaffold complete:"
echo "  Total files: $count"
echo "  Templates processed: $tmpl_count"
echo "  Static files copied: $static_count"
echo "  Conditional files skipped: $skipped_count"
if [[ $entity_count -gt 0 ]]; then
  echo "  Entity expansions: $entity_count"
fi
if [[ $pruned_count -gt 0 ]]; then
  echo "  Foundation packages pruned: $pruned_count"
fi
echo "  Target directory: $TARGET_DIR"

# ─── Cleanup temp tokens file ─────────────────────────────────────
if [[ "$TOKENS_FILE" == /tmp/*-tokens.txt ]]; then
  rm -f "$TOKENS_FILE"
  echo "  Cleaned up temp tokens file: $TOKENS_FILE"
fi

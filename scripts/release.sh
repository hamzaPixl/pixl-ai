#!/usr/bin/env bash
set -euo pipefail

# Usage: bash scripts/release.sh [patch|minor|major]
BUMP="${1:-patch}"

# Read current version from root pyproject.toml
CURRENT=$(grep '^version' pyproject.toml | head -1 | sed 's/.*"\(.*\)".*/\1/')
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT"

case "$BUMP" in
  major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
  minor) MINOR=$((MINOR + 1)); PATCH=0 ;;
  patch) PATCH=$((PATCH + 1)) ;;
  *) echo "Usage: $0 [patch|minor|major]"; exit 1 ;;
esac

NEW="$MAJOR.$MINOR.$PATCH"
echo "Bumping $CURRENT → $NEW"

# Update version in all pyproject.toml files
for f in pyproject.toml packages/engine/pyproject.toml packages/cli/pyproject.toml; do
  if [ -f "$f" ]; then
    sed -i '' "s/^version = \"$CURRENT\"/version = \"$NEW\"/" "$f"
  fi
done

# Update crew plugin.json version
PLUGIN_JSON="packages/crew/.claude-plugin/plugin.json"
if [ -f "$PLUGIN_JSON" ]; then
  # Use python for safe JSON update
  python3 -c "
import json, sys
with open('$PLUGIN_JSON') as f: d = json.load(f)
d['version'] = '$NEW'
with open('$PLUGIN_JSON', 'w') as f: json.dump(d, f, indent=2)
print(f'  Updated {\"$PLUGIN_JSON\"} → $NEW')
"
fi

git add -A
git commit -m "release: v$NEW"
git tag "v$NEW"
echo "Tagged v$NEW. Run 'git push && git push --tags' to publish."

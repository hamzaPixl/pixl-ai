#!/usr/bin/env bash
# release.sh — Bump version, changelog, tag, push, refresh local install.
#
# Usage:
#   make release            # patch bump (1.7.0 → 1.7.1)
#   make release BUMP=minor # minor bump (1.7.0 → 1.8.0)
#   make release BUMP=major # major bump (1.7.0 → 2.0.0)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR/.."
MANIFEST="$ROOT/.claude-plugin/plugin.json"
BUMP="${BUMP:-patch}"

G='\033[0;32m' D='\033[2m' R='\033[0m'

# ─── Read current version ────────────────────────────────────────────────────

current=$(grep -o '"version": "[^"]*"' "$MANIFEST" | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+')
IFS='.' read -r major minor patch <<< "$current"

case "$BUMP" in
  major) ((major++)); minor=0; patch=0 ;;
  minor) ((minor++)); patch=0 ;;
  patch) ((patch++)) ;;
  *) echo "Invalid BUMP=$BUMP (use major/minor/patch)"; exit 1 ;;
esac

next="${major}.${minor}.${patch}"

echo ""
echo -e "  ${G}release${R} ${D}${current} → ${next}${R}"
echo ""

# ─── Bump version in manifest ────────────────────────────────────────────────

perl -i -pe "s/\"version\": \"${current}\"/\"version\": \"${next}\"/" "$MANIFEST"
echo -e "  ${G}✓${R} version ${D}${next}${R}"

# ─── Generate changelog from commits since last tag ──────────────────────────

last_tag=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
if [[ -n "$last_tag" ]]; then
  log=$(git log "${last_tag}..HEAD" --oneline --no-decorate 2>/dev/null || echo "")
else
  log=$(git log --oneline --no-decorate -20 2>/dev/null || echo "")
fi

echo -e "  ${G}✓${R} changelog"
if [[ -n "$log" ]]; then
  echo "$log" | while IFS= read -r line; do
    echo -e "    ${D}${line}${R}"
  done
fi

# ─── Commit, tag, push ──────────────────────────────────────────────────────

git add -A
git commit -m "release: v${next}" > /dev/null 2>&1
git tag "v${next}"
echo -e "  ${G}✓${R} commit + tag ${D}v${next}${R}"

git push && git push --tags > /dev/null 2>&1
echo -e "  ${G}✓${R} pushed"

# ─── Refresh local install ──────────────────────────────────────────────────

claude plugin update pixl-crew@pixl-local > /dev/null 2>&1 && \
  echo -e "  ${G}✓${R} plugin refreshed" || \
  echo -e "  ${D}(plugin refresh skipped — not installed locally)${R}"

echo ""
echo -e "  ${G}✓${R} v${next} released"
echo ""

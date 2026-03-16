#!/usr/bin/env bash
# Download assets from a JSON URL list to typed subdirectories.
# Usage: bash scripts/download-assets.sh <asset-urls.json> <output-dir>
#
# Input JSON format: [{"url": "https://...", "type": "image|font|background"}]
# Output: <output-dir>/{images,fonts,backgrounds}/<filename> + asset-manifest.json

set -euo pipefail

INPUT_JSON="${1:?Usage: download-assets.sh <asset-urls.json> <output-dir>}"
OUTPUT_DIR="${2:?Usage: download-assets.sh <asset-urls.json> <output-dir>}"

mkdir -p "$OUTPUT_DIR/images" "$OUTPUT_DIR/fonts" "$OUTPUT_DIR/backgrounds"

MANIFEST="$OUTPUT_DIR/asset-manifest.json"
echo '[' > "$MANIFEST"
FIRST=true

# Parse JSON array and download each asset (requires jq)
if ! command -v jq &>/dev/null; then
  echo "Error: jq is required but not installed. Install with: brew install jq (macOS) or apt-get install jq (Linux)"
  exit 1
fi

COUNT=$(jq 'length' "$INPUT_JSON" 2>/dev/null || echo 0)

if [ "$COUNT" -eq 0 ]; then
  echo "No assets to download."
  echo ']' >> "$MANIFEST"
  exit 0
fi

for i in $(seq 0 $((COUNT - 1))); do
  URL=$(jq -r ".[$i].url" "$INPUT_JSON")
  TYPE=$(jq -r ".[$i].type // \"image\"" "$INPUT_JSON")

  # Determine subdirectory
  case "$TYPE" in
    font)       SUBDIR="fonts" ;;
    background) SUBDIR="backgrounds" ;;
    *)          SUBDIR="images" ;;
  esac

  # Extract filename from URL, fallback to hash
  FILENAME=$(basename "$URL" | sed 's/[?#].*//' | head -c 200)
  if [ -z "$FILENAME" ] || [ "$FILENAME" = "/" ]; then
    if command -v md5sum &>/dev/null; then
      FILENAME=$(echo "$URL" | md5sum | cut -c1-12)
    elif command -v md5 &>/dev/null; then
      FILENAME=$(echo "$URL" | md5 | cut -c1-12)
    else
      FILENAME="asset-$i"
    fi
  fi

  LOCAL_PATH="$SUBDIR/$FILENAME"
  FULL_PATH="$OUTPUT_DIR/$LOCAL_PATH"

  # Download, skip on failure
  if curl -sL --max-time 15 --fail -o "$FULL_PATH" "$URL" 2>/dev/null; then
    if [ "$FIRST" = true ]; then
      FIRST=false
    else
      echo ',' >> "$MANIFEST"
    fi
    printf '  {"original_url": "%s", "local_path": "%s", "type": "%s"}' "$URL" "$LOCAL_PATH" "$TYPE" >> "$MANIFEST"
    echo "  ✓ $LOCAL_PATH"
  else
    echo "  ✗ Failed: $URL"
  fi
done

echo '' >> "$MANIFEST"
echo ']' >> "$MANIFEST"

echo ""
echo "Manifest written to $MANIFEST"
echo "Downloaded to $OUTPUT_DIR"

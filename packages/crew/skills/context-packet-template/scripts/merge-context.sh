#!/usr/bin/env bash
# merge-context.sh — Merge two context packet JSON files.
# Usage: merge-context.sh <packet-a.json> <packet-b.json> [> merged.json]
#
# Simple overlay: scalar fields from packet-b override packet-a.
# Array fields (findings, constraints, endpoints) are concatenated and deduplicated.

set -euo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: $0 <packet-a.json> <packet-b.json>" >&2
  exit 1
fi

A="$1"
B="$2"

if ! command -v jq &>/dev/null; then
  echo "Error: jq is required. Install with: brew install jq" >&2
  exit 1
fi

# Deep merge with array concatenation and deduplication
jq -s '
  def merge_arrays:
    if (type == "array") then unique else . end;

  def deep_merge(b):
    . as $a |
    if ($a | type) == "object" and (b | type) == "object" then
      ($a | keys) + (b | keys) | unique | map(
        . as $k |
        if ($a[$k] | type) == "array" and (b[$k] | type) == "array" then
          { ($k): ($a[$k] + b[$k] | unique) }
        elif ($a | has($k)) and (b | has($k)) then
          { ($k): ($a[$k] | deep_merge(b[$k])) }
        elif b | has($k) then
          { ($k): b[$k] }
        else
          { ($k): $a[$k] }
        end
      ) | add // {}
    else b end;

  .[0] | deep_merge(.[1])
' "$A" "$B"

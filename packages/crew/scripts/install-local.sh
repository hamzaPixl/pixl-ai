#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PLUGIN_JSON="$ROOT_DIR/.claude-plugin/plugin.json"

if [ ! -f "$PLUGIN_JSON" ]; then
  echo "pixl-crew plugin.json not found at $PLUGIN_JSON" >&2
  exit 1
fi

CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
PLUGINS_DIR="$CLAUDE_DIR/plugins"
INSTALLED_FILE="$PLUGINS_DIR/installed_plugins.json"

mkdir -p "$PLUGINS_DIR"

ROOT_DIR="$ROOT_DIR" CLAUDE_DIR="$CLAUDE_DIR" python3 - <<'PY'
import json
import os
from datetime import datetime, timezone
from pathlib import Path

root_dir = Path(os.environ["ROOT_DIR"])
plugin_json = root_dir / ".claude-plugin" / "plugin.json"
claude_dir = Path(os.environ.get("CLAUDE_DIR", str(Path.home() / ".claude")))
plugins_dir = claude_dir / "plugins"
installed_file = plugins_dir / "installed_plugins.json"

plugins_dir.mkdir(parents=True, exist_ok=True)

version = "local"
try:
    data = json.loads(plugin_json.read_text())
    version = str(data.get("version", version))
except Exception:
    pass

payload = {"version": 2, "plugins": {}}
if installed_file.exists():
    try:
        payload = json.loads(installed_file.read_text())
    except Exception:
        payload = {"version": 2, "plugins": {}}

payload.setdefault("version", 2)
plugins = payload.setdefault("plugins", {})

now = datetime.now(timezone.utc).isoformat()
entry = {
    "scope": "user",
    "installPath": str(root_dir),
    "version": version,
    "installedAt": now,
    "lastUpdated": now,
}

plugins["pixl-crew@pixl-local"] = [entry]

installed_file.write_text(json.dumps(payload, indent=2))
print(f"Updated {installed_file}")
PY

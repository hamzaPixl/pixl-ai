"""pixl setup — register crew plugin + install companion plugins."""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import click

from pixl_cli.crew import get_crew_root

COMPANION_PLUGINS = {
    "core": [
        "ralph-loop@claude-plugins-official",
        "commit-commands@claude-plugins-official",
        "playground@claude-plugins-official",
    ],
    "lsp": [
        "typescript-lsp@claude-plugins-official",
        "pyright-lsp@claude-plugins-official",
        "swift-lsp@claude-plugins-official",
    ],
    "security": [
        "supply-chain-risk-auditor@trailofbits",
        "variant-analysis@trailofbits",
        "property-based-testing@trailofbits",
        "static-analysis@trailofbits",
        "semgrep-rule-creator@trailofbits",
    ],
}


def register_crew_plugin(crew_root: Path) -> str:
    """Write crew plugin entry to ~/.claude/plugins/installed_plugins.json."""
    plugins_dir = Path.home() / ".claude" / "plugins"
    installed_file = plugins_dir / "installed_plugins.json"
    plugins_dir.mkdir(parents=True, exist_ok=True)

    # Read version from plugin.json
    version = "local"
    pj = crew_root / ".claude-plugin" / "plugin.json"
    if pj.exists():
        version = json.loads(pj.read_text()).get("version", version)

    # Load or init installed_plugins.json
    payload: dict = {"version": 2, "plugins": {}}
    if installed_file.exists():
        try:
            payload = json.loads(installed_file.read_text())
        except Exception:
            pass
    payload.setdefault("version", 2)
    plugins = payload.setdefault("plugins", {})

    now = datetime.now(UTC).isoformat()
    plugins["pixl-crew@pixl-local"] = [
        {
            "scope": "user",
            "installPath": str(crew_root),
            "version": str(version),
            "installedAt": now,
            "lastUpdated": now,
        }
    ]
    installed_file.write_text(json.dumps(payload, indent=2))
    return version


def _sync(label: str, plugins: list[str]) -> None:
    click.echo(f"  {label} plugins:")
    for ref in plugins:
        name = ref.split("@")[0]
        try:
            subprocess.run(
                ["claude", "plugin", "install", ref],
                capture_output=True,
                timeout=30,
                check=True,
            )
            click.echo(f"    + {name}")
        except Exception:
            click.echo(f"    x {name}")


@click.command()
@click.option("--skip-plugins", is_flag=True, help="Skip companion plugin installation.")
@click.option("--skip-lsp", is_flag=True, help="Skip LSP plugin installation.")
@click.option("--skip-security", is_flag=True, help="Skip security plugin installation.")
def setup(skip_plugins: bool, skip_lsp: bool, skip_security: bool) -> None:
    """Register pixl-crew with Claude Code and install companion plugins."""
    crew_root = get_crew_root()
    version = register_crew_plugin(crew_root)
    click.echo(f"  pixl-crew v{version} registered at {crew_root}")

    if not shutil.which("claude"):
        click.echo("  claude CLI not found — skipping companion plugins")
        return

    if not skip_plugins:
        _sync("core", COMPANION_PLUGINS["core"])
    if not skip_lsp:
        _sync("LSP", COMPANION_PLUGINS["lsp"])
    if not skip_security:
        # Ensure trailofbits marketplace is registered
        subprocess.run(
            ["claude", "plugin", "marketplace", "add", "trailofbits/skills"],
            capture_output=True,
            timeout=30,
        )
        _sync("security", COMPANION_PLUGINS["security"])

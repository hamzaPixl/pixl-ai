"""Resolve the crew plugin directory across install contexts."""

from __future__ import annotations

import os
from pathlib import Path


def get_crew_root() -> Path:
    """Find the crew plugin directory.

    Priority:
    1. PIXL_CREW_ROOT env var (explicit override)
    2. Monorepo: packages/crew/ relative to CLI source
    3. Installed: _crew/ bundled inside this package
    """
    # 1. Explicit override
    override = os.getenv("PIXL_CREW_ROOT")
    if override:
        p = Path(override)
        if (p / ".claude-plugin" / "plugin.json").is_file():
            return p

    # 2. Monorepo development
    cli_pkg = Path(__file__).resolve().parent  # pixl_cli/
    monorepo = cli_pkg.parent.parent / "crew"  # packages/crew/
    if (monorepo / ".claude-plugin" / "plugin.json").is_file():
        return monorepo

    # 3. Bundled in wheel
    bundled = cli_pkg / "_crew"
    if (bundled / ".claude-plugin" / "plugin.json").is_file():
        return bundled

    raise FileNotFoundError(
        "pixl-crew not found. Re-run 'uv tool install pixl' or set PIXL_CREW_ROOT."
    )

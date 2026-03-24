"""Hatch build hook: bundle packages/crew into pixl_cli/_crew/ at sdist time.

When building from source (development installs or sdist creation), the crew
directory lives at ``../crew`` relative to this file.  After the sdist is
assembled and hatch builds the wheel from that sdist, the crew content is
already inside the source tree and is included normally via the ``packages``
declaration.

The hook copies ``packages/crew`` → ``pixl_cli/_crew/`` into the *build
directory* so hatch includes it in both the sdist and the wheel without
requiring ``force-include`` (which resolves paths relative to the package
directory and breaks when building from an sdist temp location).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CrewBundleHook(BuildHookInterface):
    """Copy the crew plugin into pixl_cli/_crew/ before each build."""

    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict) -> None:  # noqa: ARG002
        """Locate crew/ and register its contents for inclusion in the build."""
        # packages/cli/hatch_build.py  →  packages/cli/
        cli_dir = Path(__file__).resolve().parent
        # packages/cli/  →  packages/crew/
        crew_src = cli_dir.parent / "crew"

        if not crew_src.is_dir():
            # Fallback: crew may already be embedded in the sdist as
            # pixl_cli/_crew/ (wheel-from-sdist phase) — nothing to do.
            bundled = cli_dir / "pixl_cli" / "_crew"
            if bundled.is_dir():
                return
            raise FileNotFoundError(
                f"pixl-crew source not found at {crew_src}. "
                "Build from the workspace root: uv build --package pixl-cli"
            )

        dest = cli_dir / "pixl_cli" / "_crew"

        # Always rebuild to keep the bundled copy in sync with the source.
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(crew_src, dest, symlinks=False)

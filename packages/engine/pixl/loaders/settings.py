"""Settings loader."""

from __future__ import annotations

import json
from pathlib import Path

from pixl.loaders.types import LoadedSettings


class SettingsLoader:
    """Loader for .claude/settings.json."""

    def __init__(self, project_path: Path):
        """Initialize loader.

        Args:
            project_path: Project root path
        """
        self.project_path = project_path
        self.settings_path = project_path / ".claude" / "settings.json"

    def load(self) -> LoadedSettings:
        """Load settings.json.

        Returns:
            LoadedSettings with parsed data
        """
        if not self.settings_path.exists():
            return LoadedSettings()

        try:
            content = self.settings_path.read_text()
            data = json.loads(content)
        except (OSError, json.JSONDecodeError):
            return LoadedSettings()

        return LoadedSettings(
            path=str(self.settings_path),
            data=data,
        )


def load_settings(project_path: Path) -> LoadedSettings | None:
    """Load settings from project.

    Args:
        project_path: Project root path

    Returns:
        LoadedSettings or None if not found
    """
    loader = SettingsLoader(project_path)
    result = loader.load()
    return result if result.exists else None

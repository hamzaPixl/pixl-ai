"""Config resolver for multi-source configuration loading.

This module implements a search order for config files:
1. project_path/.pixl/config.yaml               # Local project override
2. ~/.pixl/projects/[PROJECT_NAME]/config.yaml  # Global project-specific override
3. ~/.pixl/config.yaml                          # Global default
4. Bundled defaults                             # Fallback
"""

from pathlib import Path
from typing import Literal

from pixl.paths import (
    get_global_pixl_dir as _get_global_pixl_dir,
)
from pixl.paths import (
    get_pixl_dir as _get_pixl_dir,
)
from pixl.paths import (
    get_project_id as _get_project_id,
)
from pixl.paths import (
    get_project_name as _get_project_name,
)


def get_global_pixl_dir(global_dir: Path | None = None) -> Path:
    """Get global pixl directory (default: ~/.pixl/)."""
    if global_dir is not None:
        return global_dir
    return _get_global_pixl_dir()


def get_project_name(project_path: Path) -> str:
    """Extract project name from path.

    Uses the directory name (last path component).
    Special characters are replaced with hyphens.

    Args:
        project_path: Path to project directory

    Returns:
        Sanitized project name
    """
    return _get_project_name(project_path)


def get_project_global_dir(project_path: Path, global_dir: Path | None = None) -> Path:
    """Get global config directory for a specific project.

    Args:
        project_path: Path to project directory
        global_dir: Override global dir (for testing)

    Returns:
        Path to ~/.pixl/projects/[project_id]/
    """
    base_dir = get_global_pixl_dir(global_dir)
    return base_dir / "projects" / _get_project_id(project_path)


class ConfigSource:
    """Represents where a config file was loaded from."""

    def __init__(
        self,
        path: Path | None,
        source_type: Literal["global-project", "global", "local", "default"],
    ) -> None:
        self.path = path
        self.source_type = source_type

    def __repr__(self) -> str:
        if self.path:
            return f"ConfigSource({self.source_type}, {self.path})"
        return f"ConfigSource({self.source_type})"

    def description(self) -> str:
        """Get a human-readable description."""
        if self.path:
            return f"{self.source_type}: {self.path}"
        return f"{self.source_type}: (bundled defaults)"


def find_config_file(
    project_path: Path,
    config_name: str,
    global_dir: Path | None = None,
) -> tuple[Path | None, ConfigSource]:
    """Find a config file using the search order.

    Args:
        project_path: Current project directory
        config_name: Name of config file (e.g., "agents.yaml")
        global_dir: Override global dir (for testing)

    Returns:
        Tuple of (path to first existing config, source info)
    """
    if global_dir is None:
        global_dir = get_global_pixl_dir()

    pixl_dir = _get_pixl_dir(project_path)
    candidates: list[tuple[Path, Literal["global-project", "global", "local"]]] = [
        (pixl_dir / config_name, "local"),
        (get_project_global_dir(project_path, global_dir) / config_name, "global-project"),
        (global_dir / config_name, "global"),
    ]

    for candidate, source_type in candidates:
        if candidate.exists():
            return candidate, ConfigSource(candidate, source_type)

    # No file found - will use defaults
    return None, ConfigSource(None, "default")


def find_all_config_sources(
    project_path: Path,
    config_name: str,
    global_dir: Path | None = None,
) -> list[ConfigSource]:
    """Find all existing config files for a given config name.

    This is useful for showing which configs would be searched
    and which actually exist.

    Args:
        project_path: Current project directory
        config_name: Name of config file (e.g., "agents.yaml")
        global_dir: Override global dir (for testing)

    Returns:
        List of ConfigSource objects for all existing files
    """
    if global_dir is None:
        global_dir = get_global_pixl_dir()

    # All possible locations
    pixl_dir = _get_pixl_dir(project_path)
    candidates: list[tuple[Path, Literal["global-project", "global", "local"]]] = [
        (pixl_dir / config_name, "local"),
        (get_project_global_dir(project_path, global_dir) / config_name, "global-project"),
        (global_dir / config_name, "global"),
    ]

    sources = []
    for candidate, source_type in candidates:
        if candidate.exists():
            sources.append(ConfigSource(candidate, source_type))

    return sources


def ensure_global_dir() -> Path:
    """Ensure the global pixl directory exists.

    Returns:
        Path to the global pixl directory
    """
    global_dir = get_global_pixl_dir()
    global_dir.mkdir(parents=True, exist_ok=True)
    return global_dir


def ensure_project_global_dir(project_path: Path) -> Path:
    """Ensure the global config directory for a project exists.

    Args:
        project_path: Path to project directory

    Returns:
        Path to the project's global config directory
    """
    ensure_global_dir()
    project_dir = get_project_global_dir(project_path)
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir


__all__ = [
    "get_global_pixl_dir",
    "get_project_name",
    "get_project_global_dir",
    "find_config_file",
    "find_all_config_sources",
    "ConfigSource",
    "ensure_global_dir",
    "ensure_project_global_dir",
]

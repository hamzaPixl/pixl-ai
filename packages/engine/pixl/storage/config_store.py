"""Storage for pixl configuration."""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from pixl.paths import get_pixl_dir

class PixlConfig(BaseModel):
    """Pixl project configuration."""

    # Project info
    project_name: str = Field(default="")
    project_root: str | None = Field(default=None, description="Project root path")
    storage_mode: str = Field(default="standalone")
    version: str = Field(default="0.1.0")

    # Default settings
    default_model: str = Field(default="anthropic/claude-sonnet-4-6")

    # Claude settings
    permission_mode: str = Field(default="bypassPermissions")
    max_tokens: int = Field(default=8192)

    # Plugin integration
    plugin: str | None = Field(
        default=None,
        description="Installed Claude Code plugin for session delegation (e.g. 'pixl-crew')",
    )
    crew_path: str | None = Field(
        default=None,
        description="Local path to pixl-crew plugin (overrides plugin registry)",
    )

    # Git settings
    branch_prefix: str = Field(default="feature/")

    # Paths
    features_dir: str = Field(default="docs/features")
    reviews_dir: str = Field(default="docs/reviews")
    domain_docs_dir: str = Field(default="docs/domain")

    # Files Claude should never read (waste of context)
    ignore_patterns: list[str] = Field(
        default=[
            # Lock files
            "*.lock",
            "package-lock.json",
            "yarn.lock",
            "uv.lock",
            "pnpm-lock.yaml",
            "Cargo.lock",
            "Gemfile.lock",
            "poetry.lock",
            # Dependencies
            "node_modules/",
            ".venv/",
            "venv/",
            ".env/",
            "vendor/",
            "__pycache__/",
            ".pytest_cache/",
            ".mypy_cache/",
            ".ruff_cache/",
            ".next/",
            "dist/",
            "build/",
            "out/",
            ".nuxt/",
            ".output/",
            "target/",
            # Generated
            "*.min.js",
            "*.min.css",
            "*.map",
            "*.pyc",
            "*.pyo",
            # Binary/Media
            "*.png",
            "*.jpg",
            "*.jpeg",
            "*.gif",
            "*.ico",
            "*.svg",
            "*.woff",
            "*.woff2",
            "*.ttf",
            "*.eot",
            "*.pdf",
            "*.zip",
            "*.tar.gz",
            # Reports/Coverage
            "coverage/",
            "htmlcov/",
            ".coverage",
            "__snapshots__/",
        ]
    )

    # High-value files to check first for context
    priority_files: list[str] = Field(
        default=[
            "CLAUDE.md",
            "README.md",
            "pyproject.toml",
            "package.json",
            "Cargo.toml",
            "go.mod",
        ]
    )

class ConfigStore:
    """Manages pixl configuration persistence."""

    def __init__(self, project_path: Path, *, pixl_dir: Path | None = None) -> None:
        self.project_path = project_path
        self.pixl_dir = pixl_dir if pixl_dir is not None else get_pixl_dir(project_path)
        self.config_path = self.pixl_dir / "config.json"

    def _ensure_dir(self) -> None:
        """Ensure .pixl directory exists."""
        self.pixl_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> PixlConfig:
        """Load configuration from disk, or create default."""
        if not self.config_path.exists():
            return PixlConfig()

        with open(self.config_path, encoding="utf-8") as f:
            data = json.load(f)

        return PixlConfig.model_validate(data)

    def save(self, config: PixlConfig) -> None:
        """Save configuration to disk."""
        self._ensure_dir()

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config.model_dump(mode="json"), f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        config = self.load()
        return getattr(config, key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        config = self.load()
        if hasattr(config, key):
            setattr(config, key, value)
            self.save(config)
        else:
            raise ValueError(f"Unknown configuration key: {key}")

    def exists(self) -> bool:
        """Check if config file exists."""
        return self.config_path.exists()

    def initialize(self, project_name: str = "") -> PixlConfig:
        """Create initial configuration."""
        config = PixlConfig(
            project_name=project_name or self.project_path.name,
            project_root=str(self.project_path),
            storage_mode="standalone",
        )
        self.save(config)
        return config

    def get_features_path(self) -> Path:
        """Get absolute path for features directory."""
        config = self.load()
        return self.project_path / config.features_dir

    def get_domain_docs_path(self) -> Path:
        """Get absolute path for domain docs directory."""
        config = self.load()
        return self.project_path / config.domain_docs_dir

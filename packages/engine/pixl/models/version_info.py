"""Version information model for Pixl."""

from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


def get_git_hash() -> str | None:
    """Get the current git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        pass
    return None


def extract_python_version(version_string: str) -> str:
    """Extract Python version from sys.version string."""
    # sys.version format: "3.11.7 (main, Dec  4 2023, 18:10:11) [Clang 15.0.0 ...]"
    match = re.match(r"(\d+\.\d+\.\d+[\w]*)", version_string)
    if match:
        return match.group(1)
    return version_string  # Fallback to original string


class VersionInfo(BaseModel):
    """Comprehensive version information for Pixl.

    This model provides structured version data for CLI output,
    API responses, and Web Console display.
    """

    version: str = Field(
        description="Semantic version of Pixl (e.g., '1.0.0')",
        examples=["1.0.0", "2.1.0-beta", "1.0.0+build.123"],
    )
    build_hash: str = Field(
        description="Git commit hash or build identifier",
        examples=["abc123def456", "unknown"],
        min_length=4,
        max_length=50,
    )
    python_version: str = Field(
        description="Python interpreter version", examples=["3.11.0", "3.12.1", "3.11.7+"]
    )
    build_date: datetime | None = Field(
        default=None, description="When this build was created (ISO 8601 format)"
    )
    api_version: str | None = Field(
        default=None,
        description="API version for compatibility tracking",
        examples=["v1", "v2", "1.0"],
    )

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate semantic version format."""
        if not v or not v.strip():
            raise ValueError("Version cannot be empty")

        v = v.strip()

        # Basic semantic version pattern (allows pre-release and build metadata)
        pattern = r"^\d+\.\d+\.\d+(?:[-+].+)?$"
        if not re.match(pattern, v):
            raise ValueError(
                f"Invalid version format: '{v}'. "
                "Expected semantic version like '1.0.0', '1.0.0-alpha', or '1.0.0+build.123'"
            )

        return v

    @field_validator("build_hash")
    @classmethod
    def validate_build_hash(cls, v: str) -> str:
        """Validate build hash format."""
        if not v or not v.strip():
            raise ValueError("Build hash cannot be empty")

        v = v.strip()

        # Allow alphanumeric characters (case insensitive) or "unknown",
        # min 4 chars for git short hashes
        pattern = r"^[a-fA-F0-9]{4,}$|^[a-zA-Z0-9]{4,}$|^unknown$"
        if not re.match(pattern, v):
            raise ValueError(
                f"Invalid build hash format: '{v}'. "
                "Expected alphanumeric string (min 4 chars) or 'unknown'"
            )

        return v

    @field_validator("python_version")
    @classmethod
    def validate_python_version(cls, v: str) -> str:
        """Validate Python version format."""
        if not v or not v.strip():
            raise ValueError("Python version cannot be empty")

        v = v.strip()

        # Python version pattern: Major.Minor.Patch with optional suffixes (letters, numbers, +, -)
        pattern = r"^\d+\.\d+\.\d+[\w+-]*$"
        if not re.match(pattern, v):
            raise ValueError(
                f"Invalid Python version format: '{v}'. "
                "Expected format like '3.11.0', '3.12.1', or '3.11.7+'"
            )

        return v

    @field_validator("api_version")
    @classmethod
    def validate_api_version(cls, v: str | None) -> str | None:
        """Validate API version format."""
        if v is None:
            return None

        if not v or not v.strip():
            raise ValueError("API version cannot be empty string")

        v = v.strip()

        # API version patterns: v1, v2, v1.0, v1.1, or just 1, 2, 1.0, 1.1
        pattern = r"^(?:v)?\d+(?:\.\d+)?$"
        if not re.match(pattern, v):
            raise ValueError(
                f"Invalid API version format: '{v}'. "
                "Expected format like 'v1', 'v1.0', '1', or '1.0'"
            )

        return v

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with proper datetime serialization."""
        data = self.model_dump()

        if self.build_date:
            data["build_date"] = self.build_date.isoformat()

        return data

    @classmethod
    def from_current_environment(cls, api_version: str | None = None) -> VersionInfo:
        """Create VersionInfo from current runtime environment.

        Args:
            api_version: Optional API version to include

        Returns:
            VersionInfo populated with current environment data
        """
        try:
            from pixl import __version__

            version = __version__
        except ImportError:
            version = "unknown"

        git_hash = get_git_hash()
        build_hash = git_hash if git_hash else "unknown"

        # Extract Python version from sys.version
        python_version = extract_python_version(sys.version)

        return cls(
            version=version,
            build_hash=build_hash,
            python_version=python_version,
            build_date=None,  # Could be populated from build metadata
            api_version=api_version,
        )

    def __str__(self) -> str:
        """String representation for CLI display."""
        parts = [f"pixl version {self.version}"]

        if self.build_hash != "unknown":
            parts.append(f"({self.build_hash[:8]})")

        parts.append(f"Python {self.python_version}")

        if self.api_version:
            parts.append(f"API {self.api_version}")

        return " ".join(parts)

    def to_cli_format(self) -> str:
        """Format for detailed CLI output."""
        lines = [
            f"Pixl Version: {self.version}",
            f"Build Hash: {self.build_hash}",
            f"Python Version: {self.python_version}",
        ]

        if self.build_date:
            lines.append(f"Build Date: {self.build_date.isoformat()}")

        if self.api_version:
            lines.append(f"API Version: {self.api_version}")

        return "\n".join(lines)

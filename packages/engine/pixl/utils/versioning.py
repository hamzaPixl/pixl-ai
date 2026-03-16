"""Semantic versioning utilities for artifact versioning.

This module provides utilities for parsing, validating, and comparing
semantic version numbers (MAJOR.MINOR.PATCH) as specified in https://semver.org/.
"""

import re
from dataclasses import dataclass

@dataclass(frozen=True)
class SemanticVersion:
    """Represents a semantic version number (MAJOR.MINOR.PATCH)."""

    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __lt__(self, other: "SemanticVersion") -> bool:
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __le__(self, other: "SemanticVersion") -> bool:
        return (self.major, self.minor, self.patch) <= (other.major, other.minor, other.patch)

    def __gt__(self, other: "SemanticVersion") -> bool:
        return (self.major, self.minor, self.patch) > (other.major, other.minor, other.patch)

    def __ge__(self, other: "SemanticVersion") -> bool:
        return (self.major, self.minor, self.patch) >= (other.major, other.minor, other.patch)

    def bump_major(self) -> "SemanticVersion":
        """Return a new version with major incremented and minor/patch reset to 0."""
        return SemanticVersion(self.major + 1, 0, 0)

    def bump_minor(self) -> "SemanticVersion":
        """Return a new version with minor incremented and patch reset to 0."""
        return SemanticVersion(self.major, self.minor + 1, 0)

    def bump_patch(self) -> "SemanticVersion":
        """Return a new version with patch incremented."""
        return SemanticVersion(self.major, self.minor, self.patch + 1)

class VersioningError(Exception):
    """Raised when version parsing or validation fails."""

    pass

# Regex pattern for semantic version validation
SEMVER_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")

def parse_version(version_str: str) -> SemanticVersion:
    """Parse a semantic version string into a SemanticVersion object.

    Args:
        version_str: Version string in format "MAJOR.MINOR.PATCH"

    Returns:
        SemanticVersion object

    Raises:
        VersioningError: If version string is invalid
    """
    if not version_str:
        raise VersioningError("Version string cannot be empty")

    match = SEMVER_PATTERN.match(version_str.strip())
    if not match:
        raise VersioningError(
            f"Invalid semantic version format: '{version_str}'. "
            "Expected format: MAJOR.MINOR.PATCH (e.g., '1.2.3')"
        )

    try:
        major, minor, patch = map(int, match.groups())
        return SemanticVersion(major, minor, patch)
    except ValueError as e:
        raise VersioningError(f"Invalid version numbers in '{version_str}': {e}") from e

def validate_version(version_str: str) -> bool:
    """Validate if a string is a valid semantic version.

    Args:
        version_str: Version string to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        parse_version(version_str)
        return True
    except VersioningError:
        return False

def compare_versions(v1: str, v2: str) -> int:
    """Compare two semantic version strings.

    Args:
        v1: First version string
        v2: Second version string

    Returns:
        -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2

    Raises:
        VersioningError: If either version string is invalid
    """
    version1 = parse_version(v1)
    version2 = parse_version(v2)

    if version1 < version2:
        return -1
    elif version1 > version2:
        return 1
    else:
        return 0

def get_next_version(current_version: str, bump_type: str = "patch") -> str:
    """Get the next version based on current version and bump type.

    Args:
        current_version: Current semantic version string
        bump_type: Type of bump - "major", "minor", or "patch" (default)

    Returns:
        Next version string

    Raises:
        VersioningError: If current version is invalid or bump type is unknown
    """
    version = parse_version(current_version)

    if bump_type == "major":
        next_version = version.bump_major()
    elif bump_type == "minor":
        next_version = version.bump_minor()
    elif bump_type == "patch":
        next_version = version.bump_patch()
    else:
        raise VersioningError(
            f"Invalid bump type: '{bump_type}'. Expected one of: 'major', 'minor', 'patch'"
        )

    return str(next_version)

def version_to_tuple(version_str: str) -> tuple[int, int, int]:
    """Convert a version string to a tuple for database storage.

    Args:
        version_str: Semantic version string

    Returns:
        Tuple of (major, minor, patch) integers

    Raises:
        VersioningError: If version string is invalid
    """
    version = parse_version(version_str)
    return (version.major, version.minor, version.patch)

def tuple_to_version(version_tuple: tuple[int, int, int]) -> str:
    """Convert a version tuple back to a string.

    Args:
        version_tuple: Tuple of (major, minor, patch) integers

    Returns:
        Semantic version string
    """
    major, minor, patch = version_tuple
    return f"{major}.{minor}.{patch}"

def get_latest_version(versions: list[str]) -> str | None:
    """Find the latest version from a list of version strings.

    Args:
        versions: List of semantic version strings

    Returns:
        Latest version string, or None if list is empty

    Raises:
        VersioningError: If any version string is invalid
    """
    if not versions:
        return None

    parsed_versions = [parse_version(v) for v in versions]
    latest = max(parsed_versions)
    return str(latest)

def is_version_conflict(new_version: str, existing_versions: list[str]) -> bool:
    """Check if a new version conflicts with existing versions.

    Args:
        new_version: New version to check
        existing_versions: List of existing version strings

    Returns:
        True if there's a conflict (version already exists)

    Raises:
        VersioningError: If any version string is invalid
    """
    parse_version(new_version)

    return new_version in existing_versions

def suggest_next_version(existing_versions: list[str], change_type: str = "patch") -> str:
    """Suggest the next version based on existing versions and change type.

    Args:
        existing_versions: List of existing version strings
        change_type: Type of change - "major", "minor", or "patch"

    Returns:
        Suggested next version string

    Raises:
        VersioningError: If any version is invalid or change_type is unknown
    """
    if not existing_versions:
        return "1.0.0"

    latest = get_latest_version(existing_versions)
    if latest is None:
        return "1.0.0"

    return get_next_version(latest, change_type)

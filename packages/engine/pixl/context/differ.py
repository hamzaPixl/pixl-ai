"""Artifact differ for generating diffs between artifact versions.

Generates unified diffs between consecutive artifact versions and
caches them for reuse by the context compiler.
"""

from __future__ import annotations

import contextlib
import difflib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DIFFS_DIR = ".diffs"


class ArtifactDiffer:
    """Generates and caches diffs between artifact versions.

    Diffs are stored at:
        {artifacts_dir}/.diffs/{artifact_name}.{old_hash[:8]}_{new_hash[:8]}.diff

    Only the most recent diff per artifact is retained.
    """

    def __init__(self, artifacts_dir: Path):
        """Initialize the differ.

        Args:
            artifacts_dir: Directory containing workflow artifacts.
        """
        self.artifacts_dir = artifacts_dir
        self._diffs_dir = artifacts_dir / DIFFS_DIR

    def compute_diff(
        self,
        old_content: str,
        new_content: str,
        artifact_name: str,
        old_hash: str = "",
        new_hash: str = "",
    ) -> str:
        """Compute unified diff between two versions of an artifact.

        Args:
            old_content: Previous version content.
            new_content: Current version content.
            artifact_name: Name of the artifact (for labels).
            old_hash: SHA256 hash of old version (for caching).
            new_hash: SHA256 hash of new version (for caching).

        Returns:
            Unified diff string, or empty string if no changes.
        """
        if old_content == new_content:
            return ""

        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        diff_lines = list(
            difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=f"a/{artifact_name}",
                tofile=f"b/{artifact_name}",
                lineterm="",
            )
        )

        diff_text = "\n".join(diff_lines)

        # Cache if hashes provided
        if old_hash and new_hash:
            self._save_diff(artifact_name, old_hash, new_hash, diff_text)

        return diff_text

    def get_cached_diff(
        self,
        artifact_name: str,
        old_hash: str,
        new_hash: str,
    ) -> str | None:
        """Retrieve a cached diff if available.

        Args:
            artifact_name: Name of the artifact.
            old_hash: SHA256 hash of old version.
            new_hash: SHA256 hash of new version.

        Returns:
            Cached diff text, or None if not cached.
        """
        diff_path = self._diff_path(artifact_name, old_hash, new_hash)
        if diff_path.exists():
            try:
                return diff_path.read_text(encoding="utf-8")
            except OSError as exc:
                logger.debug("Failed to read cached diff: %s", exc)
        return None

    def compute_diff_from_files(
        self,
        old_path: Path,
        new_path: Path,
        artifact_name: str,
        old_hash: str = "",
        new_hash: str = "",
    ) -> str:
        """Compute diff between two file paths.

        Args:
            old_path: Path to previous version.
            new_path: Path to current version.
            artifact_name: Name for labeling.
            old_hash: Optional hash for caching.
            new_hash: Optional hash for caching.

        Returns:
            Unified diff string.
        """
        old_content = ""
        new_content = ""

        if old_path.exists():
            old_content = old_path.read_text(encoding="utf-8")
        if new_path.exists():
            new_content = new_path.read_text(encoding="utf-8")

        return self.compute_diff(old_content, new_content, artifact_name, old_hash, new_hash)

    def _save_diff(
        self,
        artifact_name: str,
        old_hash: str,
        new_hash: str,
        diff_text: str,
    ) -> None:
        """Save diff to disk cache.

        Cleans up previous diffs for the same artifact.

        Args:
            artifact_name: Artifact filename.
            old_hash: Old version hash.
            new_hash: New version hash.
            diff_text: Unified diff content.
        """
        self._diffs_dir.mkdir(parents=True, exist_ok=True)

        self._cleanup_old_diffs(artifact_name)

        diff_path = self._diff_path(artifact_name, old_hash, new_hash)
        try:
            diff_path.write_text(diff_text, encoding="utf-8")
        except OSError as exc:
            logger.warning("Failed to cache diff for %s: %s", artifact_name, exc)

    def _cleanup_old_diffs(self, artifact_name: str) -> None:
        """Remove previous diffs for an artifact, keeping only the latest.

        Args:
            artifact_name: Artifact filename.
        """
        if not self._diffs_dir.exists():
            return

        prefix = f"{artifact_name}."
        for path in self._diffs_dir.iterdir():
            if path.name.startswith(prefix) and path.suffix == ".diff":
                with contextlib.suppress(OSError):
                    path.unlink()

    def _diff_path(self, artifact_name: str, old_hash: str, new_hash: str) -> Path:
        """Build path for a cached diff file.

        Args:
            artifact_name: Artifact filename.
            old_hash: Old version hash.
            new_hash: New version hash.

        Returns:
            Path to the diff file.
        """
        return self._diffs_dir / f"{artifact_name}.{old_hash[:8]}_{new_hash[:8]}.diff"

    def invalidate(self, artifact_name: str) -> None:
        """Remove all cached diffs for an artifact.

        Args:
            artifact_name: Artifact filename.
        """
        self._cleanup_old_diffs(artifact_name)


__all__ = ["ArtifactDiffer"]

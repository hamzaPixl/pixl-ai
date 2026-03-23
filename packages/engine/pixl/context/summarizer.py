"""Artifact summarizer with LLM generation and hash-based caching.

Generates concise 10-30 line summaries of artifacts using Haiku,
caching results keyed by content hash so summaries are only
regenerated when the artifact actually changes.

Fallback to heuristic extraction when LLM is unavailable.
"""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ArtifactSummarizer:
    """Generates and caches artifact summaries.

    Summaries are stored in SQLite (artifact_summaries table) when a DB is available,
    keyed by artifact name and content SHA256 hash.
    If the hash matches on next access, the cached summary is returned.
    """

    def __init__(
        self,
        artifacts_dir: Path,
        llm_query_fn: Any | None = None,
        model: str = "anthropic/claude-haiku-4-5",
        db: Any | None = None,
    ):
        """Initialize the summarizer.

        Args:
            artifacts_dir: Directory containing workflow artifacts.
            llm_query_fn: Async function for LLM queries.
                          Signature: async (prompt: str, model: str) -> str
                          If None, uses heuristic fallback only.
            model: Model to use for summarization (default: Haiku).
            db: Optional PixlDB instance for SQLite-backed summary cache.
                When provided, summaries are cached in artifact_summaries table.
        """
        self.artifacts_dir = artifacts_dir
        self.llm_query_fn = llm_query_fn
        self.model = model
        self._db = db
        self._cache: dict[str, str] = {}  # In-memory cache for current session

    async def get_or_create_summary(
        self,
        artifact_path: Path,
        artifact_hash: str | None = None,
    ) -> str:
        """Return cached summary if hash matches, else generate and cache.

        Checks SQLite cache first (if DB available), then disk cache,
        then generates via LLM (or heuristic fallback).

        Args:
            artifact_path: Path to the artifact file.
            artifact_hash: SHA256 hash of the artifact. Computed if not provided.

        Returns:
            Summary text (10-30 lines).
        """
        if not artifact_path.exists():
            return f"(artifact not found: {artifact_path.name})"

        if artifact_hash is None:
            artifact_hash = self._compute_hash(artifact_path)

        # Check in-memory cache
        cache_key = f"{artifact_path.name}:{artifact_hash}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Check SQLite cache
        db_summary = self._load_sqlite_summary(artifact_path.name, artifact_hash)
        if db_summary is not None:
            self._cache[cache_key] = db_summary
            return db_summary

        # Generate new summary
        content = artifact_path.read_text(encoding="utf-8")
        summary = await self._generate_summary(artifact_path.name, content)
        method = "llm" if self.llm_query_fn is not None else "heuristic"

        # Cache to SQLite and memory
        self._save_sqlite_summary(artifact_path.name, artifact_hash, summary, method=method)
        self._cache[cache_key] = summary

        return summary

    def get_summary_sync(
        self,
        artifact_path: Path,
        artifact_hash: str | None = None,
    ) -> str:
        """Synchronous version using heuristic fallback only.

        Checks SQLite cache first (if DB available), then disk cache,
        then generates heuristic summary.

        Args:
            artifact_path: Path to the artifact file.
            artifact_hash: SHA256 hash. Computed if not provided.

        Returns:
            Heuristic summary text.
        """
        if not artifact_path.exists():
            return f"(artifact not found: {artifact_path.name})"

        if artifact_hash is None:
            artifact_hash = self._compute_hash(artifact_path)

        # Check in-memory cache
        cache_key = f"{artifact_path.name}:{artifact_hash}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Check SQLite cache
        db_summary = self._load_sqlite_summary(artifact_path.name, artifact_hash)
        if db_summary is not None:
            self._cache[cache_key] = db_summary
            return db_summary

        # Generate heuristic summary
        content = artifact_path.read_text(encoding="utf-8")
        summary = self._heuristic_summary(artifact_path.name, content)

        self._save_sqlite_summary(artifact_path.name, artifact_hash, summary, method="heuristic")
        self._cache[cache_key] = summary
        return summary

    async def _generate_summary(self, name: str, content: str) -> str:
        """Generate summary using LLM or heuristic fallback.

        Args:
            name: Artifact filename.
            content: Full artifact content.

        Returns:
            Summary text.
        """
        if self.llm_query_fn is not None:
            try:
                prompt = self._build_summary_prompt(name, content)
                result = await self.llm_query_fn(prompt, self.model)
                if result and len(result.strip()) > 10:
                    return str(result.strip())
            except Exception as exc:
                logger.warning("LLM summary failed for %s: %s, using heuristic", name, exc)

        return self._heuristic_summary(name, content)

    @staticmethod
    def _build_summary_prompt(name: str, content: str) -> str:
        """Build the summarization prompt for the LLM.

        Args:
            name: Artifact filename.
            content: Full content (truncated if very large).

        Returns:
            Prompt string.
        """
        # Truncate very large content to avoid excessive tokens
        max_chars = 20_000
        if len(content) > max_chars:
            content = content[:max_chars] + "\n\n... (truncated)"

        return (
            f"Summarize this artifact in 10-30 lines. "
            f"Focus on: key decisions, requirements, file changes, and constraints. "
            f"Output ONLY the summary, no preamble.\n\n"
            f"# {name}\n\n{content}"
        )

    @staticmethod
    def _heuristic_summary(name: str, content: str) -> str:
        """Extract a heuristic summary without LLM.

        Uses section-first extraction: for each markdown section, extracts
        the heading plus the first sentence of content. This produces summaries
        that carry semantic meaning, not just structure.

        Args:
            name: Artifact filename.
            content: Full artifact content.

        Returns:
            Summary text (10-30 lines).
        """
        lines = content.splitlines()
        summary_lines: list[str] = [f"# Summary: {name}", ""]

        sections: list[tuple[str, str]] = []  # (heading, first_sentence)
        current_heading = ""
        current_body: list[str] = []

        for line in lines:
            if line.startswith("#"):
                if current_heading and current_body:
                    body_text = " ".join(current_body)
                    sentence_match = re.match(r"^(.+?[.!?])\s", body_text)
                    first_sentence = sentence_match.group(1) if sentence_match else body_text[:200]
                    sections.append((current_heading, first_sentence))
                current_heading = line
                current_body = []
            else:
                stripped = line.strip()
                if stripped and not stripped.startswith("```"):
                    # Strip bullet markers for cleaner sentences
                    cleaned = re.sub(r"^[-*]\s+", "", stripped)
                    current_body.append(cleaned)

        # Don't forget the last section
        if current_heading and current_body:
            body_text = " ".join(current_body)
            sentence_match = re.match(r"^(.+?[.!?])\s", body_text)
            first_sentence = sentence_match.group(1) if sentence_match else body_text[:200]
            sections.append((current_heading, first_sentence))

        if sections:
            summary_lines.append("## Key Content")
            for heading, sentence in sections[:15]:
                summary_lines.append(heading)
                summary_lines.append(f"  {sentence}")
            summary_lines.append("")
        else:
            # Fallback: extract first non-empty paragraph
            paragraph: list[str] = []
            in_paragraph = False
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if stripped and not in_paragraph:
                    in_paragraph = True
                    paragraph.append(stripped)
                elif in_paragraph and stripped:
                    paragraph.append(stripped)
                elif in_paragraph and not stripped:
                    break
            if paragraph:
                summary_lines.append("## Overview")
                summary_lines.extend(paragraph[:5])
                summary_lines.append("")

        # Count elements
        bullet_count = sum(1 for line in lines if re.match(r"^\s*[-*]\s", line))
        code_blocks = content.count("```")
        total_lines = len(lines)

        summary_lines.append("## Stats")
        summary_lines.append(f"- Lines: {total_lines}")
        summary_lines.append(f"- Bullets: {bullet_count}")
        summary_lines.append(f"- Code blocks: {code_blocks // 2}")

        # Cap at 30 lines
        return "\n".join(summary_lines[:30])

    def _load_sqlite_summary(self, artifact_name: str, source_hash: str) -> str | None:
        """Load summary from SQLite cache if available.

        Args:
            artifact_name: Artifact filename.
            source_hash: SHA256 hash of the source content.

        Returns:
            Summary text, or None if not cached or no DB.
        """
        if self._db is None:
            return None
        try:
            record = self._db.summaries.get_summary(artifact_name, source_hash)
            if record is not None:
                return str(record.summary_text)
        except Exception as exc:
            logger.debug("SQLite summary lookup failed for %s: %s", artifact_name, exc)
        return None

    def _save_sqlite_summary(
        self,
        artifact_name: str,
        source_hash: str,
        summary: str,
        *,
        method: str = "heuristic",
    ) -> None:
        """Save summary to SQLite cache if DB available.

        Args:
            artifact_name: Artifact filename.
            source_hash: SHA256 hash of the source content.
            summary: Summary text.
            method: Generation method ('heuristic' or 'llm').
        """
        if self._db is None:
            return
        try:
            from pixl.utils.tokens import estimate_tokens

            tokens = estimate_tokens(summary, "markdown")
            self._db.summaries.upsert_summary(
                artifact_name,
                source_hash,
                summary,
                summary_tokens=tokens,
                method=method,
            )
        except Exception as exc:
            logger.debug("SQLite summary save failed for %s: %s", artifact_name, exc)

    @staticmethod
    def _compute_hash(path: Path) -> str:
        """Compute SHA256 hash of a file.

        Args:
            path: File path.

        Returns:
            Hex digest string.
        """
        h = hashlib.sha256()
        h.update(path.read_bytes())
        return h.hexdigest()

    def invalidate(self, artifact_name: str) -> None:
        """Remove cached summary for an artifact.

        Args:
            artifact_name: Artifact filename.
        """
        to_remove = [k for k in self._cache if k.startswith(f"{artifact_name}:")]
        for k in to_remove:
            del self._cache[k]


__all__ = ["ArtifactSummarizer"]

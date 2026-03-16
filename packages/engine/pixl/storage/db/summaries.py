"""Artifact summary cache with SQLite persistence.

Stores and retrieves artifact summaries keyed by (artifact_name, source_hash).
Replaces the file-based .summaries/ cache with a transactional, queryable store.

THREAD SAFETY: Receives PixlDB and gets thread-local connections
for each operation, making it safe for concurrent use.
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from typing import Any

from pixl.storage.db.base import BaseStore


@dataclass(frozen=True)
class SummaryRecord:
    """Immutable record of a cached artifact summary."""

    id: str
    artifact_name: str
    source_hash: str
    summary_text: str
    summary_tokens: int
    method: str  # 'heuristic' | 'llm'
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "artifact_name": self.artifact_name,
            "source_hash": self.source_hash,
            "summary_text": self.summary_text,
            "summary_tokens": self.summary_tokens,
            "method": self.method,
            "created_at": self.created_at,
        }


class SummaryDB(BaseStore):
    """Artifact summary cache backed by SQLite.

    Provides fast lookup by (artifact_name, source_hash) and
    upsert semantics for caching summaries from heuristic or LLM.

    Receives a PixlDB instance and obtains thread-local connections
    for each operation, making it safe for multi-threaded use.
    """

    def get_summary(self, artifact_name: str, source_hash: str) -> SummaryRecord | None:
        """Retrieve a cached summary by artifact name and source hash.

        Args:
            artifact_name: Artifact filename (e.g., 'plan.md').
            source_hash: SHA256 hash of the source artifact content.

        Returns:
            SummaryRecord if found, None otherwise.
        """
        row = self._conn.execute(
            """SELECT id, artifact_name, source_hash, summary_text,
                      summary_tokens, method, created_at
               FROM artifact_summaries
               WHERE artifact_name = ? AND source_hash = ?""",
            (artifact_name, source_hash),
        ).fetchone()

        if row is None:
            return None

        return SummaryRecord(
            id=row["id"],
            artifact_name=row["artifact_name"],
            source_hash=row["source_hash"],
            summary_text=row["summary_text"],
            summary_tokens=row["summary_tokens"],
            method=row["method"],
            created_at=row["created_at"],
        )

    def upsert_summary(
        self,
        artifact_name: str,
        source_hash: str,
        summary_text: str,
        *,
        summary_tokens: int = 0,
        method: str = "heuristic",
    ) -> str:
        """Insert or update a summary in the cache.

        Uses SQLite's ON CONFLICT (UNIQUE constraint on artifact_name, source_hash)
        for upsert semantics.

        Args:
            artifact_name: Artifact filename.
            source_hash: SHA256 hash of the source content.
            summary_text: The summary text.
            summary_tokens: Estimated token count of the summary.
            method: Generation method ('heuristic' or 'llm').

        Returns:
            The summary record ID.
        """
        record_id = f"sum-{uuid.uuid4().hex[:12]}"

        self._conn.execute(
            """INSERT INTO artifact_summaries
                   (id, artifact_name, source_hash, summary_text, summary_tokens, method)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(artifact_name, source_hash) DO UPDATE SET
                   summary_text = excluded.summary_text,
                   summary_tokens = excluded.summary_tokens,
                   method = excluded.method,
                   created_at = datetime('now')""",
            (record_id, artifact_name, source_hash, summary_text, summary_tokens, method),
        )
        self._conn.commit()
        return record_id

    def get_all_for_artifact(self, artifact_name: str) -> list[SummaryRecord]:
        """Get all cached summaries for an artifact (any hash version).

        Args:
            artifact_name: Artifact filename.

        Returns:
            List of SummaryRecord instances.
        """
        rows = self._conn.execute(
            """SELECT id, artifact_name, source_hash, summary_text,
                      summary_tokens, method, created_at
               FROM artifact_summaries
               WHERE artifact_name = ?
               ORDER BY created_at DESC""",
            (artifact_name,),
        ).fetchall()

        return [
            SummaryRecord(
                id=row["id"],
                artifact_name=row["artifact_name"],
                source_hash=row["source_hash"],
                summary_text=row["summary_text"],
                summary_tokens=row["summary_tokens"],
                method=row["method"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def delete_for_artifact(self, artifact_name: str) -> int:
        """Delete all cached summaries for an artifact.

        Args:
            artifact_name: Artifact filename.

        Returns:
            Number of rows deleted.
        """
        cursor = self._conn.execute(
            "DELETE FROM artifact_summaries WHERE artifact_name = ?",
            (artifact_name,),
        )
        self._conn.commit()
        return cursor.rowcount

    def count(self) -> int:
        """Return total number of cached summaries."""
        row = self._conn.execute("SELECT COUNT(*) as cnt FROM artifact_summaries").fetchone()
        return row["cnt"] if row else 0


__all__ = ["SummaryDB", "SummaryRecord"]

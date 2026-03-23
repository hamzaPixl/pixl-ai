"""Incident tracking database with FTS5 similarity search.

Stores recovery incident records for historical analysis and similarity-based
recovery decision biasing. Uses FTS5 for efficient error message matching.

Each incident represents a terminal recovery state:
- succeeded: Recovery action resolved the error
- failed: Recovery exhausted attempts without success
- escalated: Recovery required human intervention

THREAD SAFETY: Receives PixlDB and gets thread-local connections
for each operation, making it safe for concurrent use.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pixl.storage.db.base import BaseStore
from pixl.storage.db.fts import prepare_fts_query


@dataclass(frozen=True)
class IncidentRecord:
    """Immutable record of a recovery incident."""

    id: str
    session_id: str
    node_id: str | None
    feature_id: str | None
    error_type: str
    error_message: str
    recovery_action: str | None
    outcome: str  # 'succeeded', 'failed', 'escalated'
    attempt_count: int
    payload_json: str
    created_at: str
    resolved_at: str | None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "node_id": self.node_id,
            "feature_id": self.feature_id,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "recovery_action": self.recovery_action,
            "outcome": self.outcome,
            "attempt_count": self.attempt_count,
            "payload": json.loads(self.payload_json) if self.payload_json else None,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
        }


class IncidentDB(BaseStore):
    """Incident tracking database with FTS5 search.

    Provides CRUD operations for incident records and FTS5-based
    similarity search on error messages and metadata.

    Receives a PixlDB instance and obtains thread-local connections
    for each operation, making it safe for multi-threaded use.
    """

    # CRUD operations

    def record_incident(
        self,
        *,
        incident_id: str,
        session_id: str,
        node_id: str | None,
        feature_id: str | None,
        error_type: str,
        error_message: str,
        recovery_action: str | None,
        outcome: str,
        attempt_count: int,
        payload_json: str,
        created_at: str | None = None,
        resolved_at: str | None = None,
    ) -> IncidentRecord:
        """Record a new incident.

        Args:
            incident_id: Unique incident ID
            session_id: Workflow session ID
            node_id: Node that encountered the error
            feature_id: Associated feature ID
            error_type: Type of error (provider_error, contract_error, etc.)
            error_message: Error message
            recovery_action: Action taken (retry, fail_fast, etc.)
            outcome: Terminal outcome (succeeded, failed, escalated)
            attempt_count: Number of recovery attempts
            payload_json: Full event payload as JSON string
            created_at: Incident creation time (ISO string)
            resolved_at: Resolution time (ISO string)

        Returns:
            The created IncidentRecord
        """
        if created_at is None:
            created_at = datetime.now().isoformat()

        self._conn.execute(
            """INSERT INTO incidents
               (id, session_id, node_id, feature_id, error_type, error_message,
                recovery_action, outcome, attempt_count, payload_json, created_at, resolved_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                incident_id,
                session_id,
                node_id,
                feature_id,
                error_type,
                error_message,
                recovery_action,
                outcome,
                attempt_count,
                payload_json,
                created_at,
                resolved_at,
            ),
        )
        self._conn.commit()

        return IncidentRecord(
            id=incident_id,
            session_id=session_id,
            node_id=node_id,
            feature_id=feature_id,
            error_type=error_type,
            error_message=error_message,
            recovery_action=recovery_action,
            outcome=outcome,
            attempt_count=attempt_count,
            payload_json=payload_json,
            created_at=created_at,
            resolved_at=resolved_at,
        )

    def get(self, incident_id: str) -> IncidentRecord | None:
        """Get an incident by ID."""
        row = self._conn.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
        if not row:
            return None
        return _row_to_incident(row)

    def get_by_session(self, session_id: str) -> list[IncidentRecord]:
        """Get all incidents for a session."""
        rows = self._conn.execute(
            "SELECT * FROM incidents WHERE session_id = ? ORDER BY created_at DESC",
            (session_id,),
        ).fetchall()
        return [_row_to_incident(r) for r in rows]

    def get_by_feature(self, feature_id: str) -> list[IncidentRecord]:
        """Get all incidents for a feature."""
        rows = self._conn.execute(
            "SELECT * FROM incidents WHERE feature_id = ? ORDER BY created_at DESC",
            (feature_id,),
        ).fetchall()
        return [_row_to_incident(r) for r in rows]

    def list_recent(self, limit: int = 50, offset: int = 0) -> list[IncidentRecord]:
        """List recent incidents."""
        rows = self._conn.execute(
            """SELECT * FROM incidents
               ORDER BY created_at DESC
               LIMIT ? OFFSET ?""",
            (limit, offset),
        ).fetchall()
        return [_row_to_incident(r) for r in rows]

    # FTS5 similarity search

    def find_similar_fts(
        self,
        error_type: str,
        error_message: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Find similar incidents using FTS5 BM25 ranking.

        Searches the error_message and error_type fields for similar
        historical incidents. Lower BM25 score = more similar.

        Args:
            error_type: Type of error to match
            error_message: Error message for similarity search
            limit: Maximum results to return

        Returns:
            List of dicts with incident data plus similarity score
        """
        if not error_message.strip():
            return []

        fts_query = prepare_fts_query(error_message)
        if not fts_query:
            return []

        # BM25 with error_type weighted higher (2.0) than message (1.0)
        results = self._conn.execute(
            """SELECT i.id, i.error_type, i.error_message, i.outcome,
                      i.recovery_action, i.created_at, i.attempt_count,
                      bm25(incidents_fts, 2.0, 1.0) as score
               FROM incidents_fts fts
               JOIN incidents i ON i.rowid = fts.rowid
               WHERE incidents_fts MATCH ?
               ORDER BY score
               LIMIT ?""",
            (fts_query, limit),
        ).fetchall()

        return [
            {
                "incident_id": r["id"],
                "error_type": r["error_type"],
                "error_message": r["error_message"],
                "outcome": r["outcome"],
                "recovery_action": r["recovery_action"],
                "created_at": r["created_at"],
                "attempt_count": r["attempt_count"],
                "similarity_score": abs(r["score"]),  # BM25 returns negative
            }
            for r in results
        ]

    def find_by_error_type(
        self,
        error_type: str,
        outcome: str | None = None,
        limit: int = 20,
    ) -> list[IncidentRecord]:
        """Find incidents by error type, optionally filtered by outcome."""
        if outcome:
            rows = self._conn.execute(
                """SELECT * FROM incidents
                   WHERE error_type = ? AND outcome = ?
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (error_type, outcome, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """SELECT * FROM incidents
                   WHERE error_type = ?
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (error_type, limit),
            ).fetchall()
        return [_row_to_incident(r) for r in rows]

    # Statistics

    def get_stats(self, days: int = 30, error_type: str | None = None) -> dict[str, Any]:
        """Get incident statistics for the time window.

        Args:
            days: Number of days to look back
            error_type: Filter to specific error type

        Returns:
            Dict with counts by outcome, success rate, etc.
        """
        where_clause = "WHERE created_at >= datetime('now', '-' || ? || ' days')"
        params: list[Any] = [days]

        if error_type:
            where_clause += " AND error_type = ?"
            params.append(error_type)

        # Total count
        total_row = self._conn.execute(
            f"SELECT COUNT(*) as cnt FROM incidents {where_clause}",
            params,
        ).fetchone()
        total = total_row["cnt"] if total_row else 0

        # Counts by outcome
        outcome_rows = self._conn.execute(
            f"""SELECT outcome, COUNT(*) as cnt
                FROM incidents {where_clause}
                GROUP BY outcome""",
            params,
        ).fetchall()
        by_outcome = {r["outcome"]: r["cnt"] for r in outcome_rows}

        # Success rate (succeeded / total)
        succeeded = by_outcome.get("succeeded", 0)
        escalated = by_outcome.get("escalated", 0)
        failed = by_outcome.get("failed", 0)
        success_rate = succeeded / total if total > 0 else 0.0

        # Top error types
        error_type_counts = self._conn.execute(
            f"""SELECT error_type, COUNT(*) as cnt
                FROM incidents {where_clause}
                GROUP BY error_type
                ORDER BY cnt DESC
                LIMIT 5""",
            params,
        ).fetchall()

        return {
            "total": total,
            "succeeded": succeeded,
            "failed": failed,
            "escalated": escalated,
            "success_rate": success_rate,
            "by_outcome": by_outcome,
            "top_error_types": [
                {"error_type": r["error_type"], "count": r["cnt"]} for r in error_type_counts
            ],
        }

    def get_success_rate(self, error_type: str, days: int = 30) -> float:
        """Calculate success rate for an error type.

        Returns:
            Float from 0.0 to 1.0 representing proportion of successful recoveries
        """
        stats = self.get_stats(days=days, error_type=error_type)
        return float(stats["success_rate"])


def _row_to_incident(row: sqlite3.Row) -> IncidentRecord:
    """Convert a database row to IncidentRecord."""
    return IncidentRecord(
        id=row["id"],
        session_id=row["session_id"],
        node_id=row["node_id"],
        feature_id=row["feature_id"],
        error_type=row["error_type"],
        error_message=row["error_message"],
        recovery_action=row["recovery_action"],
        outcome=row["outcome"],
        attempt_count=row["attempt_count"],
        payload_json=row["payload_json"],
        created_at=row["created_at"],
        resolved_at=row["resolved_at"],
    )

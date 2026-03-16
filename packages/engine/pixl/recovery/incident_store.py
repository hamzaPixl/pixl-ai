"""Incident store business logic for recovery history analysis.

Provides a higher-level interface over IncidentDB for querying and analyzing
incident history to bias recovery decisions.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from pixl.errors import PixlError
from pixl.models.event import Event, EventType
from pixl.storage.db.connection import PixlDB

@dataclass(frozen=True)
class IncidentSimilarity:
    """Result of similarity search with recovery context."""

    incident_id: str
    error_type: str
    error_message: str
    similarity_score: float  # FTS5 BM25 score (lower = more similar)
    outcome: str  # What happened last time: 'succeeded', 'failed', 'escalated'
    recovery_action: str | None
    created_at: str
    attempt_count: int

class IncidentStore:
    """Query incident history to bias recovery decisions.

    Wraps IncidentDB with business logic for:
    - Recording incidents from recovery events
    - Finding similar historical incidents
    - Calculating success rates for error types
    """

    def __init__(self, project_path: Path) -> None:
        """Initialize incident store.

        Args:
            project_path: Path to project (will resolve to .pixl directory)
        """
        self.project_path = project_path
        self._db: PixlDB | None = None

    @property
    def _db_instance(self) -> PixlDB:
        """Lazy-load database connection."""
        if self._db is None:
            from pixl.storage.db.db_registry import get_project_db

            self._db = get_project_db(self.project_path)
        return self._db

    def find_similar(
        self,
        error: PixlError,
        limit: int = 5,
    ) -> list[IncidentSimilarity]:
        """Find similar historical incidents using FTS5.

        Args:
            error: The current error to find matches for
            limit: Maximum number of similar incidents to return

        Returns:
            List of IncidentSimilarity with historical context
        """
        db = self._db_instance
        incident_db = db.incidents

        results = incident_db.find_similar_fts(
            error_type=error.error_type,
            error_message=error.message,
            limit=limit,
        )

        return [
            IncidentSimilarity(
                incident_id=r["incident_id"],
                error_type=r["error_type"],
                error_message=r["error_message"],
                similarity_score=r["similarity_score"],
                outcome=r["outcome"],
                recovery_action=r["recovery_action"],
                created_at=r["created_at"],
                attempt_count=r["attempt_count"],
            )
            for r in results
        ]

    def record_from_event(self, event: Event) -> str:
        """Record an incident from a recovery event.

        Creates an incident record from a terminal recovery event:
        - RECOVERY_SUCCEEDED -> outcome='succeeded'
        - RECOVERY_FAILED -> outcome='failed'
        - RECOVERY_ESCALATED -> outcome='escalated'

        Args:
            event: The recovery event to record

        Returns:
            The incident ID that was created
        """
        if event.type not in (
            EventType.RECOVERY_SUCCEEDED,
            EventType.RECOVERY_FAILED,
            EventType.RECOVERY_ESCALATED,
        ):
            raise ValueError(f"Event type {event.type} is not a terminal recovery event")

        outcome_map = {
            EventType.RECOVERY_SUCCEEDED: "succeeded",
            EventType.RECOVERY_FAILED: "failed",
            EventType.RECOVERY_ESCALATED: "escalated",
        }
        outcome = outcome_map[event.type]

        data = event.data or {}
        error_type = data.get("error_type", "unknown")
        error_message = data.get("error_message", data.get("message", ""))
        recovery_action = data.get("recovery_action")
        attempt = data.get("attempt", 0)

        # Generate incident ID
        incident_id = f"inc-{uuid.uuid4().hex[:12]}"

        payload_json = json.dumps(data)

        node_id = event.node_id
        feature_id = data.get("feature_id")

        # Record timestamp
        resolved_at = datetime.now().isoformat()
        created_at = data.get("created_at", resolved_at)

        db = self._db_instance
        incident_db = db.incidents

        incident_db.record_incident(
            incident_id=incident_id,
            session_id=event.session_id,
            node_id=node_id,
            feature_id=feature_id,
            error_type=error_type,
            error_message=error_message,
            recovery_action=recovery_action,
            outcome=outcome,
            attempt_count=attempt,
            payload_json=payload_json,
            created_at=created_at,
            resolved_at=resolved_at,
        )

        return incident_id

    def get_success_rate(self, error_type: str, days: int = 30) -> float:
        """Calculate success rate for an error type.

        Args:
            error_type: Type of error to analyze
            days: Lookback period in days

        Returns:
            Float from 0.0 to 1.0 representing success rate
        """
        db = self._db_instance
        incident_db = db.incidents
        return incident_db.get_success_rate(error_type, days)

    def get_recent_incidents(
        self,
        limit: int = 20,
        error_type: str | None = None,
        outcome: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get recent incidents, optionally filtered.

        Args:
            limit: Maximum results
            error_type: Filter by error type
            outcome: Filter by outcome

        Returns:
            List of incident dicts
        """
        db = self._db_instance
        incident_db = db.incidents

        if error_type:
            records = incident_db.find_by_error_type(error_type, outcome, limit)
        else:
            records = incident_db.list_recent(limit)

        return [r.to_dict() for r in records]

    def get_stats(self, days: int = 30) -> dict[str, Any]:
        """Get incident statistics.

        Args:
            days: Lookback period in days

        Returns:
            Dict with counts, success rates, top error types
        """
        db = self._db_instance
        incident_db = db.incidents
        return incident_db.get_stats(days)

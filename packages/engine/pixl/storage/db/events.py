"""Event store for audit trails and state transition history.

Provides two complementary systems:
1. State transitions — explicit status change records for entities
2. Events — general-purpose event log for workflow execution, user actions, etc.

Together they enable:
- Full audit trail (who changed what, when, why)
- Time-travel queries ("what was the state at time T?")
- Progress analytics (how long in each status?)
- Debugging (what happened before this failure?)

THREAD SAFETY: Receives PixlDB and gets thread-local connections
for each operation, making it safe for concurrent use.
"""

import contextlib
import json
import sqlite3
from collections.abc import Callable, Generator
from datetime import datetime
from typing import Any

from pixl.storage.db.base import BaseStore


class EventDB(BaseStore):
    """Event and state transition store.

    Replaces per-session events.jsonl files with a unified,
    indexed event store across all sessions and entities.

    Receives a PixlDB instance and obtains thread-local connections
    for each operation, making it safe for multi-threaded use.

    An optional ``on_commit`` callback is invoked after each write
    to wake SSE streams (or any other listener). This replaces the
    previous hard-coded import of ``pixl.api.sse``, eliminating the
    reverse engine→API coupling.
    """

    def __init__(
        self,
        db: "PixlDB",  # type: ignore[name-defined]  # noqa: F821
        *,
        on_commit: "Callable[[], None] | None" = None,
        event_bus: Any | None = None,
    ) -> None:
        super().__init__(db)
        self._on_commit = on_commit
        self._event_bus = event_bus
        self._batching: bool = False

        self._event_batch_buffer: list[
            tuple[str, str | None, str | None, str | None, str | None, str | None, str | None]
        ] = []
        self._transition_batch_buffer: list[
            tuple[str, str, str | None, str, str | None, str | None, str | None]
        ] = []

    def _notify(self) -> None:
        """Invoke the on_commit callback (best-effort, never raises)."""
        if self._on_commit is not None:
            try:
                self._on_commit()
            except Exception:
                pass

    # Batching

    @contextlib.contextmanager
    def batch(self) -> Generator[None, None, None]:
        """Context manager for batched event/transition writes.

        Collects all ``emit()`` and ``record_transition()`` calls made inside the
        block and commits them in a single transaction on exit.  Existing callers
        that do not use the context manager are completely unaffected (each call
        still does its own INSERT + COMMIT).

        Usage::

            with db.events.batch():
                db.events.emit("node_started", session_id=sid)
                db.events.emit("artifact_created", session_id=sid)
                db.events.record_transition("feature", fid, None, "planned")
            # all three rows committed in one transaction here

        Returns -1 as row ID for calls made inside the batch since actual IDs
        are not available until commit.
        """
        self._batching = True
        try:
            yield
            self.flush_batch()
        except BaseException:
            # Discard buffered rows on failure — the caller's exception propagates
            self._event_batch_buffer.clear()
            self._transition_batch_buffer.clear()
            raise
        finally:
            self._batching = False

    def flush_batch(self) -> None:
        """Flush buffered events and transitions to the database.

        Commits all buffered rows in a single transaction.  Safe to call even
        when there is nothing buffered (no-op).  Can also be called mid-batch to
        do an intermediate flush while keeping batching mode active.
        """
        if not self._event_batch_buffer and not self._transition_batch_buffer:
            return

        # Snapshot buffered events for bus publication after commit
        pending_events = list(self._event_batch_buffer)

        with self._db.write() as conn:
            if self._event_batch_buffer:
                conn.executemany(
                    """INSERT INTO events
                       (event_type, session_id, node_id, entity_type, entity_id, payload_json, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))""",
                    self._event_batch_buffer,
                )
                self._event_batch_buffer.clear()

            if self._transition_batch_buffer:
                conn.executemany(
                    """INSERT INTO state_transitions
                       (entity_type, entity_id, from_status, to_status,
                        trigger, trigger_id, metadata)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    self._transition_batch_buffer,
                )
                self._transition_batch_buffer.clear()

            conn.commit()
        self._notify()

        # Publish batched events to EventBus after successful commit
        for row in pending_events:
            event_type, session_id, node_id, entity_type, entity_id, payload_json, _ = row
            payload = json.loads(payload_json) if payload_json else None
            self._publish_to_bus(event_type, session_id, node_id, entity_type, entity_id, payload)

    # State transitions

    def record_transition(
        self,
        entity_type: str,
        entity_id: str,
        from_status: str | None,
        to_status: str,
        trigger: str | None = None,
        trigger_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Record a state transition.

        Args:
            entity_type: roadmap, epic, feature, session
            entity_id: Entity ID
            from_status: Previous status (None for creation)
            to_status: New status
            trigger: What caused the transition (workflow, user, system, auto_propagation)
            trigger_id: Session ID or other reference
            metadata: Additional context

        Returns:
            Transition row ID (``-1`` when batching is active since the
            actual ID is not available until the batch is committed).
        """
        metadata_json = json.dumps(metadata) if metadata else None

        if self._batching:
            self._transition_batch_buffer.append(
                (entity_type, entity_id, from_status, to_status, trigger, trigger_id, metadata_json)
            )
            return -1

        with self._db.write() as conn:
            cursor = conn.execute(
                """INSERT INTO state_transitions
                   (entity_type, entity_id, from_status, to_status,
                    trigger, trigger_id, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    entity_type,
                    entity_id,
                    from_status,
                    to_status,
                    trigger,
                    trigger_id,
                    metadata_json,
                ),
            )
            conn.commit()
        self._notify()
        return cursor.lastrowid  # type: ignore

    def get_history(
        self,
        entity_type: str,
        entity_id: str,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get state transition history for an entity.

        Returns transitions in chronological order.
        """
        query = """SELECT * FROM state_transitions
                   WHERE entity_type = ? AND entity_id = ?
                   ORDER BY created_at"""
        params: list[Any] = [entity_type, entity_id]

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        rows = self._conn.execute(query, params).fetchall()
        return [self._transition_to_dict(r) for r in rows]

    def get_entity_history(self, entity_id: str) -> list[dict[str, Any]]:
        """Get all transitions for an entity regardless of type."""
        rows = self._conn.execute(
            """SELECT * FROM state_transitions
               WHERE entity_id = ?
               ORDER BY created_at""",
            (entity_id,),
        ).fetchall()
        return [self._transition_to_dict(r) for r in rows]

    def get_transitions_since(
        self,
        since: str,
        entity_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get all transitions since a timestamp.

        Args:
            since: ISO datetime string
            entity_type: Optional filter

        Returns:
            Transitions in chronological order.
        """
        if entity_type:
            rows = self._conn.execute(
                """SELECT * FROM state_transitions
                   WHERE created_at >= ? AND entity_type = ?
                   ORDER BY created_at, id""",
                (since, entity_type),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """SELECT * FROM state_transitions
                   WHERE created_at >= ?
                   ORDER BY created_at, id""",
                (since,),
            ).fetchall()
        return [self._transition_to_dict(r) for r in rows]

    def get_status_at(
        self,
        entity_type: str,
        entity_id: str,
        at_time: str,
    ) -> str | None:
        """Get the status of an entity at a specific point in time.

        Enables time-travel queries.

        Args:
            entity_type: roadmap, epic, feature, session
            entity_id: Entity ID
            at_time: ISO datetime string

        Returns:
            Status at that time, or None if entity didn't exist yet.
        """
        row = self._conn.execute(
            """SELECT to_status FROM state_transitions
               WHERE entity_type = ? AND entity_id = ? AND created_at <= ?
               ORDER BY created_at DESC
               LIMIT 1""",
            (entity_type, entity_id, at_time),
        ).fetchone()
        return row["to_status"] if row else None

    def get_duration_in_status(
        self,
        entity_type: str,
        entity_id: str,
        status: str,
    ) -> float:
        """Calculate total time (seconds) an entity spent in a status.

        Useful for analytics: "how long was this feature in_progress?"
        """
        transitions = self.get_history(entity_type, entity_id)
        total_seconds = 0.0
        entered_at = None

        for t in transitions:
            if t["to_status"] == status and entered_at is None:
                entered_at = datetime.fromisoformat(t["created_at"])
            elif t["from_status"] == status and entered_at is not None:
                left_at = datetime.fromisoformat(t["created_at"])
                total_seconds += (left_at - entered_at).total_seconds()
                entered_at = None

        # If still in the status
        if entered_at is not None:
            total_seconds += (datetime.now() - entered_at).total_seconds()

        return total_seconds

    # General events

    def emit(
        self,
        event_type: str,
        session_id: str | None = None,
        node_id: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        payload: dict[str, Any] | None = None,
        created_at: str | None = None,
    ) -> int:
        """Emit a general event.

        Event types include:
        - node_started, node_completed, node_failed, node_skipped
        - gate_waiting, gate_approved, gate_rejected, gate_timeout
        - artifact_created, artifact_updated
        - session_started, session_completed, session_failed
        - loop_iteration
        - user_action (manual operations)

        Args:
            created_at: Optional ISO timestamp. If provided, overrides the
                DB DEFAULT (which uses UTC). Pass this to keep timestamps
                consistent with in-memory Event objects that use local time.

        Returns:
            Event row ID (``-1`` when batching is active since the actual
            ID is not available until the batch is committed).
        """
        payload_json = json.dumps(payload) if payload else None

        if self._batching:
            self._event_batch_buffer.append(
                (event_type, session_id, node_id, entity_type, entity_id, payload_json, created_at)
            )
            return -1

        with self._db.write() as conn:
            if created_at:
                cursor = conn.execute(
                    """INSERT INTO events
                       (event_type, session_id, node_id, entity_type, entity_id, payload_json, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        event_type,
                        session_id,
                        node_id,
                        entity_type,
                        entity_id,
                        payload_json,
                        created_at,
                    ),
                )
            else:
                cursor = conn.execute(
                    """INSERT INTO events
                       (event_type, session_id, node_id, entity_type, entity_id, payload_json)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (event_type, session_id, node_id, entity_type, entity_id, payload_json),
                )
            conn.commit()
        self._notify()
        self._publish_to_bus(event_type, session_id, node_id, entity_type, entity_id, payload)
        return cursor.lastrowid  # type: ignore

    def _publish_to_bus(
        self,
        event_type: str,
        session_id: str | None,
        node_id: str | None,
        entity_type: str | None,
        entity_id: str | None,
        payload: dict[str, Any] | None,
    ) -> None:
        """Publish event to the bus if attached (best-effort)."""
        if self._event_bus is None:
            return
        try:
            from types import SimpleNamespace

            event = SimpleNamespace(
                type=event_type,  # Match Event model field name
                event_type=event_type,  # Keep for bus filtering
                data=payload,  # Match Event model field name
                session_id=session_id,
                node_id=node_id,
                entity_type=entity_type,
                entity_id=entity_id,
            )
            self._event_bus.publish(event)
        except Exception:
            pass

    def get_events(
        self,
        session_id: str | None = None,
        event_type: str | None = None,
        entity_id: str | None = None,
        since: str | None = None,
        since_id: int | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Query events with optional filters.

        Args:
            since_id: Return events with id > since_id (preferred for SSE cursoring).
            since: Return events with created_at >= since (timestamp string).
        """
        conditions = []
        params: list[Any] = []

        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
        if entity_id:
            conditions.append("entity_id = ?")
            params.append(entity_id)
        if since_id is not None:
            conditions.append("id > ?")
            params.append(since_id)
        elif since:
            conditions.append("created_at >= ?")
            params.append(since)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"SELECT * FROM events {where} ORDER BY id"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        rows = self._conn.execute(query, params).fetchall()
        return [self._event_to_dict(r) for r in rows]

    def get_session_events(self, session_id: str) -> list[dict[str, Any]]:
        """Get all events for a workflow session, chronologically."""
        return self.get_events(session_id=session_id)

    def get_recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get the most recent events across all sessions."""
        rows = self._conn.execute(
            "SELECT * FROM events ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self._event_to_dict(r) for r in reversed(list(rows))]

    # Analytics

    def get_event_counts(
        self,
        session_id: str | None = None,
        since: str | None = None,
    ) -> dict[str, int]:
        """Get event counts by type."""
        # _build_where handles equality; since uses >=, so we build manually for it
        conditions: list[str] = []
        params: list[Any] = []
        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)
        if since:
            conditions.append("created_at >= ?")
            params.append(since)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = self._conn.execute(
            f"SELECT event_type, COUNT(*) as cnt FROM events {where} GROUP BY event_type",
            params,
        ).fetchall()
        return {r["event_type"]: r["cnt"] for r in rows}

    def get_transition_summary(
        self,
        entity_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get a summary of transitions grouped by from->to status.

        Useful for flow analysis: "how many features went from planned to in_progress?"
        """
        condition = "WHERE entity_type = ?" if entity_type else ""
        params = [entity_type] if entity_type else []

        rows = self._conn.execute(
            f"""SELECT entity_type, from_status, to_status, COUNT(*) as count,
                       MIN(created_at) as first_at, MAX(created_at) as last_at
                FROM state_transitions
                {condition}
                GROUP BY entity_type, from_status, to_status
                ORDER BY count DESC""",
            params,
        ).fetchall()
        return [dict(r) for r in rows]

    # Internal helpers

    def _transition_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        """Convert transition row to dict."""
        d = dict(row)
        if d.get("metadata"):
            with contextlib.suppress(json.JSONDecodeError, TypeError):
                d["metadata"] = json.loads(d["metadata"])
        return d

    def _event_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        """Convert event row to dict."""
        d = dict(row)
        self._deserialize_json(d, {"payload_json": "payload"})
        return d

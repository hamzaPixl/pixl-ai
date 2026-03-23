"""Tests for EventBus → EventDB integration.

Verifies that EventDB.emit() publishes to EventBus when configured,
batch mode triggers subscribers after commit, and subscriber errors
don't crash EventDB.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pixl.events.bus import EventBus
from pixl.storage.db.connection import PixlDB


@pytest.fixture()
def db(tmp_path: Path):
    pixl_dir = tmp_path / ".pixl"
    pixl_dir.mkdir()
    database = PixlDB(tmp_path, pixl_dir=pixl_dir)
    database.initialize()
    # Insert a parent session row for FK constraint
    conn = database.conn
    conn.execute(
        "INSERT INTO workflow_sessions (id, snapshot_hash) VALUES (?, ?)",
        ("sess-test", "abc123"),
    )
    conn.commit()
    return database


@pytest.fixture()
def bus():
    return EventBus()


@pytest.fixture()
def db_with_bus(db, bus):
    """PixlDB with an EventBus attached via the public API."""
    db.set_event_bus(bus)
    return db


class TestEventBusIntegration:
    def test_emit_publishes_to_bus(self, db_with_bus, bus):
        received = []
        bus.subscribe(lambda e: received.append(e))

        db_with_bus.events.emit("node_started", session_id="sess-test", node_id="n1")

        assert len(received) == 1
        assert received[0].event_type == "node_started"
        assert received[0].session_id == "sess-test"
        assert received[0].node_id == "n1"

    def test_emit_without_bus_works(self, db):
        """EventDB works normally when no bus is attached."""
        row_id = db.events.emit("node_started", session_id="sess-test")
        assert row_id > 0

    def test_bus_filter_by_event_type(self, db_with_bus, bus):
        started_events = []
        bus.subscribe(lambda e: started_events.append(e), event_type="node_started")

        db_with_bus.events.emit("node_started", session_id="sess-test", node_id="n1")
        db_with_bus.events.emit("node_completed", session_id="sess-test", node_id="n1")

        assert len(started_events) == 1
        assert started_events[0].event_type == "node_started"

    def test_batch_publishes_after_commit(self, db_with_bus, bus):
        received = []
        bus.subscribe(lambda e: received.append(e))

        with db_with_bus.events.batch():
            db_with_bus.events.emit("node_started", session_id="sess-test", node_id="n1")
            db_with_bus.events.emit("node_completed", session_id="sess-test", node_id="n1")

        # After batch commit, events should be published
        assert len(received) >= 2
        types = [e.event_type for e in received]
        assert "node_started" in types
        assert "node_completed" in types

    def test_subscriber_error_does_not_crash_emit(self, db_with_bus, bus):
        def bad_subscriber(event):
            raise RuntimeError("subscriber crash")

        bus.subscribe(bad_subscriber)

        # Should not raise — subscriber errors are caught
        row_id = db_with_bus.events.emit("node_started", session_id="sess-test", node_id="n1")
        assert row_id > 0

    def test_event_payload_forwarded_to_bus(self, db_with_bus, bus):
        received = []
        bus.subscribe(lambda e: received.append(e))

        db_with_bus.events.emit(
            "artifact_created",
            session_id="sess-test",
            node_id="n1",
            payload={"file_path": "/workspace/main.py", "size": 1024},
        )

        assert len(received) == 1
        assert received[0].data == {"file_path": "/workspace/main.py", "size": 1024}

    def test_multiple_subscribers_all_receive(self, db_with_bus, bus):
        received_a = []
        received_b = []
        bus.subscribe(lambda e: received_a.append(e))
        bus.subscribe(lambda e: received_b.append(e))

        db_with_bus.events.emit("node_started", session_id="sess-test")

        assert len(received_a) == 1
        assert len(received_b) == 1

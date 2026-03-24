"""Extended tests for SessionDB — covering previously uncovered branches.

Covers:
- list_sessions() with status filters: running, paused, completed, failed, stalled
- list_sessions() with offset pagination
- get_active_sessions()
- get_recent_sessions()
- list_stalled_running_sessions()
- force_unblock_for_resume()
- cleanup_orphaned_snapshots()
- update_session() with frozen_artifacts and structured_outputs
- get_nodes_by_state()
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from pixl.storage.db.connection import PixlDB
from pixl.storage.db.sessions import SessionDB

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db(tmp_path: Path) -> PixlDB:
    """Fresh PixlDB for each test."""
    pixl_dir = tmp_path / ".pixl"
    pixl_dir.mkdir()
    pixl_db = PixlDB(tmp_path, pixl_dir=pixl_dir)
    pixl_db.initialize()
    return pixl_db


@pytest.fixture()
def sessions(db: PixlDB) -> SessionDB:
    return db.sessions


def _seed_feature(db: PixlDB, feature_id: str) -> str:
    db.conn.execute(
        "INSERT OR IGNORE INTO features (id, title) VALUES (?, ?)",
        (feature_id, f"Test {feature_id}"),
    )
    db.conn.commit()
    return feature_id


# ---------------------------------------------------------------------------
# list_sessions — status filters
# ---------------------------------------------------------------------------


class TestListSessionsStatusFilters:
    def test_filter_completed_returns_only_ended_sessions(
        self, sessions: SessionDB
    ) -> None:
        # Arrange
        s1 = sessions.create_session(feature_id=None, snapshot_hash="c1")
        s2 = sessions.create_session(feature_id=None, snapshot_hash="c2")
        now = datetime.now().isoformat()
        sessions.update_session(s1["id"], status="completed", ended_at=now)

        # Act
        result = sessions.list_sessions(status="completed")

        # Assert
        ids = [s["id"] for s in result]
        assert s1["id"] in ids
        assert s2["id"] not in ids

    def test_filter_paused_returns_sessions_with_gate_waiting(
        self, sessions: SessionDB
    ) -> None:
        s1 = sessions.create_session(feature_id=None, snapshot_hash="p1")
        s2 = sessions.create_session(feature_id=None, snapshot_hash="p2")
        sessions.upsert_node_instance(s1["id"], "gate-node", "gate_waiting")

        result = sessions.list_sessions(status="paused")
        ids = [s["id"] for s in result]
        assert s1["id"] in ids
        assert s2["id"] not in ids

    def test_filter_paused_returns_sessions_with_task_blocked(
        self, sessions: SessionDB
    ) -> None:
        s1 = sessions.create_session(feature_id=None, snapshot_hash="pb1")
        sessions.upsert_node_instance(s1["id"], "blocked-node", "task_blocked")

        result = sessions.list_sessions(status="paused")
        ids = [s["id"] for s in result]
        assert s1["id"] in ids

    def test_filter_failed_returns_sessions_with_failed_nodes(
        self, sessions: SessionDB
    ) -> None:
        s1 = sessions.create_session(feature_id=None, snapshot_hash="f1")
        s2 = sessions.create_session(feature_id=None, snapshot_hash="f2")
        sessions.upsert_node_instance(s1["id"], "failed-node", "task_failed")

        result = sessions.list_sessions(status="failed")
        ids = [s["id"] for s in result]
        assert s1["id"] in ids
        assert s2["id"] not in ids

    def test_filter_running_returns_session_with_task_running(
        self, sessions: SessionDB
    ) -> None:
        s1 = sessions.create_session(feature_id=None, snapshot_hash="r1")
        sessions.upsert_node_instance(s1["id"], "running-node", "task_running")

        result = sessions.list_sessions(status="running")
        ids = [s["id"] for s in result]
        assert s1["id"] in ids

    def test_unknown_status_filter_returns_all_sessions(
        self, sessions: SessionDB
    ) -> None:
        sessions.create_session(feature_id=None, snapshot_hash="u1")
        sessions.create_session(feature_id=None, snapshot_hash="u2")
        # Unknown status — no condition appended, so all sessions returned
        result = sessions.list_sessions(status="totally_unknown_status")
        assert len(result) == 2


# ---------------------------------------------------------------------------
# list_sessions — offset pagination
# ---------------------------------------------------------------------------


class TestListSessionsOffset:
    def test_offset_skips_first_n_sessions(self, sessions: SessionDB) -> None:
        for i in range(5):
            sessions.create_session(feature_id=None, snapshot_hash=f"off{i}")

        # SQLite requires LIMIT when OFFSET is used — the production code appends
        # OFFSET only when offset is truthy, and the query builder requires limit to
        # be set too for valid SQL.  Test the combined case:
        all_result = sessions.list_sessions(limit=10)
        offset_result = sessions.list_sessions(limit=10, offset=2)
        assert len(offset_result) == 3
        assert offset_result[0]["id"] == all_result[2]["id"]

    def test_offset_and_limit_combined(self, sessions: SessionDB) -> None:
        for i in range(6):
            sessions.create_session(feature_id=None, snapshot_hash=f"ol{i}")

        result = sessions.list_sessions(limit=2, offset=2)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# get_active_sessions
# ---------------------------------------------------------------------------


class TestGetActiveSessions:
    def test_returns_sessions_without_ended_at(self, sessions: SessionDB) -> None:
        s1 = sessions.create_session(feature_id=None, snapshot_hash="a1")
        s2 = sessions.create_session(feature_id=None, snapshot_hash="a2")
        sessions.update_session(
            s2["id"], status="completed", ended_at=datetime.now().isoformat()
        )

        result = sessions.get_active_sessions()
        ids = [s["id"] for s in result]
        assert s1["id"] in ids
        assert s2["id"] not in ids

    def test_returns_empty_list_when_all_ended(self, sessions: SessionDB) -> None:
        s1 = sessions.create_session(feature_id=None, snapshot_hash="ae1")
        sessions.update_session(
            s1["id"], status="completed", ended_at=datetime.now().isoformat()
        )

        result = sessions.get_active_sessions()
        assert result == []


# ---------------------------------------------------------------------------
# get_recent_sessions
# ---------------------------------------------------------------------------


class TestGetRecentSessions:
    def test_returns_sessions_ordered_by_created_at_desc(
        self, sessions: SessionDB
    ) -> None:
        for i in range(5):
            sessions.create_session(feature_id=None, snapshot_hash=f"rec{i}")

        result = sessions.get_recent_sessions(limit=3)
        assert len(result) == 3

    def test_respects_limit(self, sessions: SessionDB) -> None:
        for i in range(10):
            sessions.create_session(feature_id=None, snapshot_hash=f"lim{i}")

        result = sessions.get_recent_sessions(limit=5)
        assert len(result) == 5

    def test_default_limit_is_15(self, sessions: SessionDB) -> None:
        for i in range(20):
            sessions.create_session(feature_id=None, snapshot_hash=f"def{i}")

        result = sessions.get_recent_sessions()
        assert len(result) == 15


# ---------------------------------------------------------------------------
# list_stalled_running_sessions
# ---------------------------------------------------------------------------


class TestListStalledRunningSessions:
    def test_returns_empty_when_no_sessions(self, sessions: SessionDB) -> None:
        result = sessions.list_stalled_running_sessions()
        assert result == []

    def test_stalled_session_detected_with_custom_threshold(
        self, sessions: SessionDB
    ) -> None:
        # Create a session with a running node
        s = sessions.create_session(feature_id=None, snapshot_hash="stall1")
        sessions.upsert_node_instance(s["id"], "running-node", "task_running")

        # Make it look stale by backdating last_updated_at
        old_ts = (datetime.now() - timedelta(seconds=200)).isoformat()
        sessions._conn.execute(
            "UPDATE workflow_sessions SET last_updated_at = ? WHERE id = ?",
            (old_ts, s["id"]),
        )
        sessions._conn.commit()

        result = sessions.list_stalled_running_sessions(stale_after_seconds=100)
        assert s["id"] in result

    def test_fresh_running_session_not_marked_stalled(
        self, sessions: SessionDB
    ) -> None:
        s = sessions.create_session(feature_id=None, snapshot_hash="fresh1")
        sessions.upsert_node_instance(s["id"], "running-node", "task_running")
        # last_updated_at is fresh (just created)

        result = sessions.list_stalled_running_sessions(stale_after_seconds=3600)
        assert s["id"] not in result


# ---------------------------------------------------------------------------
# force_unblock_for_resume
# ---------------------------------------------------------------------------


class TestForceUnblockForResume:
    def test_resets_gate_waiting_nodes(self, sessions: SessionDB) -> None:
        s = sessions.create_session(feature_id=None, snapshot_hash="fu1")
        sessions.upsert_node_instance(s["id"], "gate-node", "gate_waiting")

        unblocked = sessions.force_unblock_for_resume(s["id"])

        assert "gate-node" in unblocked
        node = sessions.get_node_instance(s["id"], "gate-node")
        assert node is not None
        assert node["state"] == "task_pending"

    def test_also_resets_blocked_and_failed_nodes(
        self, sessions: SessionDB
    ) -> None:
        s = sessions.create_session(feature_id=None, snapshot_hash="fu2")
        sessions.upsert_node_instance(s["id"], "blocked-node", "task_blocked")
        sessions.upsert_node_instance(s["id"], "failed-node", "task_failed")
        sessions.upsert_node_instance(s["id"], "gate-node", "gate_waiting")

        unblocked = sessions.force_unblock_for_resume(s["id"])

        assert "blocked-node" in unblocked
        assert "failed-node" in unblocked
        assert "gate-node" in unblocked

    def test_returns_empty_list_when_no_blocked_nodes(
        self, sessions: SessionDB
    ) -> None:
        s = sessions.create_session(feature_id=None, snapshot_hash="fu3")
        sessions.upsert_node_instance(s["id"], "done-node", "task_completed")

        unblocked = sessions.force_unblock_for_resume(s["id"])
        assert unblocked == []


# ---------------------------------------------------------------------------
# cleanup_orphaned_snapshots
# ---------------------------------------------------------------------------


class TestCleanupOrphanedSnapshots:
    def test_removes_snapshots_not_in_active_set(self, sessions: SessionDB) -> None:
        sessions.save_snapshot("hash-orphan", '{"x": 1}')
        sessions.save_snapshot("hash-active", '{"x": 2}')

        removed = sessions.cleanup_orphaned_snapshots(active_hashes={"hash-active"})

        assert removed == 1
        assert sessions.snapshot_exists("hash-active") is True
        assert sessions.snapshot_exists("hash-orphan") is False

    def test_no_snapshots_removed_when_all_active(self, sessions: SessionDB) -> None:
        sessions.save_snapshot("hash-1", '{"a": 1}')
        sessions.save_snapshot("hash-2", '{"b": 2}')

        removed = sessions.cleanup_orphaned_snapshots(
            active_hashes={"hash-1", "hash-2"}
        )
        assert removed == 0

    def test_returns_zero_when_no_snapshots_exist(self, sessions: SessionDB) -> None:
        removed = sessions.cleanup_orphaned_snapshots(active_hashes={"hash-x"})
        assert removed == 0


# ---------------------------------------------------------------------------
# update_session — frozen_artifacts and structured_outputs serialization
# ---------------------------------------------------------------------------


class TestUpdateSessionSerialization:
    def test_update_frozen_artifacts_serialized_as_json(
        self, sessions: SessionDB
    ) -> None:
        s = sessions.create_session(feature_id=None, snapshot_hash="ser1")
        frozen = {"plan.md": "abc123checksum", "spec.md": "def456checksum"}
        sessions.update_session(s["id"], frozen_artifacts=frozen)

        fetched = sessions.get_session(s["id"])
        assert fetched is not None
        assert fetched.get("frozen_artifacts") == frozen

    def test_update_structured_outputs_serialized_as_json(
        self, sessions: SessionDB
    ) -> None:
        s = sessions.create_session(feature_id=None, snapshot_hash="ser2")
        outputs = {"plan": {"payload": {"confidence": 0.9}}}
        sessions.update_session(s["id"], structured_outputs=outputs)

        fetched = sessions.get_session(s["id"])
        assert fetched is not None
        assert fetched.get("structured_outputs") == outputs

    def test_update_baton_field(self, sessions: SessionDB) -> None:
        s = sessions.create_session(feature_id=None, snapshot_hash="ser3")
        sessions.update_session(s["id"], status="running")
        fetched = sessions.get_session(s["id"])
        assert fetched is not None
        assert fetched["status"] == "running"


# ---------------------------------------------------------------------------
# get_nodes_by_state
# ---------------------------------------------------------------------------


class TestGetNodesByState:
    def test_returns_nodes_matching_state(self, sessions: SessionDB) -> None:
        s = sessions.create_session(feature_id=None, snapshot_hash="nbs1")
        sessions.upsert_node_instance(s["id"], "node-a", "task_completed")
        sessions.upsert_node_instance(s["id"], "node-b", "task_completed")
        sessions.upsert_node_instance(s["id"], "node-c", "task_running")

        result = sessions.get_nodes_by_state(s["id"], "task_completed")
        assert len(result) == 2
        assert all(n["state"] == "task_completed" for n in result)

    def test_returns_empty_list_when_no_nodes_in_state(
        self, sessions: SessionDB
    ) -> None:
        s = sessions.create_session(feature_id=None, snapshot_hash="nbs2")
        sessions.upsert_node_instance(s["id"], "node-a", "task_running")

        result = sessions.get_nodes_by_state(s["id"], "task_failed")
        assert result == []


# ---------------------------------------------------------------------------
# unblock_tasks_for_resume — running and failed nodes
# ---------------------------------------------------------------------------


class TestUnblockTasksForResumeExtended:
    def test_resets_running_nodes_to_pending(self, sessions: SessionDB) -> None:
        s = sessions.create_session(feature_id=None, snapshot_hash="ubr-ext1")
        sessions.upsert_node_instance(s["id"], "running-node", "task_running")

        unblocked = sessions.unblock_tasks_for_resume(s["id"])

        assert "running-node" in unblocked
        node = sessions.get_node_instance(s["id"], "running-node")
        assert node is not None
        assert node["state"] == "task_pending"

    def test_resets_failed_nodes_to_pending(self, sessions: SessionDB) -> None:
        s = sessions.create_session(feature_id=None, snapshot_hash="ubr-ext2")
        sessions.upsert_node_instance(s["id"], "failed-node", "task_failed")

        unblocked = sessions.unblock_tasks_for_resume(s["id"])

        assert "failed-node" in unblocked
        node = sessions.get_node_instance(s["id"], "failed-node")
        assert node is not None
        assert node["state"] == "task_pending"

    def test_resets_loop_states_on_resume(self, sessions: SessionDB) -> None:
        s = sessions.create_session(feature_id=None, snapshot_hash="ubr-ext3")
        sessions.upsert_node_instance(s["id"], "blocked-node", "task_blocked")
        sessions.upsert_loop_state(s["id"], "loop-1", current_iteration=3, max_iterations=5)

        sessions.unblock_tasks_for_resume(s["id"])

        loop = sessions.get_loop_state(s["id"], "loop-1")
        assert loop is not None
        assert loop["current_iteration"] == 0

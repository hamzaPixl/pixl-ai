"""Unit tests for SessionDB — the SQLite-backed workflow session store.

Uses a real PixlDB with a temp-directory database so every test is isolated
and fast.  No mocks for the database layer — we test against the real schema.

NOTE on feature_id: workflow_sessions.feature_id has a nullable FK to
features(id).  Passing a non-NULL string that does not exist in features
raises an IntegrityError.  Tests that don't specifically test feature-id
filtering pass feature_id=None.  Tests that need filtering pre-seed a row
in the features table via _seed_feature().
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
    """Fresh PixlDB for each test, fully initialized with the current schema."""
    pixl_dir = tmp_path / ".pixl"
    pixl_dir.mkdir()
    pixl_db = PixlDB(tmp_path, pixl_dir=pixl_dir)
    pixl_db.initialize()
    return pixl_db


@pytest.fixture()
def sessions(db: PixlDB) -> SessionDB:
    """Convenience accessor for the session store."""
    return db.sessions


def _seed_feature(db: PixlDB, feature_id: str) -> str:
    """Insert a minimal features row to satisfy the FK on workflow_sessions.

    workflow_sessions.feature_id REFERENCES features(id) ON DELETE SET NULL.
    This helper must be called before create_session() when a non-NULL
    feature_id is passed.
    """
    db.conn.execute(
        "INSERT OR IGNORE INTO features (id, title) VALUES (?, ?)",
        (feature_id, f"Test feature {feature_id}"),
    )
    db.conn.commit()
    return feature_id


# ---------------------------------------------------------------------------
# Session creation
# ---------------------------------------------------------------------------


class TestCreateSession:
    def test_returns_dict_with_expected_keys(self, sessions: SessionDB) -> None:
        # Arrange / Act
        result = sessions.create_session(
            feature_id=None,
            snapshot_hash="abc123",
        )

        # Assert
        assert isinstance(result, dict)
        assert result["snapshot_hash"] == "abc123"

    def test_generated_id_has_sess_prefix(self, sessions: SessionDB) -> None:
        result = sessions.create_session(feature_id=None, snapshot_hash="def456")
        assert result["id"].startswith("sess-")

    def test_each_session_gets_unique_id(self, sessions: SessionDB) -> None:
        first = sessions.create_session(feature_id=None, snapshot_hash="h1")
        second = sessions.create_session(feature_id=None, snapshot_hash="h2")
        assert first["id"] != second["id"]

    def test_optional_fields_stored_correctly(self, sessions: SessionDB) -> None:
        result = sessions.create_session(
            feature_id=None,
            snapshot_hash="ghi789",
            baseline_commit="abc0001",
            workspace_root="/workspace/proj",
        )
        assert result["baseline_commit"] == "abc0001"
        assert result["workspace_root"] == "/workspace/proj"

    def test_created_at_is_parseable_iso_string(self, sessions: SessionDB) -> None:
        result = sessions.create_session(feature_id=None, snapshot_hash="jkl")
        created_at = result["created_at"]
        # Should not raise
        parsed = datetime.fromisoformat(created_at)
        assert isinstance(parsed, datetime)

    def test_feature_id_stored_when_feature_exists(self, db: PixlDB) -> None:
        # Arrange — seed the feature row first
        _seed_feature(db, "feat-real")

        # Act
        result = db.sessions.create_session(feature_id="feat-real", snapshot_hash="xyz")

        # Assert
        assert result["feature_id"] == "feat-real"


# ---------------------------------------------------------------------------
# Session retrieval
# ---------------------------------------------------------------------------


class TestGetSession:
    def test_returns_none_for_missing_session(self, sessions: SessionDB) -> None:
        result = sessions.get_session("sess-doesnotexist")
        assert result is None

    def test_returns_session_after_creation(self, sessions: SessionDB) -> None:
        created = sessions.create_session(feature_id=None, snapshot_hash="mno")
        fetched = sessions.get_session(created["id"])
        assert fetched is not None
        assert fetched["id"] == created["id"]

    def test_frozen_artifacts_defaults_to_none_or_empty(self, sessions: SessionDB) -> None:
        created = sessions.create_session(feature_id=None, snapshot_hash="pqr")
        fetched = sessions.get_session(created["id"])
        assert fetched is not None
        # frozen_artifacts is not set on creation so it should be None or {}
        assert fetched.get("frozen_artifacts") in (None, {})

    def test_node_instances_defaults_to_empty_dict(self, sessions: SessionDB) -> None:
        created = sessions.create_session(feature_id=None, snapshot_hash="stu")
        fetched = sessions.get_session(created["id"])
        assert fetched is not None
        assert fetched["node_instances"] == {}

    def test_loop_state_defaults_to_empty_dict(self, sessions: SessionDB) -> None:
        created = sessions.create_session(feature_id=None, snapshot_hash="vwx")
        fetched = sessions.get_session(created["id"])
        assert fetched is not None
        assert fetched["loop_state"] == {}


# ---------------------------------------------------------------------------
# Session update
# ---------------------------------------------------------------------------


class TestUpdateSession:
    def test_update_returns_true_for_existing_session(self, sessions: SessionDB) -> None:
        created = sessions.create_session(feature_id=None, snapshot_hash="aaa")
        result = sessions.update_session(created["id"], status="running")
        assert result is True

    def test_update_returns_false_for_missing_session(self, sessions: SessionDB) -> None:
        result = sessions.update_session("sess-ghost", status="running")
        assert result is False

    def test_updated_status_persists(self, sessions: SessionDB) -> None:
        created = sessions.create_session(feature_id=None, snapshot_hash="bbb")
        sessions.update_session(
            created["id"], status="completed", ended_at=datetime.now().isoformat()
        )
        fetched = sessions.get_session(created["id"])
        assert fetched is not None
        assert fetched["status"] == "completed"

    def test_update_serializes_cursor_as_json(self, sessions: SessionDB) -> None:
        # Arrange
        created = sessions.create_session(feature_id=None, snapshot_hash="ccc")
        cursor_data = {"position": 3, "node": "build"}

        # Act
        sessions.update_session(created["id"], cursor=cursor_data)
        fetched = sessions.get_session(created["id"])

        # Assert — cursor should be deserialized back to the original dict
        assert fetched is not None
        assert fetched.get("cursor") == cursor_data

    def test_update_serializes_session_state_as_json(self, sessions: SessionDB) -> None:
        created = sessions.create_session(feature_id=None, snapshot_hash="ddd")
        state = {"phase": "review", "approved": True}
        sessions.update_session(created["id"], session_state=state)
        fetched = sessions.get_session(created["id"])
        assert fetched is not None
        assert fetched.get("session_state") == state


# ---------------------------------------------------------------------------
# Session deletion
# ---------------------------------------------------------------------------


class TestDeleteSession:
    def test_delete_returns_true_for_existing_session(self, sessions: SessionDB) -> None:
        created = sessions.create_session(feature_id=None, snapshot_hash="eee")
        result = sessions.delete_session(created["id"])
        assert result is True

    def test_delete_returns_false_for_missing_session(self, sessions: SessionDB) -> None:
        result = sessions.delete_session("sess-phantom")
        assert result is False

    def test_deleted_session_no_longer_retrievable(self, sessions: SessionDB) -> None:
        created = sessions.create_session(feature_id=None, snapshot_hash="fff")
        sessions.delete_session(created["id"])
        assert sessions.get_session(created["id"]) is None


# ---------------------------------------------------------------------------
# Session listing
# ---------------------------------------------------------------------------


class TestListSessions:
    def test_empty_store_returns_empty_list(self, sessions: SessionDB) -> None:
        result = sessions.list_sessions()
        assert result == []

    def test_returns_all_sessions_when_no_filter(self, sessions: SessionDB) -> None:
        sessions.create_session(feature_id=None, snapshot_hash="h1")
        sessions.create_session(feature_id=None, snapshot_hash="h2")
        result = sessions.list_sessions()
        assert len(result) == 2

    def test_filter_by_feature_id(self, db: PixlDB) -> None:
        # Arrange — seed two features then create one session for each
        _seed_feature(db, "feat-target")
        _seed_feature(db, "feat-other")
        db.sessions.create_session(feature_id="feat-target", snapshot_hash="t1")
        db.sessions.create_session(feature_id="feat-other", snapshot_hash="o1")

        # Act
        result = db.sessions.list_sessions(feature_id="feat-target")

        # Assert
        assert len(result) == 1
        assert result[0]["feature_id"] == "feat-target"

    def test_limit_restricts_result_count(self, sessions: SessionDB) -> None:
        for i in range(5):
            sessions.create_session(feature_id=None, snapshot_hash=f"h{i}")
        result = sessions.list_sessions(limit=3)
        assert len(result) == 3

    def test_ordered_by_created_at_desc(self, sessions: SessionDB) -> None:
        for i in range(3):
            sessions.create_session(feature_id=None, snapshot_hash=f"hord{i}")
        result = sessions.list_sessions()
        timestamps = [r["created_at"] for r in result]
        assert timestamps == sorted(timestamps, reverse=True)


# ---------------------------------------------------------------------------
# DateTime parsing helpers
# ---------------------------------------------------------------------------


class TestSessionAgeSeconds:
    def test_returns_none_when_value_is_none(self) -> None:
        result = SessionDB._session_age_seconds(None)
        assert result is None

    def test_returns_none_for_invalid_string(self) -> None:
        result = SessionDB._session_age_seconds("not-a-date")
        assert result is None

    def test_returns_non_negative_float_for_past_timestamp(self) -> None:
        past = (datetime.now() - timedelta(seconds=30)).isoformat()
        result = SessionDB._session_age_seconds(past)
        assert result is not None
        assert result >= 0.0

    def test_accepts_datetime_object(self) -> None:
        past_dt = datetime.now() - timedelta(seconds=10)
        result = SessionDB._session_age_seconds(past_dt)
        assert result is not None
        assert result >= 0.0


# ---------------------------------------------------------------------------
# Sum node durations helper
# ---------------------------------------------------------------------------


class TestSumNodeDurations:
    def test_returns_zero_for_empty_dict(self) -> None:
        result = SessionDB._sum_node_durations({})
        assert result == 0.0

    def test_sums_multiple_nodes(self) -> None:
        now = datetime.now()
        node_instances = {
            "node-a": {
                "started_at": (now - timedelta(seconds=10)).isoformat(),
                "ended_at": now.isoformat(),
            },
            "node-b": {
                "started_at": (now - timedelta(seconds=5)).isoformat(),
                "ended_at": now.isoformat(),
            },
        }
        result = SessionDB._sum_node_durations(node_instances)
        # Each node ran for at least the specified interval
        assert result >= 14.0  # generous lower bound for CI timing jitter

    def test_skips_nodes_without_ended_at(self) -> None:
        now = datetime.now()
        node_instances = {
            "node-running": {
                "started_at": (now - timedelta(seconds=20)).isoformat(),
                "ended_at": None,
            },
        }
        result = SessionDB._sum_node_durations(node_instances)
        assert result == 0.0

    def test_skips_nodes_without_started_at(self) -> None:
        now = datetime.now()
        node_instances = {
            "node-pending": {
                "started_at": None,
                "ended_at": now.isoformat(),
            },
        }
        result = SessionDB._sum_node_durations(node_instances)
        assert result == 0.0


# ---------------------------------------------------------------------------
# All nodes terminal helper
# ---------------------------------------------------------------------------


class TestAllNodesTerminal:
    def test_returns_false_for_empty_dict(self) -> None:
        assert SessionDB._all_nodes_terminal({}) is False

    def test_returns_true_when_all_nodes_are_terminal(self) -> None:
        nodes = {
            "n1": {"state": "task_completed"},
            "n2": {"state": "gate_approved"},
        }
        assert SessionDB._all_nodes_terminal(nodes) is True

    def test_returns_false_when_one_node_still_running(self) -> None:
        nodes = {
            "n1": {"state": "task_completed"},
            "n2": {"state": "task_running"},
        }
        assert SessionDB._all_nodes_terminal(nodes) is False

    def test_task_failed_is_terminal(self) -> None:
        nodes = {
            "n1": {"state": "task_failed"},
        }
        assert SessionDB._all_nodes_terminal(nodes) is True

    def test_task_skipped_is_terminal(self) -> None:
        nodes = {
            "n1": {"state": "task_skipped"},
        }
        assert SessionDB._all_nodes_terminal(nodes) is True


# ---------------------------------------------------------------------------
# Node instances
# ---------------------------------------------------------------------------


class TestUpsertNodeInstance:
    def test_creates_node_on_first_call(self, sessions: SessionDB) -> None:
        created = sessions.create_session(feature_id=None, snapshot_hash="ni1")
        sessions.upsert_node_instance(created["id"], "node-1", "task_pending")
        node = sessions.get_node_instance(created["id"], "node-1")
        assert node is not None
        assert node["state"] == "task_pending"

    def test_updates_node_state_on_second_call(self, sessions: SessionDB) -> None:
        created = sessions.create_session(feature_id=None, snapshot_hash="ni2")
        sessions.upsert_node_instance(created["id"], "node-x", "task_pending")
        sessions.upsert_node_instance(created["id"], "node-x", "task_running")
        node = sessions.get_node_instance(created["id"], "node-x")
        assert node is not None
        assert node["state"] == "task_running"

    def test_get_node_instance_returns_none_for_missing(self, sessions: SessionDB) -> None:
        created = sessions.create_session(feature_id=None, snapshot_hash="ni3")
        result = sessions.get_node_instance(created["id"], "nonexistent-node")
        assert result is None

    def test_get_nodes_by_state_filters_correctly(self, sessions: SessionDB) -> None:
        created = sessions.create_session(feature_id=None, snapshot_hash="ni4")
        sessions.upsert_node_instance(created["id"], "node-a", "task_pending")
        sessions.upsert_node_instance(created["id"], "node-b", "task_running")
        sessions.upsert_node_instance(created["id"], "node-c", "task_pending")

        pending = sessions.get_nodes_by_state(created["id"], "task_pending")
        assert len(pending) == 2
        assert all(n["state"] == "task_pending" for n in pending)

    def test_token_counts_accumulate_on_upsert(self, sessions: SessionDB) -> None:
        created = sessions.create_session(feature_id=None, snapshot_hash="ni5")
        sessions.upsert_node_instance(
            created["id"], "node-t", "task_pending",
            input_tokens=100, output_tokens=50, total_tokens=150, cost_usd=0.01,
        )
        sessions.upsert_node_instance(
            created["id"], "node-t", "task_running",
            input_tokens=200, output_tokens=75, total_tokens=275, cost_usd=0.02,
        )
        node = sessions.get_node_instance(created["id"], "node-t")
        assert node is not None
        # Tokens accumulate on ON CONFLICT UPDATE
        assert node["input_tokens"] == 300
        assert node["output_tokens"] == 125


# ---------------------------------------------------------------------------
# Touch session (heartbeat)
# ---------------------------------------------------------------------------


class TestTouchSession:
    def test_touch_returns_true_for_existing_session(self, sessions: SessionDB) -> None:
        created = sessions.create_session(feature_id=None, snapshot_hash="t1")
        result = sessions.touch_session(created["id"])
        assert result is True

    def test_touch_returns_false_for_missing_session(self, sessions: SessionDB) -> None:
        result = sessions.touch_session("sess-does-not-exist")
        assert result is False

    def test_touch_updates_last_updated_at(self, sessions: SessionDB) -> None:
        created = sessions.create_session(feature_id=None, snapshot_hash="t2")
        before = created["last_updated_at"]
        sessions.touch_session(created["id"])
        fetched = sessions.get_session(created["id"])
        assert fetched is not None
        # last_updated_at should have been refreshed (>= original timestamp)
        assert fetched["last_updated_at"] >= before


# ---------------------------------------------------------------------------
# Snapshot operations
# ---------------------------------------------------------------------------


class TestSnapshots:
    def test_save_and_retrieve_snapshot(self, sessions: SessionDB) -> None:
        sessions.save_snapshot("sha256abc", '{"graph": {}}')
        result = sessions.get_snapshot("sha256abc")
        assert result == '{"graph": {}}'

    def test_get_snapshot_returns_none_for_missing_hash(self, sessions: SessionDB) -> None:
        result = sessions.get_snapshot("nonexistent-hash")
        assert result is None

    def test_snapshot_exists_returns_true_after_save(self, sessions: SessionDB) -> None:
        sessions.save_snapshot("hash-xyz", '{"v": 1}')
        assert sessions.snapshot_exists("hash-xyz") is True

    def test_snapshot_exists_returns_false_for_missing(self, sessions: SessionDB) -> None:
        assert sessions.snapshot_exists("not-saved") is False

    def test_save_snapshot_is_idempotent(self, sessions: SessionDB) -> None:
        sessions.save_snapshot("idem-hash", '{"a": 1}')
        # Second save with same hash should not raise
        sessions.save_snapshot("idem-hash", '{"a": 1}')
        assert sessions.snapshot_exists("idem-hash") is True


# ---------------------------------------------------------------------------
# Loop states
# ---------------------------------------------------------------------------


class TestLoopStates:
    def test_upsert_and_retrieve_loop_state(self, sessions: SessionDB) -> None:
        created = sessions.create_session(feature_id=None, snapshot_hash="l1")
        sessions.upsert_loop_state(
            created["id"], "loop-main", current_iteration=2, max_iterations=5
        )
        state = sessions.get_loop_state(created["id"], "loop-main")
        assert state is not None
        assert state["current_iteration"] == 2
        assert state["max_iterations"] == 5

    def test_get_loop_state_returns_none_for_missing(self, sessions: SessionDB) -> None:
        created = sessions.create_session(feature_id=None, snapshot_hash="l2")
        state = sessions.get_loop_state(created["id"], "missing-loop")
        assert state is None

    def test_reset_loop_states_sets_iteration_to_zero(self, sessions: SessionDB) -> None:
        created = sessions.create_session(feature_id=None, snapshot_hash="l3")
        sessions.upsert_loop_state(
            created["id"], "loop-a", current_iteration=3, max_iterations=10
        )
        sessions.upsert_loop_state(
            created["id"], "loop-b", current_iteration=7, max_iterations=10
        )

        count = sessions.reset_loop_states(created["id"])
        assert count == 2

        state_a = sessions.get_loop_state(created["id"], "loop-a")
        assert state_a is not None
        assert state_a["current_iteration"] == 0

    def test_loop_history_is_stored_and_retrieved(self, sessions: SessionDB) -> None:
        created = sessions.create_session(feature_id=None, snapshot_hash="l4")
        history = [{"result": "pass", "iteration": 1}]
        sessions.upsert_loop_state(
            created["id"], "loop-hist", current_iteration=1, max_iterations=3, history=history
        )
        state = sessions.get_loop_state(created["id"], "loop-hist")
        assert state is not None
        assert state["history"] == history


# ---------------------------------------------------------------------------
# Get latest session
# ---------------------------------------------------------------------------


class TestGetLatestSession:
    def test_returns_none_when_no_sessions(self, sessions: SessionDB) -> None:
        result = sessions.get_latest_session()
        assert result is None

    def test_returns_most_recently_created_session(self, sessions: SessionDB) -> None:
        sessions.create_session(feature_id=None, snapshot_hash="old1")
        second = sessions.create_session(feature_id=None, snapshot_hash="new1")
        result = sessions.get_latest_session()
        assert result is not None
        assert result["id"] == second["id"]


# ---------------------------------------------------------------------------
# Unblock tasks for resume
# ---------------------------------------------------------------------------


class TestUnblockTasksForResume:
    def test_resets_blocked_nodes_to_pending(self, sessions: SessionDB) -> None:
        created = sessions.create_session(feature_id=None, snapshot_hash="ubr1")
        sessions.upsert_node_instance(created["id"], "node-blocked", "task_blocked")

        unblocked = sessions.unblock_tasks_for_resume(created["id"])

        assert "node-blocked" in unblocked
        node = sessions.get_node_instance(created["id"], "node-blocked")
        assert node is not None
        assert node["state"] == "task_pending"

    def test_returns_empty_list_when_no_blocked_nodes(self, sessions: SessionDB) -> None:
        created = sessions.create_session(feature_id=None, snapshot_hash="ubr2")
        sessions.upsert_node_instance(created["id"], "node-done", "task_completed")

        unblocked = sessions.unblock_tasks_for_resume(created["id"])
        assert unblocked == []


# ---------------------------------------------------------------------------
# Find sessions with failed nodes
# ---------------------------------------------------------------------------


class TestFindSessionsWithFailedNodes:
    def test_returns_session_id_when_failed_node_exists(self, sessions: SessionDB) -> None:
        created = sessions.create_session(feature_id=None, snapshot_hash="fsfn1")
        sessions.upsert_node_instance(created["id"], "node-fail", "task_failed")

        result = sessions.find_sessions_with_failed_nodes()
        assert created["id"] in result

    def test_returns_empty_list_when_no_failures(self, sessions: SessionDB) -> None:
        sessions.create_session(feature_id=None, snapshot_hash="fsfn2")
        result = sessions.find_sessions_with_failed_nodes()
        assert result == []

"""Tests for SandboxDB project tracking and operation logging."""

from __future__ import annotations

from pathlib import Path

import pytest
from pixl.storage.db.connection import PixlDB


@pytest.fixture()
def db(tmp_path: Path) -> PixlDB:
    """Create a fresh in-memory PixlDB with schema initialized."""
    pixl_dir = tmp_path / ".pixl"
    pixl_dir.mkdir()
    db = PixlDB(tmp_path, pixl_dir=pixl_dir)
    db.initialize()
    return db


class TestCreateProject:
    def test_create_project_returns_dict(self, db: PixlDB) -> None:
        result = db.sandboxes.create_project(
            "proj-1",
            "https://sandbox.example.com",
            repo_url="https://github.com/org/repo",
            branch="develop",
            env_keys=["API_KEY", "SECRET"],
            config={"timeout": 30},
        )
        assert isinstance(result, dict)
        assert result["id"] == "proj-1"
        assert result["sandbox_url"] == "https://sandbox.example.com"
        assert result["repo_url"] == "https://github.com/org/repo"
        assert result["branch"] == "develop"
        assert result["env_keys"] == ["API_KEY", "SECRET"]
        assert result["config"] == {"timeout": 30}
        assert result["status"] == "creating"
        assert result["created_at"] is not None

    def test_create_project_defaults(self, db: PixlDB) -> None:
        result = db.sandboxes.create_project("proj-2", "https://sandbox.example.com")
        assert result["branch"] == "main"
        assert result["repo_url"] is None
        assert result["env_keys"] == []
        assert result["config"] == {}


class TestGetProject:
    def test_get_project_returns_none_for_missing(self, db: PixlDB) -> None:
        result = db.sandboxes.get_project("nonexistent-id")
        assert result is None

    def test_get_project_returns_created_project(self, db: PixlDB) -> None:
        db.sandboxes.create_project("proj-1", "https://sandbox.example.com")
        result = db.sandboxes.get_project("proj-1")
        assert result is not None
        assert result["id"] == "proj-1"


class TestListProjects:
    def test_list_projects_empty(self, db: PixlDB) -> None:
        result = db.sandboxes.list_projects()
        assert result == []

    def test_list_projects_with_status_filter(self, db: PixlDB) -> None:
        db.sandboxes.create_project("proj-1", "https://s1.example.com")
        db.sandboxes.create_project("proj-2", "https://s2.example.com")
        # Update one project to a different status
        db.sandboxes.update_project("proj-2", status="ready")

        creating = db.sandboxes.list_projects(status="creating")
        assert len(creating) == 1
        assert creating[0]["id"] == "proj-1"

        ready = db.sandboxes.list_projects(status="ready")
        assert len(ready) == 1
        assert ready[0]["id"] == "proj-2"

    def test_list_projects_respects_limit(self, db: PixlDB) -> None:
        for i in range(5):
            db.sandboxes.create_project(f"proj-{i}", f"https://s{i}.example.com")

        result = db.sandboxes.list_projects(limit=3)
        assert len(result) == 3

    def test_list_projects_ordered_by_created_at_desc(self, db: PixlDB) -> None:
        db.sandboxes.create_project("proj-a", "https://a.example.com")
        db.sandboxes.create_project("proj-b", "https://b.example.com")

        result = db.sandboxes.list_projects()
        # Most recently created first
        assert len(result) == 2
        assert result[0]["created_at"] >= result[1]["created_at"]


class TestUpdateProject:
    def test_update_project_changes_fields(self, db: PixlDB) -> None:
        db.sandboxes.create_project("proj-1", "https://sandbox.example.com")
        result = db.sandboxes.update_project("proj-1", status="ready")

        assert result is not None
        assert result["status"] == "ready"
        assert result["updated_at"] is not None

    def test_update_project_returns_none_for_missing(self, db: PixlDB) -> None:
        result = db.sandboxes.update_project("nonexistent-id", status="ready")
        # update_project calls get_project after the UPDATE, which returns None
        assert result is None

    def test_update_project_with_no_fields_returns_current(self, db: PixlDB) -> None:
        db.sandboxes.create_project("proj-1", "https://sandbox.example.com")
        result = db.sandboxes.update_project("proj-1")
        assert result is not None
        assert result["id"] == "proj-1"

    def test_update_project_json_fields(self, db: PixlDB) -> None:
        db.sandboxes.create_project("proj-1", "https://sandbox.example.com")
        result = db.sandboxes.update_project(
            "proj-1",
            env_keys=["NEW_KEY"],
            config={"new": "value"},
        )
        assert result is not None
        assert result["env_keys"] == ["NEW_KEY"]
        assert result["config"] == {"new": "value"}


class TestLogOperation:
    def test_log_operation_success(self, db: PixlDB) -> None:
        db.sandboxes.create_project("proj-1", "https://sandbox.example.com")
        op_id = db.sandboxes.log_operation(
            "proj-1",
            "deploy",
            status="completed",
            request={"image": "node:18"},
            response={"ok": True},
        )
        assert isinstance(op_id, int)
        assert op_id > 0

    def test_log_operation_with_error(self, db: PixlDB) -> None:
        db.sandboxes.create_project("proj-1", "https://sandbox.example.com")
        op_id = db.sandboxes.log_operation(
            "proj-1",
            "deploy",
            status="failed",
            error="Connection timeout after 30s",
        )
        assert isinstance(op_id, int)
        assert op_id > 0

        # Verify the error is stored
        row = db.conn.execute(
            "SELECT error, status FROM sandbox_operations WHERE id = ?",
            (op_id,),
        ).fetchone()
        assert row["error"] == "Connection timeout after 30s"
        assert row["status"] == "failed"

    def test_log_operation_with_duration(self, db: PixlDB) -> None:
        db.sandboxes.create_project("proj-1", "https://sandbox.example.com")
        op_id = db.sandboxes.log_operation(
            "proj-1",
            "exec",
            status="completed",
            duration_ms=1250,
        )
        row = db.conn.execute(
            "SELECT duration_ms FROM sandbox_operations WHERE id = ?",
            (op_id,),
        ).fetchone()
        assert row["duration_ms"] == 1250

    def test_log_operation_default_status_is_started(self, db: PixlDB) -> None:
        db.sandboxes.create_project("proj-1", "https://sandbox.example.com")
        op_id = db.sandboxes.log_operation("proj-1", "health_check")

        row = db.conn.execute(
            "SELECT status FROM sandbox_operations WHERE id = ?",
            (op_id,),
        ).fetchone()
        assert row["status"] == "started"

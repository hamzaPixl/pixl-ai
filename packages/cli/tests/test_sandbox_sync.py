"""Tests for pixl sandbox sync command."""

from __future__ import annotations

import json
import sqlite3
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner
from pixl_cli.main import cli


@pytest.fixture()
def runner():
    return CliRunner()


@pytest.fixture()
def mock_client():
    client = MagicMock()
    client._client = MagicMock()
    client._client.base_url = "https://sandbox.example.com"
    return client


@pytest.fixture()
def mock_db():
    """Create a mock DB that records raw SQL calls for sync verification."""
    db = MagicMock()
    db.sandboxes = MagicMock()
    return db


class TestSandboxSync:
    """Tests for the sandbox sync command."""

    def test_sync_calls_export(self, runner, mock_client, mock_db):
        """Sync should call client.export() with the project_id."""
        mock_client.export.return_value = {
            "sessions": [],
            "events": [],
            "artifacts": [],
        }
        with (
            patch("pixl_cli.commands.sandbox._get_client", return_value=mock_client),
            patch(
                "pixl_cli.context.CLIContext.db",
                new_callable=lambda: property(lambda self: mock_db),
            ),
        ):
            result = runner.invoke(cli, ["sandbox", "sync", "proj-1"])
        mock_client.export.assert_called_once_with("proj-1")
        assert result.exit_code == 0

    def test_sync_empty_data(self, runner, mock_client, mock_db):
        """Sync with empty export data should report zero counts."""
        mock_client.export.return_value = {
            "sessions": [],
            "events": [],
            "artifacts": [],
        }
        with (
            patch("pixl_cli.commands.sandbox._get_client", return_value=mock_client),
            patch(
                "pixl_cli.context.CLIContext.db",
                new_callable=lambda: property(lambda self: mock_db),
            ),
        ):
            result = runner.invoke(cli, ["--json", "sandbox", "sync", "proj-1"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["synced"]["sessions"] == 0
        assert data["synced"]["events"] == 0
        assert data["synced"]["artifacts"] == 0

    def test_sync_json_output_format(self, runner, mock_client, mock_db):
        """JSON output should include project_id, synced counts, and duration."""
        mock_client.export.return_value = {
            "sessions": [],
            "events": [],
            "artifacts": [],
        }
        with (
            patch("pixl_cli.commands.sandbox._get_client", return_value=mock_client),
            patch(
                "pixl_cli.context.CLIContext.db",
                new_callable=lambda: property(lambda self: mock_db),
            ),
        ):
            result = runner.invoke(cli, ["--json", "sandbox", "sync", "my-sandbox"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["project_id"] == "my-sandbox"
        assert "synced" in data
        assert "duration_ms" in data

    def test_sync_export_failure(self, runner, mock_client, mock_db):
        """Sync should exit 1 and report error when export fails."""
        mock_client.export.side_effect = Exception("connection refused")
        with (
            patch("pixl_cli.commands.sandbox._get_client", return_value=mock_client),
            patch(
                "pixl_cli.context.CLIContext.db",
                new_callable=lambda: property(lambda self: mock_db),
            ),
        ):
            result = runner.invoke(cli, ["sandbox", "sync", "proj-1"])
        assert result.exit_code == 1

    def test_sync_sessions_with_provenance(self, runner, mock_client, mock_db):
        """Sessions should be inserted with sandbox_origin_id for provenance."""
        mock_client.export.return_value = {
            "sessions": [
                {
                    "id": "sess-abc",
                    "feature_id": "feat-1",
                    "snapshot_hash": "hash-1",
                    "status": "completed",
                    "created_at": "2026-01-01T00:00:00",
                    "started_at": "2026-01-01T00:01:00",
                    "ended_at": "2026-01-01T00:10:00",
                }
            ],
            "events": [],
            "artifacts": [],
        }

        # Use a real in-memory SQLite DB to verify SQL operations
        conn = sqlite3.connect(":memory:")
        conn.execute(
            """CREATE TABLE workflow_sessions (
                id TEXT PRIMARY KEY,
                feature_id TEXT,
                snapshot_hash TEXT,
                status TEXT,
                created_at TEXT,
                started_at TEXT,
                ended_at TEXT,
                sandbox_origin_id TEXT
            )"""
        )

        mock_db.write.return_value.__enter__ = MagicMock(return_value=conn)
        mock_db.write.return_value.__exit__ = MagicMock(return_value=False)

        with (
            patch("pixl_cli.commands.sandbox._get_client", return_value=mock_client),
            patch(
                "pixl_cli.context.CLIContext.db",
                new_callable=lambda: property(lambda self: mock_db),
            ),
        ):
            result = runner.invoke(cli, ["--json", "sandbox", "sync", "my-sandbox"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["synced"]["sessions"] == 1

        # Verify provenance was set
        row = conn.execute(
            "SELECT sandbox_origin_id FROM workflow_sessions WHERE id = 'sess-abc'"
        ).fetchone()
        assert row is not None
        assert row[0] == "my-sandbox"
        conn.close()

    def test_sync_events_with_provenance(self, runner, mock_client, mock_db):
        """Events should be inserted with sandbox_origin_id for provenance."""
        mock_client.export.return_value = {
            "sessions": [],
            "events": [
                {
                    "event_type": "node_completed",
                    "session_id": "sess-1",
                    "node_id": "node-1",
                    "entity_type": None,
                    "entity_id": None,
                    "payload": {"result": "ok"},
                    "created_at": "2026-01-01T00:05:00",
                }
            ],
            "artifacts": [],
        }

        conn = sqlite3.connect(":memory:")
        conn.execute(
            """CREATE TABLE events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                event_type TEXT NOT NULL,
                node_id TEXT,
                entity_type TEXT,
                entity_id TEXT,
                payload_json TEXT,
                sandbox_origin_id TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )"""
        )

        mock_db.write.return_value.__enter__ = MagicMock(return_value=conn)
        mock_db.write.return_value.__exit__ = MagicMock(return_value=False)

        with (
            patch("pixl_cli.commands.sandbox._get_client", return_value=mock_client),
            patch(
                "pixl_cli.context.CLIContext.db",
                new_callable=lambda: property(lambda self: mock_db),
            ),
        ):
            result = runner.invoke(cli, ["--json", "sandbox", "sync", "my-sandbox"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["synced"]["events"] == 1

        # Verify provenance and payload
        row = conn.execute(
            "SELECT sandbox_origin_id, payload_json FROM events"
            " WHERE event_type = 'node_completed'"
        ).fetchone()
        assert row is not None
        assert row[0] == "my-sandbox"
        assert json.loads(row[1]) == {"result": "ok"}
        conn.close()

    def test_sync_artifacts_with_provenance(self, runner, mock_client, mock_db):
        """Artifacts should be inserted with sandbox_origin_id for provenance."""
        mock_client.export.return_value = {
            "sessions": [],
            "events": [],
            "artifacts": [
                {
                    "id": "art-abc123",
                    "name": "design.md",
                    "type": "document",
                    "content": "# Design doc",
                    "path": "docs/design.md",
                    "task_id": "task-1",
                    "session_id": "sess-1",
                    "tags": ["design"],
                    "extra": {},
                    "created_at": "2026-01-01T00:05:00",
                }
            ],
        }

        conn = sqlite3.connect(":memory:")
        conn.execute(
            """CREATE TABLE artifacts (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL DEFAULT 'other',
                name TEXT NOT NULL,
                path TEXT,
                content TEXT,
                task_id TEXT,
                session_id TEXT,
                tags_json TEXT NOT NULL DEFAULT '[]',
                extra_json TEXT NOT NULL DEFAULT '{}',
                sandbox_origin_id TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )"""
        )

        mock_db.write.return_value.__enter__ = MagicMock(return_value=conn)
        mock_db.write.return_value.__exit__ = MagicMock(return_value=False)

        with (
            patch("pixl_cli.commands.sandbox._get_client", return_value=mock_client),
            patch(
                "pixl_cli.context.CLIContext.db",
                new_callable=lambda: property(lambda self: mock_db),
            ),
        ):
            result = runner.invoke(cli, ["--json", "sandbox", "sync", "my-sandbox"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["synced"]["artifacts"] == 1

        # Verify provenance
        row = conn.execute(
            "SELECT sandbox_origin_id, name FROM artifacts WHERE id = 'art-abc123'"
        ).fetchone()
        assert row is not None
        assert row[0] == "my-sandbox"
        assert row[1] == "design.md"
        conn.close()

    def test_sync_dedup_sessions(self, runner, mock_client, mock_db):
        """Re-syncing the same session should not create duplicates (INSERT OR IGNORE)."""
        session_data = {
            "id": "sess-dup",
            "feature_id": "feat-1",
            "snapshot_hash": "hash-1",
            "status": "completed",
            "created_at": "2026-01-01T00:00:00",
            "started_at": None,
            "ended_at": None,
        }
        mock_client.export.return_value = {
            "sessions": [session_data],
            "events": [],
            "artifacts": [],
        }

        conn = sqlite3.connect(":memory:")
        conn.execute(
            """CREATE TABLE workflow_sessions (
                id TEXT PRIMARY KEY,
                feature_id TEXT,
                snapshot_hash TEXT,
                status TEXT,
                created_at TEXT,
                started_at TEXT,
                ended_at TEXT,
                sandbox_origin_id TEXT
            )"""
        )
        # Pre-insert the session
        conn.execute(
            "INSERT INTO workflow_sessions (id, status, sandbox_origin_id)"
            " VALUES ('sess-dup', 'completed', 'my-sandbox')"
        )
        conn.commit()

        mock_db.write.return_value.__enter__ = MagicMock(return_value=conn)
        mock_db.write.return_value.__exit__ = MagicMock(return_value=False)

        with (
            patch("pixl_cli.commands.sandbox._get_client", return_value=mock_client),
            patch(
                "pixl_cli.context.CLIContext.db",
                new_callable=lambda: property(lambda self: mock_db),
            ),
        ):
            result = runner.invoke(cli, ["--json", "sandbox", "sync", "my-sandbox"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        # Session already existed, so rowcount is 0 -- should report 0 new
        assert data["synced"]["sessions"] == 0

        # Only one row in the table (no duplicate)
        count = conn.execute("SELECT COUNT(*) FROM workflow_sessions").fetchone()[0]
        assert count == 1
        conn.close()

    def test_sync_dedup_artifacts(self, runner, mock_client, mock_db):
        """Re-syncing artifacts with same ID should not duplicate them."""
        mock_client.export.return_value = {
            "sessions": [],
            "events": [],
            "artifacts": [
                {
                    "id": "art-dup123",
                    "name": "readme.md",
                    "type": "document",
                    "content": "# Hello",
                    "task_id": "task-1",
                    "session_id": "sess-1",
                    "tags": [],
                    "extra": {},
                }
            ],
        }

        conn = sqlite3.connect(":memory:")
        conn.execute(
            """CREATE TABLE artifacts (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL DEFAULT 'other',
                name TEXT NOT NULL,
                path TEXT,
                content TEXT,
                task_id TEXT,
                session_id TEXT,
                tags_json TEXT NOT NULL DEFAULT '[]',
                extra_json TEXT NOT NULL DEFAULT '{}',
                sandbox_origin_id TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )"""
        )
        # Pre-insert
        conn.execute(
            "INSERT INTO artifacts (id, name, type, sandbox_origin_id)"
            " VALUES ('art-dup123', 'readme.md', 'document', 'my-sandbox')"
        )
        conn.commit()

        mock_db.write.return_value.__enter__ = MagicMock(return_value=conn)
        mock_db.write.return_value.__exit__ = MagicMock(return_value=False)

        with (
            patch("pixl_cli.commands.sandbox._get_client", return_value=mock_client),
            patch(
                "pixl_cli.context.CLIContext.db",
                new_callable=lambda: property(lambda self: mock_db),
            ),
        ):
            result = runner.invoke(cli, ["--json", "sandbox", "sync", "my-sandbox"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["synced"]["artifacts"] == 0

        count = conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
        assert count == 1
        conn.close()

    def test_sync_db_write_failure(self, runner, mock_client, mock_db):
        """Sync should exit 1 when DB write fails."""
        mock_client.export.return_value = {
            "sessions": [{"id": "sess-1", "status": "completed"}],
            "events": [],
            "artifacts": [],
        }
        mock_db.write.side_effect = Exception("disk full")

        with (
            patch("pixl_cli.commands.sandbox._get_client", return_value=mock_client),
            patch(
                "pixl_cli.context.CLIContext.db",
                new_callable=lambda: property(lambda self: mock_db),
            ),
        ):
            result = runner.invoke(cli, ["sandbox", "sync", "proj-1"])
        assert result.exit_code == 1

    def test_sync_logs_operation(self, runner, mock_client, mock_db):
        """Sync should log the operation to the sandbox operations table."""
        mock_client.export.return_value = {
            "sessions": [],
            "events": [],
            "artifacts": [],
        }
        with (
            patch("pixl_cli.commands.sandbox._get_client", return_value=mock_client),
            patch(
                "pixl_cli.context.CLIContext.db",
                new_callable=lambda: property(lambda self: mock_db),
            ),
        ):
            result = runner.invoke(cli, ["sandbox", "sync", "proj-1"])

        assert result.exit_code == 0
        mock_db.sandboxes.log_operation.assert_called_once()
        call_kwargs = mock_db.sandboxes.log_operation.call_args
        assert call_kwargs[0][0] == "proj-1"  # project_id
        assert call_kwargs[0][1] == "sync"  # operation

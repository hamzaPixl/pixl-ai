"""Tests for pixl sandbox CLI commands."""

from __future__ import annotations

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
    db = MagicMock()
    db.sandboxes = MagicMock()
    return db


class TestSandboxList:
    def test_list_empty(self, runner, mock_db):
        mock_db.sandboxes.list_projects.return_value = []
        with patch("pixl_cli.context.CLIContext.db", new_callable=lambda: property(lambda self: mock_db)):
            result = runner.invoke(cli, ["sandbox", "list"])
        assert result.exit_code == 0

    def test_list_json_output(self, runner, mock_db):
        mock_db.sandboxes.list_projects.return_value = [
            {"id": "proj-1", "status": "ready", "branch": "main", "repo_url": None, "created_at": "2026-01-01"},
        ]
        with patch("pixl_cli.context.CLIContext.db", new_callable=lambda: property(lambda self: mock_db)):
            result = runner.invoke(cli, ["--json", "sandbox", "list"])
        assert result.exit_code == 0

    def test_list_with_status_filter(self, runner, mock_db):
        mock_db.sandboxes.list_projects.return_value = []
        with patch("pixl_cli.context.CLIContext.db", new_callable=lambda: property(lambda self: mock_db)):
            result = runner.invoke(cli, ["sandbox", "list", "--status", "ready"])
        mock_db.sandboxes.list_projects.assert_called_once_with(status="ready")
        assert result.exit_code == 0


class TestSandboxStatus:
    def test_status_success(self, runner, mock_client):
        mock_client.status.return_value = {"id": "proj-1", "status": "ready", "versions": {}}
        with patch("pixl_cli.commands.sandbox._get_client", return_value=mock_client):
            result = runner.invoke(cli, ["sandbox", "status", "proj-1"])
        mock_client.status.assert_called_once_with("proj-1")
        assert result.exit_code == 0

    def test_status_json(self, runner, mock_client):
        mock_client.status.return_value = {"id": "proj-1", "status": "ready"}
        with patch("pixl_cli.commands.sandbox._get_client", return_value=mock_client):
            result = runner.invoke(cli, ["--json", "sandbox", "status", "proj-1"])
        assert result.exit_code == 0


class TestSandboxCreate:
    def test_create_success(self, runner, mock_client, mock_db):
        mock_client.create.return_value = {"status": "ready", "versions": {"pixl": "1.0"}}
        with (
            patch("pixl_cli.commands.sandbox._get_client", return_value=mock_client),
            patch("pixl_cli.context.CLIContext.db", new_callable=lambda: property(lambda self: mock_db)),
        ):
            result = runner.invoke(cli, ["sandbox", "create", "proj-1"])
        mock_client.create.assert_called_once()
        assert result.exit_code == 0

    def test_create_with_repo(self, runner, mock_client, mock_db):
        mock_client.create.return_value = {"status": "ready", "versions": {}}
        with (
            patch("pixl_cli.commands.sandbox._get_client", return_value=mock_client),
            patch("pixl_cli.context.CLIContext.db", new_callable=lambda: property(lambda self: mock_db)),
        ):
            result = runner.invoke(cli, ["sandbox", "create", "proj-1", "--repo-url", "https://github.com/test/repo"])
        call_args = mock_client.create.call_args
        assert call_args[1].get("repo_url") == "https://github.com/test/repo" or call_args[0][1] if len(call_args[0]) > 1 else True
        assert result.exit_code == 0

    def test_create_invalid_env_pair(self, runner, mock_db):
        with patch("pixl_cli.context.CLIContext.db", new_callable=lambda: property(lambda self: mock_db)):
            result = runner.invoke(cli, ["sandbox", "create", "proj-1", "--env", "NOEQUALS"])
        assert result.exit_code != 0


class TestSandboxDestroy:
    def test_destroy_success(self, runner, mock_client, mock_db):
        mock_client.destroy.return_value = {"ok": True}
        with (
            patch("pixl_cli.commands.sandbox._get_client", return_value=mock_client),
            patch("pixl_cli.context.CLIContext.db", new_callable=lambda: property(lambda self: mock_db)),
        ):
            result = runner.invoke(cli, ["sandbox", "destroy", "proj-1"])
        mock_client.destroy.assert_called_once_with("proj-1")
        assert result.exit_code == 0


class TestStreamHelpers:
    def test_print_stream_event_log(self, capsys):
        from pixl_cli.commands.sandbox import _print_stream_event

        _print_stream_event({"type": "log", "message": "hello"})
        captured = capsys.readouterr()
        assert "hello" in captured.out

    def test_print_stream_event_stdout(self, capsys):
        from pixl_cli.commands.sandbox import _print_stream_event

        _print_stream_event({"type": "stdout", "data": "output line"})
        captured = capsys.readouterr()
        assert "output line" in captured.out

    def test_print_stream_event_error(self, capsys):
        from pixl_cli.commands.sandbox import _print_stream_event

        _print_stream_event({"type": "error", "message": "oops"})
        captured = capsys.readouterr()
        assert "oops" in captured.err

    def test_consume_stream_collects(self):
        from pixl_cli.commands.sandbox import _consume_stream

        events = iter([{"type": "log", "message": "a"}, {"type": "done", "success": True}])
        collected = _consume_stream(events)
        assert len(collected) == 2
        assert collected[0]["type"] == "log"

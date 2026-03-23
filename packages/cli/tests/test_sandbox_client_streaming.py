"""Tests for SandboxClient SSE streaming methods."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest
from pixl_cli.sandbox_client import SandboxClient


@pytest.fixture()
def client() -> SandboxClient:
    return SandboxClient("https://sandbox.example.com", "test-api-key")


def _make_stream_response(lines: list[str], status_code: int = 200) -> MagicMock:
    """Build a mock httpx response that yields lines from iter_lines()."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.iter_lines.return_value = iter(lines)
    mock_resp.headers = {"content-type": "text/event-stream"}
    # Support context manager protocol
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


class TestStreamSSEParser:
    """Verify the SSE line-parsing logic in _stream_sse."""

    def test_parses_data_lines_as_json(self, client: SandboxClient) -> None:
        lines = [
            'data: {"type":"log","message":"hello"}',
            "",
            'data: {"type":"done"}',
        ]
        mock_resp = _make_stream_response(lines)

        with patch.object(client._client, "stream", return_value=mock_resp):
            events = list(client.exec_stream("proj-1", "echo hi"))

        assert len(events) == 2
        assert events[0] == {"type": "log", "message": "hello"}
        assert events[1] == {"type": "done"}

    def test_skips_comment_lines(self, client: SandboxClient) -> None:
        lines = [
            ": keepalive",
            'data: {"type":"log","message":"real"}',
        ]
        mock_resp = _make_stream_response(lines)

        with patch.object(client._client, "stream", return_value=mock_resp):
            events = list(client.exec_stream("proj-1", "ls"))

        assert len(events) == 1
        assert events[0]["type"] == "log"

    def test_skips_empty_lines(self, client: SandboxClient) -> None:
        lines = ["", "", 'data: {"ok":true}', ""]
        mock_resp = _make_stream_response(lines)

        with patch.object(client._client, "stream", return_value=mock_resp):
            events = list(client.exec_stream("proj-1", "pwd"))

        assert len(events) == 1
        assert events[0] == {"ok": True}

    def test_skips_malformed_json(self, client: SandboxClient) -> None:
        lines = [
            "data: not-json",
            'data: {"valid":true}',
        ]
        mock_resp = _make_stream_response(lines)

        with patch.object(client._client, "stream", return_value=mock_resp):
            events = list(client.exec_stream("proj-1", "whoami"))

        assert len(events) == 1
        assert events[0] == {"valid": True}

    def test_skips_non_data_lines(self, client: SandboxClient) -> None:
        lines = [
            "event: message",
            "id: 42",
            'data: {"type":"output"}',
        ]
        mock_resp = _make_stream_response(lines)

        with patch.object(client._client, "stream", return_value=mock_resp):
            events = list(client.exec_stream("proj-1", "date"))

        assert len(events) == 1
        assert events[0]["type"] == "output"


class TestExecStream:
    """Verify exec_stream sends correct request."""

    def test_posts_to_correct_endpoint(self, client: SandboxClient) -> None:
        mock_resp = _make_stream_response(['data: {"done":true}'])

        with patch.object(client._client, "stream", return_value=mock_resp) as mock_stream:
            list(client.exec_stream("my-project", "npm test"))

        mock_stream.assert_called_once_with(
            "POST",
            "/sandboxes/my-project/exec/stream",
            json={"command": "npm test"},
        )


class TestWorkflowStream:
    """Verify workflow_stream sends correct request and parameters."""

    def test_posts_to_correct_endpoint_minimal(self, client: SandboxClient) -> None:
        mock_resp = _make_stream_response(['data: {"step":"plan"}'])

        with patch.object(client._client, "stream", return_value=mock_resp) as mock_stream:
            list(client.workflow_stream("proj-1", "build a landing page"))

        mock_stream.assert_called_once_with(
            "POST",
            "/sandboxes/proj-1/workflow/stream",
            json={"prompt": "build a landing page", "autoApprove": True},
        )

    def test_includes_workflow_when_provided(self, client: SandboxClient) -> None:
        mock_resp = _make_stream_response(['data: {"step":"done"}'])

        with patch.object(client._client, "stream", return_value=mock_resp) as mock_stream:
            list(client.workflow_stream("proj-1", "deploy", workflow="deploy-v2"))

        call_kwargs = mock_stream.call_args
        assert call_kwargs[1]["json"]["workflowId"] == "deploy-v2"

    def test_auto_approve_false(self, client: SandboxClient) -> None:
        mock_resp = _make_stream_response(['data: {"step":"gate"}'])

        with patch.object(client._client, "stream", return_value=mock_resp) as mock_stream:
            list(client.workflow_stream("proj-1", "risky op", yes=False))

        call_kwargs = mock_stream.call_args
        assert (
            call_kwargs[1]["json"].get("autoApprove") is None
            or call_kwargs[1]["json"]["autoApprove"] is False
        )

    def test_yields_parsed_events(self, client: SandboxClient) -> None:
        lines = [
            'data: {"step":"plan","detail":"analyzing"}',
            'data: {"step":"execute","detail":"running"}',
            'data: {"step":"done"}',
        ]
        mock_resp = _make_stream_response(lines)

        with patch.object(client._client, "stream", return_value=mock_resp):
            events = list(client.workflow_stream("proj-1", "build"))

        assert len(events) == 3
        assert events[0]["step"] == "plan"
        assert events[2]["step"] == "done"


class TestStreamErrorHandling:
    """Verify graceful degradation on connection errors."""

    def test_connection_error_yields_nothing(self, client: SandboxClient) -> None:
        with patch.object(client._client, "stream", side_effect=httpx.ConnectError("refused")):
            events = list(client.exec_stream("proj-1", "ls"))

        assert events == []

    def test_timeout_error_yields_nothing(self, client: SandboxClient) -> None:
        with patch.object(client._client, "stream", side_effect=httpx.TimeoutException("timeout")):
            events = list(client.workflow_stream("proj-1", "build"))

        assert events == []

    def test_http_error_yields_nothing(self, client: SandboxClient) -> None:
        with patch.object(
            client._client,
            "stream",
            side_effect=httpx.HTTPStatusError(
                "500", request=MagicMock(), response=MagicMock(status_code=500)
            ),
        ):
            events = list(client.exec_stream("proj-1", "ls"))

        assert events == []

"""Tests for sandbox workflow/exec commands with SSE streaming."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

# -- Helpers ------------------------------------------------------------------


def _make_cli_ctx(is_json: bool = False) -> MagicMock:
    """Build a mock CLI context returned by get_ctx()."""
    ctx = MagicMock()
    ctx.is_json = is_json
    ctx.db.sandboxes = MagicMock()
    return ctx


def _make_client(
    *,
    workflow_result: dict | None = None,
    exec_result: dict | None = None,
    stream_events: list[dict] | None = None,
) -> MagicMock:
    """Build a mock SandboxClient."""
    client = MagicMock()
    if workflow_result is not None:
        client.workflow.return_value = workflow_result
    if exec_result is not None:
        client.exec.return_value = exec_result
    if stream_events is not None:
        client.workflow_stream.return_value = iter(stream_events)
        client.exec_stream.return_value = iter(stream_events)
    else:
        # Default: empty iterator (simulates streaming failure/no events)
        client.workflow_stream.return_value = iter([])
        client.exec_stream.return_value = iter([])
    return client


# -- Workflow command tests ---------------------------------------------------


class TestSandboxWorkflowStreaming:
    """Verify sandbox workflow uses streaming by default."""

    @patch("pixl_cli.commands.sandbox._get_client")
    @patch("pixl_cli.commands.sandbox.get_ctx")
    def test_streams_by_default(self, mock_get_ctx, mock_get_client) -> None:
        """When --no-stream is not set, workflow should call workflow_stream."""
        from pixl_cli.commands.sandbox import sandbox

        events = [
            {"type": "log", "message": "Planning..."},
            {"type": "log", "message": "Executing..."},
            {"type": "done", "success": True},
        ]
        mock_client = _make_client(stream_events=events, workflow_result={"success": True})
        mock_get_client.return_value = mock_client
        mock_get_ctx.return_value = _make_cli_ctx(is_json=False)

        runner = CliRunner()
        result = runner.invoke(sandbox, ["workflow", "proj-1", "--prompt", "build it", "--yes"])

        assert result.exit_code == 0
        mock_client.workflow_stream.assert_called_once()
        mock_client.workflow.assert_not_called()

    @patch("pixl_cli.commands.sandbox._get_client")
    @patch("pixl_cli.commands.sandbox.get_ctx")
    def test_prints_stream_events(self, mock_get_ctx, mock_get_client) -> None:
        """Streaming events should be printed to stdout."""
        from pixl_cli.commands.sandbox import sandbox

        events = [
            {"type": "log", "message": "Step 1"},
            {"type": "output", "data": "some output"},
            {"type": "done", "success": True},
        ]
        mock_client = _make_client(stream_events=events, workflow_result={"success": True})
        mock_get_client.return_value = mock_client
        mock_get_ctx.return_value = _make_cli_ctx(is_json=False)

        runner = CliRunner()
        result = runner.invoke(sandbox, ["workflow", "proj-1", "--prompt", "build it", "--yes"])

        assert result.exit_code == 0
        assert "Step 1" in result.output

    @patch("pixl_cli.commands.sandbox._get_client")
    @patch("pixl_cli.commands.sandbox.get_ctx")
    def test_no_stream_flag_uses_sync(self, mock_get_ctx, mock_get_client) -> None:
        """When --no-stream is set, workflow should use synchronous call."""
        from pixl_cli.commands.sandbox import sandbox

        mock_client = _make_client(workflow_result={"success": True, "stdout": "done"})
        mock_get_client.return_value = mock_client
        mock_get_ctx.return_value = _make_cli_ctx(is_json=False)

        runner = CliRunner()
        result = runner.invoke(
            sandbox, ["workflow", "proj-1", "--prompt", "build it", "--yes", "--no-stream"]
        )

        assert result.exit_code == 0
        mock_client.workflow.assert_called_once()
        mock_client.workflow_stream.assert_not_called()

    @patch("pixl_cli.commands.sandbox._get_client")
    @patch("pixl_cli.commands.sandbox.get_ctx")
    def test_json_mode_uses_sync(self, mock_get_ctx, mock_get_client) -> None:
        """When --json is active, workflow should use sync path for clean JSON output."""
        from pixl_cli.commands.sandbox import sandbox

        mock_client = _make_client(workflow_result={"success": True})
        mock_get_client.return_value = mock_client
        mock_get_ctx.return_value = _make_cli_ctx(is_json=True)

        runner = CliRunner()
        result = runner.invoke(sandbox, ["workflow", "proj-1", "--prompt", "build it", "--yes"])

        assert result.exit_code == 0
        mock_client.workflow.assert_called_once()
        mock_client.workflow_stream.assert_not_called()

    @patch("pixl_cli.commands.sandbox._get_client")
    @patch("pixl_cli.commands.sandbox.get_ctx")
    def test_stream_fallback_on_empty(self, mock_get_ctx, mock_get_client) -> None:
        """When streaming yields no events, fall back to sync."""
        from pixl_cli.commands.sandbox import sandbox

        mock_client = _make_client(
            stream_events=[],  # empty = streaming failed
            workflow_result={"success": True, "stdout": "sync output"},
        )
        mock_get_client.return_value = mock_client
        mock_get_ctx.return_value = _make_cli_ctx(is_json=False)

        runner = CliRunner()
        result = runner.invoke(sandbox, ["workflow", "proj-1", "--prompt", "build it", "--yes"])

        assert result.exit_code == 0
        mock_client.workflow_stream.assert_called_once()
        mock_client.workflow.assert_called_once()

    @patch("pixl_cli.commands.sandbox._get_client")
    @patch("pixl_cli.commands.sandbox.get_ctx")
    def test_passes_workflow_id_to_stream(self, mock_get_ctx, mock_get_client) -> None:
        """workflow_stream should receive the workflow ID."""
        from pixl_cli.commands.sandbox import sandbox

        events = [{"type": "done", "success": True}]
        mock_client = _make_client(stream_events=events)
        mock_get_client.return_value = mock_client
        mock_get_ctx.return_value = _make_cli_ctx(is_json=False)

        runner = CliRunner()
        result = runner.invoke(
            sandbox,
            ["workflow", "proj-1", "--prompt", "deploy", "--workflow-id", "wf-42", "--yes"],
        )

        assert result.exit_code == 0
        mock_client.workflow_stream.assert_called_once_with(
            "proj-1", "deploy", workflow="wf-42", yes=True
        )


# -- Exec command tests -------------------------------------------------------


class TestSandboxExecStreaming:
    """Verify sandbox exec uses streaming by default."""

    @patch("pixl_cli.commands.sandbox._get_client")
    @patch("pixl_cli.commands.sandbox.get_ctx")
    def test_streams_by_default(self, mock_get_ctx, mock_get_client) -> None:
        """When --no-stream is not set, exec should call exec_stream."""
        from pixl_cli.commands.sandbox import sandbox

        events = [
            {"type": "output", "data": "hello world"},
            {"type": "done", "exit_code": 0},
        ]
        mock_client = _make_client(stream_events=events, exec_result={"success": True})
        mock_get_client.return_value = mock_client
        mock_get_ctx.return_value = _make_cli_ctx(is_json=False)

        runner = CliRunner()
        result = runner.invoke(sandbox, ["exec", "proj-1", "echo hello"])

        assert result.exit_code == 0
        mock_client.exec_stream.assert_called_once()
        mock_client.exec.assert_not_called()

    @patch("pixl_cli.commands.sandbox._get_client")
    @patch("pixl_cli.commands.sandbox.get_ctx")
    def test_prints_stream_events(self, mock_get_ctx, mock_get_client) -> None:
        """Streaming events should be printed to stdout."""
        from pixl_cli.commands.sandbox import sandbox

        events = [
            {"type": "stdout", "data": "line 1"},
            {"type": "stdout", "data": "line 2"},
            {"type": "done", "exit_code": 0},
        ]
        mock_client = _make_client(stream_events=events, exec_result={"success": True})
        mock_get_client.return_value = mock_client
        mock_get_ctx.return_value = _make_cli_ctx(is_json=False)

        runner = CliRunner()
        result = runner.invoke(sandbox, ["exec", "proj-1", "ls -la"])

        assert result.exit_code == 0
        assert "line 1" in result.output
        assert "line 2" in result.output

    @patch("pixl_cli.commands.sandbox._get_client")
    @patch("pixl_cli.commands.sandbox.get_ctx")
    def test_no_stream_flag_uses_sync(self, mock_get_ctx, mock_get_client) -> None:
        """When --no-stream is set, exec should use synchronous call."""
        from pixl_cli.commands.sandbox import sandbox

        mock_client = _make_client(exec_result={"success": True, "stdout": "sync result"})
        mock_get_client.return_value = mock_client
        mock_get_ctx.return_value = _make_cli_ctx(is_json=False)

        runner = CliRunner()
        result = runner.invoke(sandbox, ["exec", "proj-1", "echo hi", "--no-stream"])

        assert result.exit_code == 0
        mock_client.exec.assert_called_once()
        mock_client.exec_stream.assert_not_called()

    @patch("pixl_cli.commands.sandbox._get_client")
    @patch("pixl_cli.commands.sandbox.get_ctx")
    def test_json_mode_uses_sync(self, mock_get_ctx, mock_get_client) -> None:
        """When --json is active, exec should use sync path."""
        from pixl_cli.commands.sandbox import sandbox

        mock_client = _make_client(exec_result={"success": True, "stdout": "output"})
        mock_get_client.return_value = mock_client
        mock_get_ctx.return_value = _make_cli_ctx(is_json=True)

        runner = CliRunner()
        result = runner.invoke(sandbox, ["exec", "proj-1", "ls"])

        assert result.exit_code == 0
        mock_client.exec.assert_called_once()
        mock_client.exec_stream.assert_not_called()

    @patch("pixl_cli.commands.sandbox._get_client")
    @patch("pixl_cli.commands.sandbox.get_ctx")
    def test_stream_fallback_on_empty(self, mock_get_ctx, mock_get_client) -> None:
        """When streaming yields no events, fall back to sync."""
        from pixl_cli.commands.sandbox import sandbox

        mock_client = _make_client(
            stream_events=[],
            exec_result={"success": True, "stdout": "sync fallback"},
        )
        mock_get_client.return_value = mock_client
        mock_get_ctx.return_value = _make_cli_ctx(is_json=False)

        runner = CliRunner()
        result = runner.invoke(sandbox, ["exec", "proj-1", "whoami"])

        assert result.exit_code == 0
        mock_client.exec_stream.assert_called_once()
        mock_client.exec.assert_called_once()

"""Tests for execution hook modules.

Covers:
- pixl.execution.hooks.git_hooks  — init_git_hook, finalize_git_hook
- pixl.execution.hooks.sync_hooks — materialize_sync_results_hook
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from pixl.execution.hooks import HookContext

# ---------------------------------------------------------------------------
# Helpers — minimal HookContext construction
# ---------------------------------------------------------------------------


def _make_session(session_id: str = "sess-001", feature_id: str = "feat-1") -> MagicMock:
    session = MagicMock()
    session.id = session_id
    session.structured_outputs = {}
    return session


def _make_ctx(
    tmp_path: Path,
    *,
    session_id: str = "sess-001",
    feature_id: str = "feat-1",
    params: dict | None = None,
) -> HookContext:
    session = _make_session(session_id, feature_id)
    return HookContext(
        session=session,
        project_root=tmp_path,
        session_dir=tmp_path / ".pixl" / "sessions" / session_id,
        artifacts_dir=tmp_path / ".pixl" / "artifacts",
        feature_id=feature_id,
        params=params or {},
    )


# ---------------------------------------------------------------------------
# git_hooks — init_git_hook
# ---------------------------------------------------------------------------


class TestInitGitHook:
    """Tests for init_git_hook."""

    def test_reuses_existing_worktree(self, tmp_path: Path) -> None:
        """When worktree directory already exists, hook returns success immediately."""
        from pixl.execution.hooks.git_hooks import init_git_hook

        ctx = _make_ctx(tmp_path)
        worktree_dir = tmp_path / ".pixl" / "worktrees" / ctx.session.id
        worktree_dir.mkdir(parents=True)

        result = init_git_hook(ctx)

        assert result.success is True
        assert result.data.get("reused") is True
        assert result.workspace_root == str(worktree_dir)

    def test_returns_failure_when_git_rev_parse_fails(self, tmp_path: Path) -> None:
        """When 'git rev-parse HEAD' exits non-zero, hook returns failure."""
        from pixl.execution.hooks.git_hooks import init_git_hook

        ctx = _make_ctx(tmp_path)

        failed_proc = MagicMock()
        failed_proc.returncode = 128
        failed_proc.stderr = "fatal: not a git repository"

        with patch("subprocess.run", return_value=failed_proc):
            result = init_git_hook(ctx)

        assert result.success is False
        assert "git rev-parse HEAD failed" in result.error

    def test_returns_failure_when_worktree_add_fails(self, tmp_path: Path) -> None:
        """When 'git worktree add' exits non-zero, hook returns failure."""
        from pixl.execution.hooks.git_hooks import init_git_hook

        ctx = _make_ctx(tmp_path)

        def _run_side_effect(cmd, **kwargs):
            proc = MagicMock()
            if "rev-parse" in cmd:
                proc.returncode = 0
                proc.stdout = "abc123\n"
                proc.stderr = ""
            elif "branch" in cmd:
                proc.returncode = 0
                proc.stderr = ""
            else:
                # worktree add
                proc.returncode = 1
                proc.stderr = "error: worktree already registered"
            return proc

        with patch("subprocess.run", side_effect=_run_side_effect):
            result = init_git_hook(ctx)

        assert result.success is False
        assert "git worktree add failed" in result.error

    def test_returns_success_on_happy_path(self, tmp_path: Path) -> None:
        """When all git commands succeed, hook returns success with branch + commit data."""
        from pixl.execution.hooks.git_hooks import init_git_hook

        ctx = _make_ctx(tmp_path, params={"branch_prefix": "ci"})

        def _run_side_effect(cmd, **kwargs):
            proc = MagicMock()
            proc.returncode = 0
            proc.stdout = "deadbeef\n"
            proc.stderr = ""
            return proc

        with patch("subprocess.run", side_effect=_run_side_effect):
            result = init_git_hook(ctx)

        assert result.success is True
        assert result.data.get("base_commit") == "deadbeef"
        assert "ci/" in result.data.get("branch", "")

    def test_handles_timeout(self, tmp_path: Path) -> None:
        """TimeoutExpired during git commands is caught and returns failure."""
        from pixl.execution.hooks.git_hooks import init_git_hook

        ctx = _make_ctx(tmp_path)

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 10)):
            result = init_git_hook(ctx)

        assert result.success is False
        assert "timed out" in result.error

    def test_handles_unexpected_exception(self, tmp_path: Path) -> None:
        """Any unexpected exception is caught and returned as failure."""
        from pixl.execution.hooks.git_hooks import init_git_hook

        ctx = _make_ctx(tmp_path)

        with patch("subprocess.run", side_effect=OSError("permission denied")):
            result = init_git_hook(ctx)

        assert result.success is False
        assert "permission denied" in result.error

    def test_branch_prefix_from_params(self, tmp_path: Path) -> None:
        """Branch name uses the branch_prefix parameter."""
        from pixl.execution.hooks.git_hooks import init_git_hook

        ctx = _make_ctx(tmp_path, params={"branch_prefix": "myprefix"})

        def _run_side_effect(cmd, **kwargs):
            proc = MagicMock()
            proc.returncode = 0
            proc.stdout = "sha1\n"
            proc.stderr = ""
            return proc

        with patch("subprocess.run", side_effect=_run_side_effect):
            result = init_git_hook(ctx)

        assert result.success is True
        assert result.data["branch"].startswith("myprefix/")


# ---------------------------------------------------------------------------
# git_hooks — finalize_git_hook
# ---------------------------------------------------------------------------


class TestFinalizeGitHook:
    def test_already_cleaned(self, tmp_path: Path) -> None:
        """When worktree directory does not exist, reports already_cleaned."""
        from pixl.execution.hooks.git_hooks import finalize_git_hook

        ctx = _make_ctx(tmp_path)
        # Worktree dir never created, so it doesn't exist
        result = finalize_git_hook(ctx)

        assert result.success is True
        assert result.data.get("already_cleaned") is True

    def test_removes_worktree_successfully(self, tmp_path: Path) -> None:
        """When worktree dir exists and git command succeeds, returns success."""
        from pixl.execution.hooks.git_hooks import finalize_git_hook

        ctx = _make_ctx(tmp_path)
        worktree_dir = tmp_path / ".pixl" / "worktrees" / ctx.session.id
        worktree_dir.mkdir(parents=True)

        success_proc = MagicMock()
        success_proc.returncode = 0
        success_proc.stderr = ""

        with patch("subprocess.run", return_value=success_proc):
            result = finalize_git_hook(ctx)

        assert result.success is True
        assert result.data.get("removed") == str(worktree_dir)

    def test_returns_failure_when_git_remove_fails(self, tmp_path: Path) -> None:
        """When 'git worktree remove' exits non-zero, hook returns failure."""
        from pixl.execution.hooks.git_hooks import finalize_git_hook

        ctx = _make_ctx(tmp_path)
        worktree_dir = tmp_path / ".pixl" / "worktrees" / ctx.session.id
        worktree_dir.mkdir(parents=True)

        fail_proc = MagicMock()
        fail_proc.returncode = 1
        fail_proc.stderr = "error: worktree not registered"

        with patch("subprocess.run", return_value=fail_proc):
            result = finalize_git_hook(ctx)

        assert result.success is False
        assert "git worktree remove failed" in result.error

    def test_handles_exception(self, tmp_path: Path) -> None:
        """Unexpected exception during cleanup is caught and returned as failure."""
        from pixl.execution.hooks.git_hooks import finalize_git_hook

        ctx = _make_ctx(tmp_path)
        worktree_dir = tmp_path / ".pixl" / "worktrees" / ctx.session.id
        worktree_dir.mkdir(parents=True)

        with patch("subprocess.run", side_effect=OSError("disk full")):
            result = finalize_git_hook(ctx)

        assert result.success is False
        assert "disk full" in result.error


# ---------------------------------------------------------------------------
# sync_hooks — materialize_sync_results_hook
# ---------------------------------------------------------------------------


class TestMaterializeSyncResultsHook:
    def _make_sync_ctx(
        self,
        tmp_path: Path,
        *,
        feature_actions: list | str | None = None,
        source_node_id: str = "scan-main",
    ) -> HookContext:
        session = _make_session()
        if feature_actions is not None:
            payload = {"feature_actions": feature_actions}
            session.structured_outputs = {source_node_id: {"payload": payload}}
        return HookContext(
            session=session,
            project_root=tmp_path,
            session_dir=tmp_path / ".pixl" / "sessions" / session.id,
            artifacts_dir=tmp_path / ".pixl" / "artifacts",
            feature_id="feat-1",
            params={"source_node_id": source_node_id},
        )

    def test_invalid_feature_actions_returns_failure(self, tmp_path: Path) -> None:
        """Non-list feature_actions triggers failure."""
        from pixl.execution.hooks.sync_hooks import materialize_sync_results_hook

        ctx = self._make_sync_ctx(tmp_path, feature_actions="not-a-list")

        mock_db = MagicMock()
        mock_db.backlog = MagicMock()
        mock_db.events = MagicMock()
        mock_db.events.emit = MagicMock()

        with patch("pixl.execution.hooks.sync_hooks.PixlDB", return_value=mock_db):
            mock_db.initialize = MagicMock()
            result = materialize_sync_results_hook(ctx)

        assert result.success is False
        assert "feature_actions" in result.error

    def test_empty_feature_actions(self, tmp_path: Path) -> None:
        """Empty feature_actions list produces success with all zeros."""
        from pixl.execution.hooks.sync_hooks import materialize_sync_results_hook

        ctx = self._make_sync_ctx(tmp_path, feature_actions=[])

        mock_db = MagicMock()
        mock_db.events.emit = MagicMock()

        with patch("pixl.execution.hooks.sync_hooks.PixlDB", return_value=mock_db):
            mock_db.initialize = MagicMock()
            result = materialize_sync_results_hook(ctx)

        assert result.success is True
        assert result.data["total_actions"] == 0
        assert result.data["marked_done"] == []

    def test_skips_non_mark_done_actions(self, tmp_path: Path) -> None:
        """Actions that are not 'mark_done' are recorded in skipped list."""
        from pixl.execution.hooks.sync_hooks import materialize_sync_results_hook

        actions = [
            {"feature_id": "feat-2", "action": "already_done"},
            {"feature_id": "feat-3", "action": "no_pr"},
        ]
        ctx = self._make_sync_ctx(tmp_path, feature_actions=actions)

        mock_db = MagicMock()
        mock_db.events.emit = MagicMock()

        with patch("pixl.execution.hooks.sync_hooks.PixlDB", return_value=mock_db):
            mock_db.initialize = MagicMock()
            result = materialize_sync_results_hook(ctx)

        assert result.success is True
        assert set(result.data["skipped"]) == {"feat-2", "feat-3"}
        assert result.data["marked_done"] == []

    def test_skips_feature_already_done(self, tmp_path: Path) -> None:
        """Features already in 'done' status are added to skipped, not re-marked."""
        from pixl.execution.hooks.sync_hooks import materialize_sync_results_hook

        actions = [{"feature_id": "feat-done", "action": "mark_done"}]
        ctx = self._make_sync_ctx(tmp_path, feature_actions=actions)

        mock_db = MagicMock()
        mock_db.backlog.get_feature.return_value = {"id": "feat-done", "status": "done"}
        mock_db.events.emit = MagicMock()

        with patch("pixl.execution.hooks.sync_hooks.PixlDB", return_value=mock_db):
            mock_db.initialize = MagicMock()
            result = materialize_sync_results_hook(ctx)

        assert result.success is True
        assert "feat-done" in result.data["skipped"]
        assert "feat-done" not in result.data["marked_done"]
        mock_db.backlog.update_feature_status.assert_not_called()

    def test_marks_feature_done_with_pr_url(self, tmp_path: Path) -> None:
        """mark_done action on an in-progress feature updates its status."""
        from pixl.execution.hooks.sync_hooks import materialize_sync_results_hook

        actions = [
            {
                "feature_id": "feat-1",
                "action": "mark_done",
                "pr_url": "https://github.com/org/repo/pull/42",
            }
        ]
        ctx = self._make_sync_ctx(tmp_path, feature_actions=actions)

        mock_db = MagicMock()
        mock_db.backlog.get_feature.return_value = {"id": "feat-1", "status": "in_progress"}
        mock_db.events.emit = MagicMock()

        with patch("pixl.execution.hooks.sync_hooks.PixlDB", return_value=mock_db):
            mock_db.initialize = MagicMock()
            result = materialize_sync_results_hook(ctx)

        assert result.success is True
        assert "feat-1" in result.data["marked_done"]
        mock_db.backlog.update_feature_status.assert_called_once()
        call_args = mock_db.backlog.update_feature_status.call_args
        assert call_args.args[0] == "feat-1"
        assert call_args.kwargs["status"] == "done"
        assert "https://github.com" in call_args.kwargs["note"]

    def test_marks_feature_done_with_pr_number(self, tmp_path: Path) -> None:
        """PR number is included in note when pr_url is absent."""
        from pixl.execution.hooks.sync_hooks import materialize_sync_results_hook

        actions = [
            {
                "feature_id": "feat-1",
                "action": "mark_done",
                "pr_number": "99",
            }
        ]
        ctx = self._make_sync_ctx(tmp_path, feature_actions=actions)

        mock_db = MagicMock()
        mock_db.backlog.get_feature.return_value = {"id": "feat-1", "status": "open"}
        mock_db.events.emit = MagicMock()

        with patch("pixl.execution.hooks.sync_hooks.PixlDB", return_value=mock_db):
            mock_db.initialize = MagicMock()
            result = materialize_sync_results_hook(ctx)

        assert result.success is True
        call_args = mock_db.backlog.update_feature_status.call_args
        assert "PR #99" in call_args.kwargs["note"]

    def test_records_error_when_feature_not_found(self, tmp_path: Path) -> None:
        """Missing feature is recorded in errors list, not raised."""
        from pixl.execution.hooks.sync_hooks import materialize_sync_results_hook

        actions = [{"feature_id": "feat-ghost", "action": "mark_done"}]
        ctx = self._make_sync_ctx(tmp_path, feature_actions=actions)

        mock_db = MagicMock()
        mock_db.backlog.get_feature.return_value = None
        mock_db.events.emit = MagicMock()

        with patch("pixl.execution.hooks.sync_hooks.PixlDB", return_value=mock_db):
            mock_db.initialize = MagicMock()
            result = materialize_sync_results_hook(ctx)

        assert result.success is True
        assert any("feat-ghost" in e for e in result.data["errors"])

    def test_skips_malformed_action_items(self, tmp_path: Path) -> None:
        """Non-dict entries in feature_actions are silently skipped."""
        from pixl.execution.hooks.sync_hooks import materialize_sync_results_hook

        actions: list = ["not-a-dict", None, 42]
        ctx = self._make_sync_ctx(tmp_path, feature_actions=actions)

        mock_db = MagicMock()
        mock_db.events.emit = MagicMock()

        with patch("pixl.execution.hooks.sync_hooks.PixlDB", return_value=mock_db):
            mock_db.initialize = MagicMock()
            result = materialize_sync_results_hook(ctx)

        assert result.success is True
        assert result.data["marked_done"] == []

    def test_missing_structured_outputs_returns_empty_success(self, tmp_path: Path) -> None:
        """When scan payload is absent, feature_actions defaults to empty list → success."""
        from pixl.execution.hooks.sync_hooks import materialize_sync_results_hook

        # No structured outputs set at all — hook treats missing payload as empty list
        ctx = self._make_sync_ctx(tmp_path)  # feature_actions=None

        mock_db = MagicMock()
        mock_db.events.emit = MagicMock()

        with patch("pixl.execution.hooks.sync_hooks.PixlDB", return_value=mock_db):
            mock_db.initialize = MagicMock()
            result = materialize_sync_results_hook(ctx)

        # Missing payload → empty feature_actions → no error, no work done
        assert result.success is True
        assert result.data["total_actions"] == 0
        assert result.data["marked_done"] == []

    def test_total_actions_count(self, tmp_path: Path) -> None:
        """total_actions matches the number of items in feature_actions."""
        from pixl.execution.hooks.sync_hooks import materialize_sync_results_hook

        actions = [
            {"feature_id": "feat-1", "action": "mark_done"},
            {"feature_id": "feat-2", "action": "already_done"},
            {"feature_id": "feat-3", "action": "no_pr"},
        ]
        ctx = self._make_sync_ctx(tmp_path, feature_actions=actions)

        mock_db = MagicMock()
        mock_db.backlog.get_feature.side_effect = lambda fid: (
            {"id": fid, "status": "open"} if fid == "feat-1" else None
        )
        mock_db.events.emit = MagicMock()

        with patch("pixl.execution.hooks.sync_hooks.PixlDB", return_value=mock_db):
            mock_db.initialize = MagicMock()
            result = materialize_sync_results_hook(ctx)

        assert result.data["total_actions"] == 3

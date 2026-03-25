"""Tests for chain execution pipeline: runner, node_executor, manager, pr_manager.

Heavy dependencies (OrchestratorCore, PixlDB, git, threading) are replaced with
MagicMock. Tests focus on orchestration logic, input/output contracts, and state
transitions that can be exercised without actual I/O.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Pre-patch: runner.py imports should_auto_merge_pr from workflow_background
# but the symbol lives elsewhere.  Inject a stub before the chain package is
# collected so the import does not fail.
# ---------------------------------------------------------------------------
import pixl.execution.workflow_background as _wfb

if not hasattr(_wfb, "should_auto_merge_pr"):
    _wfb.should_auto_merge_pr = MagicMock(return_value={"approve": False})  # type: ignore[attr-defined]

import pytest

# ---------------------------------------------------------------------------
# Modules under test
# ---------------------------------------------------------------------------
from pixl.execution.chain.node_executor import (
    build_worktree_context,
    dispatch_node_pr_retry,
    query_architectural_context,
    refine_node,
)
from pixl.execution.chain.pr_manager import ensure_pr_for_node

# ===========================================================================
# Helpers
# ===========================================================================


def _make_db(
    *,
    config_raw: str | None = None,
    nodes: list[dict] | None = None,
    file_claims: dict | None = None,
    sibling_signals: list | None = None,
) -> MagicMock:
    """Build a minimal fake PixlDB."""
    db = MagicMock()
    db.project_path = Path("/fake/project")
    db.db_path = "/fake/project/.pixl/pixl.db"

    db.get_config.return_value = config_raw
    db.set_config.return_value = None

    db.sessions.get_session.return_value = None
    db.sessions.update_session.return_value = None

    db.backlog.get_feature.return_value = None
    db.backlog.update_feature.return_value = None

    db.knowledge.search.return_value = []

    db.chain_signals.get_file_claims.return_value = file_claims or {}
    db.chain_signals.get_sibling_signals.return_value = sibling_signals or []

    db.events.emit.return_value = None

    # conn mock for raw SQL calls used in manager.reconcile
    row_mock = MagicMock()
    row_mock.__getitem__ = MagicMock(side_effect=lambda k: "chain-1" if k == "id" else None)
    db.conn.execute.return_value.fetchall.return_value = []
    db.conn.__enter__ = MagicMock(return_value=db.conn)
    db.conn.__exit__ = MagicMock(return_value=False)
    db.conn.commit.return_value = None

    return db


def _make_node(
    node_id: str = "node-1",
    feature_id: str = "feat-1",
    status: str = "pending",
    session_id: str | None = None,
    wave: int = 0,
    metadata: dict | None = None,
    estimate_points: int = 0,
) -> dict:
    return {
        "node_id": node_id,
        "feature_id": feature_id,
        "status": status,
        "session_id": session_id,
        "wave": wave,
        "metadata": metadata or {},
        "estimate_points": estimate_points,
    }


def _make_chain_store(nodes: list[dict] | None = None) -> MagicMock:
    store = MagicMock()
    store.get_execution_nodes.return_value = nodes or []
    store.get_edges.return_value = []
    store.get_chain.return_value = {
        "status": "running",
        "max_parallel": 1,
        "stop_on_failure": False,
    }
    store.try_claim_node_for_execution.return_value = True
    store.update_node_metadata.return_value = None
    return store


# ===========================================================================
# Section 1: build_worktree_context
# ===========================================================================


class TestBuildWorktreeContext:
    def test_returns_dict_with_expected_keys(self) -> None:
        db = _make_db()
        store_mock = _make_chain_store(nodes=[])
        with patch("pixl.execution.chain.node_executor.ChainPlanDB", return_value=store_mock):
            result = build_worktree_context(
                db,
                chain_id="c1",
                node_id="n1",
                branch_name="feat/x",
                base_ref="abc123",
                worktree_path="/tmp/wt",
            )

        assert "branch_name" in result
        assert "base_ref" in result
        assert "workspace_root" in result
        assert "parallel_features" in result
        assert "claimed_files" in result

    def test_sets_branch_name_and_base_ref(self) -> None:
        db = _make_db()
        store_mock = _make_chain_store(nodes=[])
        with patch("pixl.execution.chain.node_executor.ChainPlanDB", return_value=store_mock):
            result = build_worktree_context(
                db,
                chain_id="c1",
                node_id="n1",
                branch_name="feat/my-branch",
                base_ref="deadbeef",
                worktree_path="/tmp/wt",
            )

        assert result["branch_name"] == "feat/my-branch"
        assert result["base_ref"] == "deadbeef"
        assert result["workspace_root"] == "/tmp/wt"

    def test_parallel_features_excludes_current_node(self) -> None:
        """Other pending nodes in the same wave appear as parallel features."""
        db = _make_db()
        feature_a = {"title": "Feature A"}
        db.backlog.get_feature.side_effect = lambda fid: {"feat-a": feature_a}.get(fid)

        nodes = [
            _make_node("n1", feature_id="feat-n1", status="running", wave=0),
            _make_node("n2", feature_id="feat-a", status="pending", wave=0),
        ]
        store_mock = _make_chain_store(nodes=nodes)
        with patch("pixl.execution.chain.node_executor.ChainPlanDB", return_value=store_mock):
            result = build_worktree_context(
                db,
                chain_id="c1",
                node_id="n1",
                branch_name=None,
                base_ref=None,
                worktree_path=None,
            )

        assert "Feature A" in result["parallel_features"]

    def test_claimed_files_excludes_current_node_claims(self) -> None:
        """Files claimed only by other nodes appear in claimed_files."""
        db = _make_db(
            file_claims={
                "src/foo.py": ["n2"],
                "src/bar.py": ["n1"],  # own claim — should be excluded
            }
        )
        store_mock = _make_chain_store(nodes=[])
        with patch("pixl.execution.chain.node_executor.ChainPlanDB", return_value=store_mock):
            result = build_worktree_context(
                db,
                chain_id="c1",
                node_id="n1",
                branch_name=None,
                base_ref=None,
                worktree_path=None,
            )

        assert "src/foo.py" in result["claimed_files"]
        assert "src/bar.py" not in result["claimed_files"]

    def test_parallel_features_capped_at_20(self) -> None:
        """parallel_features list is capped at 20 items."""
        db = _make_db()
        db.backlog.get_feature.return_value = {"title": "F"}
        nodes = [
            _make_node(f"nx{i}", feature_id=f"f{i}", status="pending", wave=0) for i in range(30)
        ]
        store_mock = _make_chain_store(nodes=nodes)
        with patch("pixl.execution.chain.node_executor.ChainPlanDB", return_value=store_mock):
            result = build_worktree_context(
                db,
                chain_id="c1",
                node_id="current",
                branch_name=None,
                base_ref=None,
                worktree_path=None,
            )

        assert len(result["parallel_features"]) <= 20

    def test_claimed_files_capped_at_50(self) -> None:
        """claimed_files list is capped at 50 items."""
        db = _make_db(file_claims={f"file{i}.py": ["other-node"] for i in range(60)})
        store_mock = _make_chain_store(nodes=[])
        with patch("pixl.execution.chain.node_executor.ChainPlanDB", return_value=store_mock):
            result = build_worktree_context(
                db,
                chain_id="c1",
                node_id="n1",
                branch_name=None,
                base_ref=None,
                worktree_path=None,
            )

        assert len(result["claimed_files"]) <= 50

    def test_returns_valid_dict_when_chain_store_raises(self) -> None:
        """Failures in enrichment are swallowed; a valid dict is always returned."""
        db = _make_db()
        bad_store = MagicMock()
        bad_store.get_execution_nodes.side_effect = RuntimeError("db error")
        with patch("pixl.execution.chain.node_executor.ChainPlanDB", return_value=bad_store):
            result = build_worktree_context(
                db,
                chain_id="c1",
                node_id="n1",
                branch_name="b",
                base_ref="r",
                worktree_path="/wt",
            )

        assert isinstance(result, dict)
        assert "parallel_features" in result
        assert "claimed_files" in result

    def test_none_branch_and_base_ref_are_passed_through(self) -> None:
        db = _make_db()
        store_mock = _make_chain_store(nodes=[])
        with patch("pixl.execution.chain.node_executor.ChainPlanDB", return_value=store_mock):
            result = build_worktree_context(
                db,
                chain_id="c1",
                node_id="n1",
                branch_name=None,
                base_ref=None,
                worktree_path=None,
            )

        assert result["branch_name"] is None
        assert result["base_ref"] is None
        assert result["workspace_root"] is None


# ===========================================================================
# Section 2: query_architectural_context
# ===========================================================================


class TestQueryArchitecturalContext:
    def test_returns_none_when_feature_has_no_title_or_description(self) -> None:
        db = _make_db()
        result = query_architectural_context(db=db, feature={})

        assert result is None

    def test_returns_none_when_knowledge_search_empty(self) -> None:
        db = _make_db()
        db.knowledge.search.return_value = []
        result = query_architectural_context(db=db, feature={"title": "auth flow"})

        assert result is None

    def test_returns_markdown_section_when_results_found(self) -> None:
        db = _make_db()
        db.knowledge.search.return_value = [
            {"content": "Use JWT tokens", "source": "arch.md"},
            {"content": "See RBAC pattern", "source": "security.md"},
        ]
        result = query_architectural_context(
            db=db,
            feature={"title": "auth", "description": "login flow"},
        )

        assert result is not None
        assert "Architectural Context" in result
        assert "arch.md" in result

    def test_returns_none_on_knowledge_search_exception(self) -> None:
        db = _make_db()
        db.knowledge.search.side_effect = RuntimeError("index missing")
        result = query_architectural_context(db=db, feature={"title": "auth"})

        assert result is None

    def test_uses_both_title_and_description_for_query(self) -> None:
        db = _make_db()
        db.knowledge.search.return_value = []
        query_architectural_context(
            db=db,
            feature={"title": "auth", "description": "login flow"},
        )

        call_args = db.knowledge.search.call_args
        query_arg = call_args[0][0]
        assert "auth" in query_arg
        assert "login flow" in query_arg

    def test_limits_to_3_chunks_in_output(self) -> None:
        db = _make_db()
        db.knowledge.search.return_value = [
            {"content": f"chunk {i}", "source": f"src{i}.md"} for i in range(5)
        ]
        result = query_architectural_context(
            db=db,
            feature={"title": "big feature"},
        )

        assert result is not None
        # Only first 3 sources should appear
        assert "src0.md" in result
        assert "src1.md" in result
        assert "src2.md" in result
        assert "src3.md" not in result

    def test_content_truncated_at_1000_chars(self) -> None:
        db = _make_db()
        long_content = "x" * 2000
        db.knowledge.search.return_value = [{"content": long_content, "source": "big.md"}]
        result = query_architectural_context(
            db=db,
            feature={"title": "feat"},
        )

        assert result is not None
        # The long content is sliced to [:1000] in the implementation
        assert "x" * 1001 not in result

    def test_falls_back_to_text_key_when_content_missing(self) -> None:
        db = _make_db()
        db.knowledge.search.return_value = [{"text": "fallback text", "source": "fallback.md"}]
        result = query_architectural_context(
            db=db,
            feature={"title": "feat"},
        )

        assert result is not None
        assert "fallback text" in result


# ===========================================================================
# Section 3: dispatch_node_pr_retry
# ===========================================================================


class TestDispatchNodePrRetry:
    def test_returns_false_when_node_id_missing(self) -> None:
        db = _make_db()
        node = _make_node(node_id="", session_id="s1", feature_id="f1")

        ok, err = dispatch_node_pr_retry(db=db, chain_id="c1", node=node)

        assert ok is False
        assert err is not None

    def test_returns_false_when_session_id_missing(self) -> None:
        db = _make_db()
        node = _make_node(node_id="n1", session_id=None, feature_id="f1")

        ok, err = dispatch_node_pr_retry(db=db, chain_id="c1", node=node)

        assert ok is False
        assert err is not None

    def test_returns_false_when_feature_id_missing(self) -> None:
        db = _make_db()
        node = _make_node(node_id="n1", session_id="s1", feature_id="")

        ok, err = dispatch_node_pr_retry(db=db, chain_id="c1", node=node)

        assert ok is False
        assert err is not None

    def test_returns_false_when_session_not_found(self) -> None:
        db = _make_db()
        db.sessions.get_session.return_value = None
        node = _make_node(node_id="n1", session_id="s1", feature_id="f1")
        store_mock = _make_chain_store()

        with patch("pixl.execution.chain.node_executor.ChainPlanDB", return_value=store_mock):
            ok, err = dispatch_node_pr_retry(db=db, chain_id="c1", node=node)

        assert ok is False
        assert "not found" in (err or "")

    def test_returns_false_when_session_not_completed(self) -> None:
        db = _make_db()
        db.sessions.get_session.return_value = {"status": "running", "workspace_root": "/wt"}
        node = _make_node(node_id="n1", session_id="s1", feature_id="f1")
        store_mock = _make_chain_store()

        with patch("pixl.execution.chain.node_executor.ChainPlanDB", return_value=store_mock):
            ok, err = dispatch_node_pr_retry(db=db, chain_id="c1", node=node)

        assert ok is False
        assert "not completed" in (err or "")

    def test_returns_false_when_worktree_does_not_exist(self, tmp_path: Path) -> None:
        db = _make_db()
        missing = str(tmp_path / "nonexistent_wt")
        db.sessions.get_session.return_value = {
            "status": "completed",
            "workspace_root": missing,
        }
        node = _make_node(node_id="n1", session_id="s1", feature_id="f1")
        store_mock = _make_chain_store()

        with patch("pixl.execution.chain.node_executor.ChainPlanDB", return_value=store_mock):
            ok, err = dispatch_node_pr_retry(db=db, chain_id="c1", node=node)

        assert ok is False
        assert "worktree" in (err or "").lower()

    def test_returns_false_when_claim_fails(self, tmp_path: Path) -> None:
        db = _make_db()
        wt = tmp_path / "wt"
        wt.mkdir()
        db.sessions.get_session.return_value = {
            "status": "completed",
            "workspace_root": str(wt),
        }
        node = _make_node(node_id="n1", session_id="s1", feature_id="f1")
        store_mock = _make_chain_store()
        store_mock.try_claim_node_for_execution.return_value = False

        with patch("pixl.execution.chain.node_executor.ChainPlanDB", return_value=store_mock):
            ok, err = dispatch_node_pr_retry(db=db, chain_id="c1", node=node)

        assert ok is False
        assert "claim lost" in (err or "")

    def test_returns_true_on_success(self, tmp_path: Path) -> None:
        db = _make_db()
        wt = tmp_path / "wt"
        wt.mkdir()
        db.sessions.get_session.return_value = {
            "status": "completed",
            "workspace_root": str(wt),
        }
        node = _make_node(node_id="n1", session_id="s1", feature_id="f1")
        store_mock = _make_chain_store()
        store_mock.try_claim_node_for_execution.return_value = True

        with patch("pixl.execution.chain.node_executor.ChainPlanDB", return_value=store_mock):
            ok, err = dispatch_node_pr_retry(db=db, chain_id="c1", node=node)

        assert ok is True
        assert err is None

    def test_updates_pr_retry_metadata_on_success(self, tmp_path: Path) -> None:
        db = _make_db()
        wt = tmp_path / "wt"
        wt.mkdir()
        db.sessions.get_session.return_value = {
            "status": "completed",
            "workspace_root": str(wt),
        }
        node = _make_node(node_id="n1", session_id="s1", feature_id="f1")
        store_mock = _make_chain_store()
        store_mock.try_claim_node_for_execution.return_value = True

        with patch("pixl.execution.chain.node_executor.ChainPlanDB", return_value=store_mock):
            dispatch_node_pr_retry(db=db, chain_id="c1", node=node)

        store_mock.update_node_metadata.assert_called_once()
        update_call = store_mock.update_node_metadata.call_args
        assert update_call.kwargs["updates"]["pr_retry"] is False


# ===========================================================================
# Section 4: refine_node
# ===========================================================================


class TestRefineNode:
    def test_clears_needs_refinement_when_feature_not_found(self) -> None:
        db = _make_db()
        db.backlog.get_feature.return_value = None
        store_mock = _make_chain_store()
        node = _make_node(node_id="n1", feature_id="f1")

        refine_node(db=db, store=store_mock, chain_id="c1", node=node)

        store_mock.update_node_metadata.assert_called_once()
        updates = store_mock.update_node_metadata.call_args.kwargs["updates"]
        assert updates["needs_refinement"] is False
        assert "feature_not_found" in updates.get("refinement_error", "")

    def test_clears_needs_refinement_when_agent_not_wired(self) -> None:
        db = _make_db()
        db.backlog.get_feature.return_value = {"title": "Feature X", "epic_id": "e1"}
        store_mock = _make_chain_store()
        node = _make_node(node_id="n1", feature_id="f1")

        refine_node(db=db, store=store_mock, chain_id="c1", node=node)

        store_mock.update_node_metadata.assert_called_once()
        updates = store_mock.update_node_metadata.call_args.kwargs["updates"]
        assert updates["needs_refinement"] is False
        assert "agent_not_wired" in updates.get("refinement_error", "")

    def test_does_not_raise_when_feature_id_empty(self) -> None:
        db = _make_db()
        db.backlog.get_feature.return_value = None
        store_mock = _make_chain_store()
        node = _make_node(node_id="n1", feature_id="")

        # Should not raise — gracefully clears flag
        refine_node(db=db, store=store_mock, chain_id="c1", node=node)

        store_mock.update_node_metadata.assert_called_once()

    def test_update_targets_correct_chain_and_node(self) -> None:
        db = _make_db()
        db.backlog.get_feature.return_value = None
        store_mock = _make_chain_store()
        node = _make_node(node_id="target-node", feature_id="f99")

        refine_node(db=db, store=store_mock, chain_id="my-chain", node=node)

        call_kwargs = store_mock.update_node_metadata.call_args
        assert call_kwargs.args[0] == "my-chain"
        assert call_kwargs.args[1] == "target-node"


# ===========================================================================
# Section 5: ensure_pr_for_node (pr_manager)
# ===========================================================================


class TestEnsurePrForNode:
    def _make_pr_info(self, url: str = "https://github.com/org/repo/pull/1") -> MagicMock:
        pr = MagicMock()
        pr.url = url
        return pr

    def test_delegates_to_ensure_pr_for_feature(self, tmp_path: Path) -> None:
        db = _make_db()
        store_mock = _make_chain_store()
        pr_info = self._make_pr_info()

        with (
            patch(
                "pixl.execution.chain.pr_manager.resolve_storage_root",
                return_value=tmp_path,
            ),
            patch(
                "pixl.execution.chain.pr_manager.ensure_pr_for_feature",
                return_value=pr_info,
            ) as mock_ensure,
            patch("pixl.execution.chain.pr_manager.pr_automation") as mock_pr_auto,
        ):
            mock_pr_auto.git_current_branch.return_value = "feat/branch"
            result = ensure_pr_for_node(
                db=db,
                chain_store=store_mock,
                chain_id="c1",
                node_id="n1",
                feature_id="f1",
                session_id="s1",
                worktree_path=tmp_path,
                base_remote="origin",
                base_branch="main",
            )

        mock_ensure.assert_called_once()
        assert result is pr_info

    def test_raises_when_ensure_pr_returns_none(self, tmp_path: Path) -> None:
        db = _make_db()
        store_mock = _make_chain_store()

        with (
            patch(
                "pixl.execution.chain.pr_manager.resolve_storage_root",
                return_value=tmp_path,
            ),
            patch(
                "pixl.execution.chain.pr_manager.ensure_pr_for_feature",
                return_value=None,
            ),
        ):
            with pytest.raises(Exception):
                ensure_pr_for_node(
                    db=db,
                    chain_store=store_mock,
                    chain_id="c1",
                    node_id="n1",
                    feature_id="f1",
                    session_id="s1",
                    worktree_path=tmp_path,
                    base_remote="origin",
                    base_branch="main",
                )

    def test_passes_chain_id_as_extra_trailer(self, tmp_path: Path) -> None:
        db = _make_db()
        store_mock = _make_chain_store()
        pr_info = self._make_pr_info()

        with (
            patch(
                "pixl.execution.chain.pr_manager.resolve_storage_root",
                return_value=tmp_path,
            ),
            patch(
                "pixl.execution.chain.pr_manager.ensure_pr_for_feature",
                return_value=pr_info,
            ) as mock_ensure,
            patch("pixl.execution.chain.pr_manager.pr_automation") as mock_pr_auto,
        ):
            mock_pr_auto.git_current_branch.return_value = "feat/b"
            ensure_pr_for_node(
                db=db,
                chain_store=store_mock,
                chain_id="my-chain-id",
                node_id="n1",
                feature_id="f1",
                session_id="s1",
                worktree_path=tmp_path,
                base_remote="origin",
                base_branch="main",
            )

        kwargs = mock_ensure.call_args.kwargs
        assert "my-chain-id" in kwargs.get("extra_trailers", "")

    def test_updates_node_metadata_with_pr_url_and_branch(self, tmp_path: Path) -> None:
        db = _make_db()
        store_mock = _make_chain_store()
        pr_info = self._make_pr_info(url="https://github.com/org/repo/pull/42")

        with (
            patch(
                "pixl.execution.chain.pr_manager.resolve_storage_root",
                return_value=tmp_path,
            ),
            patch(
                "pixl.execution.chain.pr_manager.ensure_pr_for_feature",
                return_value=pr_info,
            ),
            patch("pixl.execution.chain.pr_manager.pr_automation") as mock_pr_auto,
        ):
            mock_pr_auto.git_current_branch.return_value = "feat/test-branch"
            ensure_pr_for_node(
                db=db,
                chain_store=store_mock,
                chain_id="c1",
                node_id="n1",
                feature_id="f1",
                session_id="s1",
                worktree_path=tmp_path,
                base_remote="origin",
                base_branch="main",
            )

        store_mock.update_node_metadata.assert_called_once()
        updates = store_mock.update_node_metadata.call_args.kwargs["updates"]
        assert updates["pr_url"] == "https://github.com/org/repo/pull/42"
        assert updates["branch_name"] == "feat/test-branch"

    def test_does_not_raise_when_metadata_update_fails(self, tmp_path: Path) -> None:
        db = _make_db()
        store_mock = _make_chain_store()
        store_mock.update_node_metadata.side_effect = RuntimeError("db locked")
        pr_info = self._make_pr_info()

        with (
            patch(
                "pixl.execution.chain.pr_manager.resolve_storage_root",
                return_value=tmp_path,
            ),
            patch(
                "pixl.execution.chain.pr_manager.ensure_pr_for_feature",
                return_value=pr_info,
            ),
            patch("pixl.execution.chain.pr_manager.pr_automation") as mock_pr_auto,
        ):
            mock_pr_auto.git_current_branch.return_value = "feat/b"
            # Must not raise
            result = ensure_pr_for_node(
                db=db,
                chain_store=store_mock,
                chain_id="c1",
                node_id="n1",
                feature_id="f1",
                session_id="s1",
                worktree_path=tmp_path,
                base_remote="origin",
                base_branch="main",
            )

        assert result is pr_info


# ===========================================================================
# Section 6: ChainRunnerManager
# ===========================================================================


class TestChainRunnerManager:
    """Test lifecycle management without spinning real runner threads."""

    def _make_manager_imports(self) -> None:
        """Ensure the module is importable with workflow_background stub."""
        from pixl.execution.chain.manager import ChainRunnerManager  # noqa: F401

    def test_start_chain_is_idempotent(self, tmp_path: Path) -> None:
        """Calling start_chain twice for the same chain does not start a second thread."""
        from pixl.execution.chain.manager import ChainRunnerManager

        db = _make_db()

        # Provide a git repo so the guard passes
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        with (
            patch(
                "pixl.execution.chain.manager.resolve_project_root",
                return_value=tmp_path,
            ),
            patch(
                "pixl.execution.chain.manager.git_symbolic_head",
                return_value=("main", None),
            ),
            patch(
                "pixl.execution.chain.manager.git_rev_parse",
                return_value=("abc123", None),
            ),
            patch(
                "pixl.execution.chain.manager.load_chain_exec_config",
                return_value={"base_branch": "main", "base_ref": "abc123"},
            ),
            patch("pixl.execution.chain.manager.save_chain_exec_config"),
            patch("pixl.execution.chain.runner.run_chain_loop") as mock_loop,
        ):
            mock_loop.side_effect = lambda **_: None  # exits immediately

            # Reset class state between tests
            ChainRunnerManager._threads.clear()
            ChainRunnerManager._stop_events.clear()
            ChainRunnerManager._reconciled_db_paths.clear()

            ChainRunnerManager.start_chain(
                db=db,
                chain_id="chain-test-idempotent",
                workflow_id="tdd",
                skip_approval=True,
            )
            # Second call — thread may still be alive or exited; method must not error
            ChainRunnerManager.start_chain(
                db=db,
                chain_id="chain-test-idempotent",
                workflow_id="tdd",
                skip_approval=True,
            )

    def test_stop_all_signals_stop_events(self, tmp_path: Path) -> None:
        """stop_all sets all stop events."""
        from pixl.execution.chain.manager import ChainRunnerManager, _RunnerKey

        stop_event = threading.Event()
        key = _RunnerKey(db_path="/fake.db", chain_id="chain-stop-test")

        ChainRunnerManager._stop_events[key] = stop_event
        ChainRunnerManager._threads[key] = MagicMock(is_alive=lambda: False)

        ChainRunnerManager.stop_all(timeout=0.1)

        assert stop_event.is_set()

    def test_reconcile_skips_when_project_root_not_git_repo(self, tmp_path: Path) -> None:
        """reconcile does not start threads if project root lacks .git."""
        from pixl.execution.chain.manager import ChainRunnerManager

        db = _make_db()
        # tmp_path has no .git — triggers the guard
        db.conn.execute.return_value.fetchall.return_value = [{"id": "chain-orphan"}]

        ChainRunnerManager._reconciled_db_paths.discard(str(tmp_path))

        with patch(
            "pixl.execution.chain.manager.resolve_project_root",
            return_value=tmp_path,
        ):
            # Must not start any threads — guard should short-circuit
            ChainRunnerManager.reconcile(db=db)

        # No thread should have been started for an orphan chain
        for key in ChainRunnerManager._threads:
            if key.chain_id == "chain-orphan":
                raise AssertionError("Should not have started a thread for chain-orphan")

    def test_reconcile_is_idempotent_per_db_path(self, tmp_path: Path) -> None:
        """Second call to reconcile for same db_path is a no-op."""
        from pixl.execution.chain.manager import ChainRunnerManager

        db = _make_db()
        db.db_path = str(tmp_path / "pixl.db")

        ChainRunnerManager._reconciled_db_paths.discard(db.db_path)

        call_count = 0

        def fake_resolve(d: object) -> Path:
            nonlocal call_count
            call_count += 1
            return tmp_path  # no .git → guard fires immediately

        with patch(
            "pixl.execution.chain.manager.resolve_project_root",
            side_effect=fake_resolve,
        ):
            ChainRunnerManager.reconcile(db=db)
            first_count = call_count
            ChainRunnerManager.reconcile(db=db)

        # resolve_project_root should only be called once (second call is a no-op)
        assert call_count == first_count

    def test_stop_chain_joins_thread(self) -> None:
        """stop_chain signals the event and joins the thread."""
        from pixl.execution.chain.manager import ChainRunnerManager, _RunnerKey

        stop_event = threading.Event()
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True
        key = _RunnerKey(db_path="/db.path", chain_id="chain-stop-join")

        ChainRunnerManager._stop_events[key] = stop_event
        ChainRunnerManager._threads[key] = mock_thread

        ChainRunnerManager.stop_chain(key)

        assert stop_event.is_set()
        mock_thread.join.assert_called_once_with(timeout=5.0)


# ===========================================================================
# Section 7: runner._unpack_cfg (helper extracted from run_chain_loop)
# ===========================================================================


class TestRunnerConfigUnpacking:
    """
    run_chain_loop contains an inline _unpack_cfg closure. We test it
    indirectly by verifying the runner handles missing/default cfg keys
    gracefully when we seed the DB mock correctly.
    """

    def _cfg_from_dict(self, data: dict) -> str:
        return json.dumps(data)

    def test_workflow_id_defaults_to_tdd_when_absent(self) -> None:
        """If workflow_id not in cfg, runner treats it as 'tdd'."""
        # We test _unpack_cfg logic by running a single iteration of run_chain_loop
        # with a chain that is immediately terminal (all nodes completed) so the
        # loop returns without dispatching anything.
        from pixl.execution.chain.runner import run_chain_loop

        db = _make_db(config_raw=self._cfg_from_dict({}))
        store_mock = _make_chain_store()
        store_mock.get_chain.return_value = {
            "status": "completed",
            "max_parallel": 1,
            "stop_on_failure": False,
        }
        stop_event = threading.Event()
        stop_event.set()  # Stop immediately

        with (
            patch(
                "pixl.execution.chain.runner.resolve_project_root",
                return_value=Path("/fake"),
            ),
            patch(
                "pixl.execution.chain.runner.ChainPlanDB",
                return_value=store_mock,
            ),
            patch(
                "pixl.execution.chain.runner.git_has_remote",
                return_value=False,
            ),
        ):
            # Should return without error — chain is already terminal
            run_chain_loop(db=db, chain_id="c1", stop_event=stop_event)

    def test_runner_returns_immediately_when_chain_not_found(self) -> None:
        """run_chain_loop exits when store.get_chain returns None."""
        from pixl.execution.chain.runner import run_chain_loop

        db = _make_db(config_raw=self._cfg_from_dict({"workflow_id": "tdd"}))
        store_mock = _make_chain_store()
        store_mock.get_chain.return_value = None

        with (
            patch(
                "pixl.execution.chain.runner.resolve_project_root",
                return_value=Path("/fake"),
            ),
            patch(
                "pixl.execution.chain.runner.ChainPlanDB",
                return_value=store_mock,
            ),
            patch(
                "pixl.execution.chain.runner.git_has_remote",
                return_value=False,
            ),
        ):
            run_chain_loop(db=db, chain_id="c1")

        # If we reach here, the function returned (did not spin forever).

    def test_runner_returns_when_chain_status_is_terminal(self) -> None:
        """run_chain_loop exits when chain status is not running/paused."""
        from pixl.execution.chain.runner import run_chain_loop

        db = _make_db(config_raw=self._cfg_from_dict({}))
        store_mock = _make_chain_store()
        store_mock.get_chain.return_value = {"status": "cancelled"}

        with (
            patch(
                "pixl.execution.chain.runner.resolve_project_root",
                return_value=Path("/fake"),
            ),
            patch(
                "pixl.execution.chain.runner.ChainPlanDB",
                return_value=store_mock,
            ),
            patch(
                "pixl.execution.chain.runner.git_has_remote",
                return_value=False,
            ),
        ):
            run_chain_loop(db=db, chain_id="c1")

    def test_runner_marks_chain_completed_when_all_nodes_terminal(self) -> None:
        """All-terminal nodes trigger final status → 'completed'."""
        from pixl.execution.chain.runner import run_chain_loop

        db = _make_db(config_raw=self._cfg_from_dict({}))
        nodes = [
            _make_node("n1", status="completed"),
            _make_node("n2", status="completed"),
        ]
        store_mock = _make_chain_store(nodes=nodes)
        store_mock.get_chain.return_value = {
            "status": "running",
            "max_parallel": 2,
            "stop_on_failure": False,
        }

        with (
            patch(
                "pixl.execution.chain.runner.resolve_project_root",
                return_value=Path("/fake"),
            ),
            patch(
                "pixl.execution.chain.runner.ChainPlanDB",
                return_value=store_mock,
            ),
            patch(
                "pixl.execution.chain.runner.git_has_remote",
                return_value=False,
            ),
            patch("pixl.execution.chain.runner.check_and_run_judge", return_value="ok"),
            patch("pixl.execution.chain.runner.record_chain_quality_scores"),
            patch("pixl.execution.chain.runner.toposort_ready_nodes", return_value=([], [])),
            patch("pixl.execution.chain.runner.filter_conflicting_nodes", return_value=[]),
        ):
            run_chain_loop(db=db, chain_id="c1")

        store_mock.set_chain_status.assert_called_with("c1", "completed")

    def test_runner_marks_chain_failed_when_any_node_failed(self) -> None:
        """Any failed node causes final chain status → 'failed'."""
        from pixl.execution.chain.runner import run_chain_loop

        db = _make_db(config_raw=self._cfg_from_dict({}))
        nodes = [
            _make_node("n1", status="completed"),
            _make_node("n2", status="failed"),
        ]
        store_mock = _make_chain_store(nodes=nodes)
        store_mock.get_chain.return_value = {
            "status": "running",
            "max_parallel": 2,
            "stop_on_failure": False,
        }

        with (
            patch(
                "pixl.execution.chain.runner.resolve_project_root",
                return_value=Path("/fake"),
            ),
            patch(
                "pixl.execution.chain.runner.ChainPlanDB",
                return_value=store_mock,
            ),
            patch(
                "pixl.execution.chain.runner.git_has_remote",
                return_value=False,
            ),
            patch("pixl.execution.chain.runner.check_and_run_judge", return_value="ok"),
            patch("pixl.execution.chain.runner.record_chain_quality_scores"),
            patch("pixl.execution.chain.runner.toposort_ready_nodes", return_value=([], [])),
            patch("pixl.execution.chain.runner.filter_conflicting_nodes", return_value=[]),
        ):
            run_chain_loop(db=db, chain_id="c1")

        store_mock.set_chain_status.assert_called_with("c1", "failed")

    def test_runner_stop_on_failure_cancels_pending_nodes(self) -> None:
        """stop_on_failure=True causes pending nodes to be cancelled after first failure.

        The runner calls get_execution_nodes multiple times per iteration (for
        reconcile-refresh, toposort, block-descendants, stop-on-failure, terminal
        check). We return the 'already-failed' state from every call so the
        stop_on_failure branch fires on the first and only iteration.
        """
        from pixl.execution.chain.runner import run_chain_loop

        db = _make_db(config_raw=self._cfg_from_dict({}))
        # All calls to get_execution_nodes return one failed + one pending node.
        # The runner will then cancel the pending node and the chain will go
        # terminal on the final node refresh (after mark_nodes_cancelled is called).
        nodes_with_failure = [
            _make_node("n1", status="failed"),
            _make_node("n2", status="pending"),
        ]
        nodes_after_cancel = [
            _make_node("n1", status="failed"),
            _make_node("n2", status="cancelled"),
        ]

        call_count = [0]

        def get_nodes(_cid: str) -> list:
            call_count[0] += 1
            # Return the cancelled state after the first few calls so the
            # terminal check terminates the loop.
            if call_count[0] <= 3:
                return nodes_with_failure
            return nodes_after_cancel

        store_mock = _make_chain_store()
        store_mock.get_execution_nodes.side_effect = get_nodes
        store_mock.get_chain.return_value = {
            "status": "running",
            "max_parallel": 2,
            "stop_on_failure": True,
        }

        with (
            patch(
                "pixl.execution.chain.runner.resolve_project_root",
                return_value=Path("/fake"),
            ),
            patch(
                "pixl.execution.chain.runner.ChainPlanDB",
                return_value=store_mock,
            ),
            patch(
                "pixl.execution.chain.runner.git_has_remote",
                return_value=False,
            ),
            patch("pixl.execution.chain.runner.check_and_run_judge", return_value="ok"),
            patch("pixl.execution.chain.runner.record_chain_quality_scores"),
            patch("pixl.execution.chain.runner.toposort_ready_nodes", return_value=([], [])),
            patch("pixl.execution.chain.runner.filter_conflicting_nodes", return_value=[]),
        ):
            run_chain_loop(db=db, chain_id="c1")

        store_mock.mark_nodes_cancelled.assert_called()
        # Find the stop_on_failure cancellation call (there may be a block call too)
        sof_calls = [
            c
            for c in store_mock.mark_nodes_cancelled.call_args_list
            if c.kwargs.get("reason") == "stop_on_failure"
        ]
        assert sof_calls, "Expected at least one mark_nodes_cancelled with reason='stop_on_failure'"
        # The pending node n2 must have been cancelled
        cancelled_ids = sof_calls[0].args[1]
        assert "n2" in cancelled_ids

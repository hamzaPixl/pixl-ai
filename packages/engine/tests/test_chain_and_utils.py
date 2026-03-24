"""Tests for chain topology, conflict detection, budget, and utility modules.

No DB I/O — all DB/external dependencies are replaced with MagicMock.
Focuses on pure algorithmic logic.
"""

from __future__ import annotations

import json
import logging
import threading
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Pre-patch: chain/runner.py imports should_auto_merge_pr from
# workflow_background but the function actually lives in autonomy.py.
# Inject it as a stub before the chain package __init__ is executed so that
# the import chain does not fail at collection time.
# ---------------------------------------------------------------------------
import pixl.execution.workflow_background as _wfb
import pytest

if not hasattr(_wfb, "should_auto_merge_pr"):
    _wfb.should_auto_merge_pr = MagicMock(return_value=False)  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# Modules under test — import leaf modules after the stub is in place.
# ---------------------------------------------------------------------------
from pixl.execution.budget import get_budget, record_cost, set_budget
from pixl.execution.chain.config import (  # noqa: E402
    _chain_exec_key,
    load_chain_exec_config,
    patch_chain_exec_config,
    save_chain_exec_config,
)
from pixl.execution.chain.conflict_detector import (  # noqa: E402
    emit_file_claims,
    extract_and_persist_signals,
    filter_conflicting_nodes,
    refresh_file_claims_from_session,
)
from pixl.execution.chain.topology import (  # noqa: E402
    descendants,
    detect_completed_wave,
    toposort_ready_nodes,
)
from pixl.models.budget import BudgetConfig, check_budget
from pixl.utils.thread_hooks import install_thread_excepthook
from pixl.utils.tokens import estimate_tokens
from pixl.utils.versioning import (
    SemanticVersion,
    VersioningError,
    compare_versions,
    get_latest_version,
    get_next_version,
    is_version_conflict,
    parse_version,
    suggest_next_version,
    tuple_to_version,
    validate_version,
    version_to_tuple,
)

# ===========================================================================
# Section 1: topology.py — toposort_ready_nodes
# ===========================================================================


def _node(node_id: str, status: str, wave: int = 0, parallel_group: int = 0) -> dict:
    return {
        "node_id": node_id,
        "status": status,
        "wave": wave,
        "parallel_group": parallel_group,
    }


class TestToposortReadyNodesPendingNoPrereqs:
    def test_returns_pending_node_with_no_predecessors_as_runnable(self) -> None:
        nodes = [_node("a", "pending")]
        runnable, blocked = toposort_ready_nodes(nodes=nodes, edges=[])

        assert len(runnable) == 1
        assert runnable[0]["node_id"] == "a"
        assert blocked == []

    def test_returns_empty_when_no_nodes(self) -> None:
        runnable, blocked = toposort_ready_nodes(nodes=[], edges=[])

        assert runnable == []
        assert blocked == []

    def test_skips_non_pending_nodes(self) -> None:
        nodes = [_node("a", "completed"), _node("b", "running"), _node("c", "failed")]
        runnable, blocked = toposort_ready_nodes(nodes=nodes, edges=[])

        assert runnable == []
        assert blocked == []

    def test_returns_all_pending_nodes_when_no_edges(self) -> None:
        nodes = [_node("a", "pending"), _node("b", "pending")]
        runnable, blocked = toposort_ready_nodes(nodes=nodes, edges=[])

        node_ids = {n["node_id"] for n in runnable}
        assert node_ids == {"a", "b"}
        assert blocked == []


class TestToposortReadyNodesWithEdges:
    def test_node_is_runnable_when_all_predecessors_completed(self) -> None:
        nodes = [_node("a", "completed"), _node("b", "pending")]
        edges = [{"from": "a", "to": "b"}]

        runnable, blocked = toposort_ready_nodes(nodes=nodes, edges=edges)

        assert len(runnable) == 1
        assert runnable[0]["node_id"] == "b"

    def test_node_is_not_runnable_when_predecessor_still_running(self) -> None:
        nodes = [_node("a", "running"), _node("b", "pending")]
        edges = [{"from": "a", "to": "b"}]

        runnable, blocked = toposort_ready_nodes(nodes=nodes, edges=edges)

        assert runnable == []
        assert blocked == []

    def test_node_is_blocked_when_predecessor_failed(self) -> None:
        nodes = [_node("a", "failed"), _node("b", "pending")]
        edges = [{"from": "a", "to": "b"}]

        runnable, blocked = toposort_ready_nodes(nodes=nodes, edges=edges)

        assert runnable == []
        assert "b" in blocked

    def test_node_is_blocked_when_predecessor_cancelled(self) -> None:
        nodes = [_node("a", "cancelled"), _node("b", "pending")]
        edges = [{"from": "a", "to": "b"}]

        runnable, blocked = toposort_ready_nodes(nodes=nodes, edges=edges)

        assert "b" in blocked

    def test_node_is_blocked_when_predecessor_is_blocked(self) -> None:
        nodes = [_node("a", "blocked"), _node("b", "pending")]
        edges = [{"from": "a", "to": "b"}]

        runnable, blocked = toposort_ready_nodes(nodes=nodes, edges=edges)

        assert "b" in blocked

    def test_node_is_runnable_when_predecessor_is_refined(self) -> None:
        nodes = [_node("a", "refined"), _node("b", "pending")]
        edges = [{"from": "a", "to": "b"}]

        runnable, blocked = toposort_ready_nodes(nodes=nodes, edges=edges)

        assert len(runnable) == 1
        assert runnable[0]["node_id"] == "b"

    def test_node_not_runnable_when_only_one_of_two_predecessors_completed(self) -> None:
        nodes = [_node("a", "completed"), _node("b", "running"), _node("c", "pending")]
        edges = [{"from": "a", "to": "c"}, {"from": "b", "to": "c"}]

        runnable, blocked = toposort_ready_nodes(nodes=nodes, edges=edges)

        assert runnable == []
        assert blocked == []  # b is running, not terminal-failure → c is just waiting

    def test_edges_with_unknown_nodes_are_ignored(self) -> None:
        nodes = [_node("a", "pending")]
        edges = [{"from": "ghost", "to": "a"}]

        runnable, blocked = toposort_ready_nodes(nodes=nodes, edges=edges)

        # "ghost" not in by_id, so preds[a] stays empty — "a" should be runnable
        assert len(runnable) == 1


class TestToposortReadyNodesOrdering:
    def test_runnable_nodes_sorted_by_wave_then_parallel_group_then_id(self) -> None:
        nodes = [
            _node("c", "pending", wave=1, parallel_group=0),
            _node("a", "pending", wave=0, parallel_group=0),
            _node("b", "pending", wave=0, parallel_group=1),
        ]
        runnable, _ = toposort_ready_nodes(nodes=nodes, edges=[])

        ids = [n["node_id"] for n in runnable]
        assert ids == ["a", "b", "c"]


# ===========================================================================
# Section 2: topology.py — descendants
# ===========================================================================


class TestDescendants:
    def test_returns_empty_when_no_edges(self) -> None:
        result = descendants(start_node_id="a", edges=[])

        assert result == []

    def test_returns_direct_children(self) -> None:
        edges = [{"from": "a", "to": "b"}, {"from": "a", "to": "c"}]

        result = descendants(start_node_id="a", edges=edges)

        assert sorted(result) == ["b", "c"]

    def test_returns_all_transitive_descendants(self) -> None:
        edges = [{"from": "a", "to": "b"}, {"from": "b", "to": "c"}]

        result = descendants(start_node_id="a", edges=edges)

        assert "b" in result
        assert "c" in result

    def test_does_not_include_start_node_itself(self) -> None:
        edges = [{"from": "a", "to": "b"}]

        result = descendants(start_node_id="a", edges=edges)

        assert "a" not in result

    def test_handles_diamond_shaped_dag(self) -> None:
        # a → b, a → c, b → d, c → d
        edges = [
            {"from": "a", "to": "b"},
            {"from": "a", "to": "c"},
            {"from": "b", "to": "d"},
            {"from": "c", "to": "d"},
        ]

        result = descendants(start_node_id="a", edges=edges)

        assert sorted(result) == ["b", "c", "d"]

    def test_ignores_edges_with_empty_endpoints(self) -> None:
        edges = [{"from": "", "to": "b"}, {"from": "a", "to": ""}]

        result = descendants(start_node_id="a", edges=edges)

        assert result == []

    def test_result_is_sorted(self) -> None:
        edges = [{"from": "root", "to": "z"}, {"from": "root", "to": "a"}]

        result = descendants(start_node_id="root", edges=edges)

        assert result == sorted(result)


# ===========================================================================
# Section 3: topology.py — detect_completed_wave
# ===========================================================================


class TestDetectCompletedWave:
    def test_returns_none_when_no_nodes(self) -> None:
        result = detect_completed_wave([])

        assert result is None

    def test_returns_none_when_first_wave_not_completed(self) -> None:
        nodes = [_node("a", "running", wave=0), _node("b", "pending", wave=1)]

        result = detect_completed_wave(nodes)

        assert result is None

    def test_returns_wave_number_when_wave_complete_and_next_has_pending(self) -> None:
        nodes = [
            _node("a", "completed", wave=0),
            _node("b", "pending", wave=1),
        ]

        result = detect_completed_wave(nodes)

        assert result == 0

    def test_returns_none_when_next_wave_has_no_pending_nodes(self) -> None:
        nodes = [
            _node("a", "completed", wave=0),
            _node("b", "completed", wave=1),
        ]

        result = detect_completed_wave(nodes)

        assert result is None

    def test_detects_completed_wave_with_mixed_terminal_states(self) -> None:
        # Wave 0 has completed + failed nodes — both are terminal
        nodes = [
            _node("a", "completed", wave=0),
            _node("b", "failed", wave=0),
            _node("c", "pending", wave=1),
        ]

        result = detect_completed_wave(nodes)

        assert result == 0

    def test_returns_none_when_only_one_wave(self) -> None:
        nodes = [_node("a", "completed", wave=0)]

        result = detect_completed_wave(nodes)

        assert result is None

    def test_detects_completed_middle_wave(self) -> None:
        nodes = [
            _node("a", "completed", wave=0),
            _node("b", "completed", wave=1),
            _node("c", "pending", wave=2),
        ]

        result = detect_completed_wave(nodes)

        # Wave 0 is complete with next wave 1 also complete, so wave 0 does not qualify
        # (wave 1's nodes are not pending). Wave 1 is complete with next wave 2 pending → returns 1
        assert result == 1


# ===========================================================================
# Section 4: config.py — chain exec config helpers
# ===========================================================================


class TestChainExecKey:
    def test_prefixes_chain_id_with_namespace(self) -> None:
        key = _chain_exec_key("abc-123")

        assert key == "chain_exec:abc-123"


class TestLoadChainExecConfig:
    def test_returns_empty_dict_when_no_config_stored(self) -> None:
        db = MagicMock()
        db.get_config.return_value = None

        result = load_chain_exec_config(db, "chain-1")

        assert result == {}

    def test_returns_empty_dict_when_value_is_empty_string(self) -> None:
        db = MagicMock()
        db.get_config.return_value = ""

        result = load_chain_exec_config(db, "chain-1")

        assert result == {}

    def test_parses_valid_json_config(self) -> None:
        db = MagicMock()
        db.get_config.return_value = json.dumps({"workflow_id": "wf-1"})

        result = load_chain_exec_config(db, "chain-1")

        assert result["workflow_id"] == "wf-1"

    def test_returns_empty_dict_for_malformed_json(self) -> None:
        db = MagicMock()
        db.get_config.return_value = "not valid json {"

        result = load_chain_exec_config(db, "chain-1")

        assert result == {}

    def test_returns_empty_dict_when_json_is_list_not_dict(self) -> None:
        db = MagicMock()
        db.get_config.return_value = json.dumps(["a", "b"])

        result = load_chain_exec_config(db, "chain-1")

        assert result == {}


class TestSaveChainExecConfig:
    def test_calls_set_config_with_serialized_payload(self) -> None:
        db = MagicMock()

        save_chain_exec_config(
            db,
            "chain-1",
            workflow_id="wf-99",
            skip_approval=True,
        )

        db.set_config.assert_called_once()
        call_args = db.set_config.call_args
        key = call_args[0][0]
        raw_value = call_args[0][1]
        payload = json.loads(raw_value)

        assert key == "chain_exec:chain-1"
        assert payload["workflow_id"] == "wf-99"
        assert payload["skip_approval"] is True

    def test_defaults_base_remote_to_origin(self) -> None:
        db = MagicMock()

        save_chain_exec_config(db, "c", workflow_id="w", skip_approval=False)

        raw = db.set_config.call_args[0][1]
        payload = json.loads(raw)
        assert payload["base_remote"] == "origin"

    def test_merge_method_defaults_to_squash(self) -> None:
        db = MagicMock()

        save_chain_exec_config(db, "c", workflow_id="w", skip_approval=False)

        raw = db.set_config.call_args[0][1]
        payload = json.loads(raw)
        assert payload["merge_method"] == "squash"

    def test_includes_updated_at_timestamp(self) -> None:
        db = MagicMock()

        save_chain_exec_config(db, "c", workflow_id="w", skip_approval=False)

        raw = db.set_config.call_args[0][1]
        payload = json.loads(raw)
        assert "updated_at" in payload


class TestPatchChainExecConfig:
    def test_merges_updates_into_existing_config(self) -> None:
        db = MagicMock()
        existing = {"workflow_id": "wf-1", "skip_approval": False}
        db.get_config.return_value = json.dumps(existing)

        patch_chain_exec_config(db, "chain-1", updates={"skip_approval": True})

        raw = db.set_config.call_args[0][1]
        payload = json.loads(raw)
        assert payload["workflow_id"] == "wf-1"
        assert payload["skip_approval"] is True

    def test_patch_with_empty_updates_does_not_remove_existing_keys(self) -> None:
        db = MagicMock()
        db.get_config.return_value = json.dumps({"workflow_id": "wf-1"})

        patch_chain_exec_config(db, "chain-1", updates={})

        raw = db.set_config.call_args[0][1]
        payload = json.loads(raw)
        assert payload["workflow_id"] == "wf-1"


# ===========================================================================
# Section 5: conflict_detector.py — filter_conflicting_nodes
# ===========================================================================


def _candidate(node_id: str, files: list[str]) -> dict:
    return {
        "node_id": node_id,
        "metadata": {"work_scope": {"files": files}},
    }


class TestFilterConflictingNodes:
    def test_returns_single_candidate_unchanged(self) -> None:
        db = MagicMock()
        db.chain_signals.get_file_claims.return_value = {}

        result = filter_conflicting_nodes(db, "chain-1", [_candidate("a", ["x.py"])])

        assert len(result) == 1
        assert result[0]["node_id"] == "a"

    def test_returns_empty_list_as_is_for_zero_candidates(self) -> None:
        db = MagicMock()
        db.chain_signals.get_file_claims.return_value = {}

        result = filter_conflicting_nodes(db, "chain-1", [])

        assert result == []

    def test_dispatches_both_candidates_when_no_file_overlap(self) -> None:
        db = MagicMock()
        db.chain_signals.get_file_claims.return_value = {}

        candidates = [_candidate("a", ["a.py"]), _candidate("b", ["b.py"])]
        result = filter_conflicting_nodes(db, "chain-1", candidates)

        node_ids = {n["node_id"] for n in result}
        assert node_ids == {"a", "b"}

    def test_defers_second_candidate_when_files_overlap(self) -> None:
        db = MagicMock()
        db.chain_signals.get_file_claims.return_value = {}

        candidates = [_candidate("a", ["shared.py"]), _candidate("b", ["shared.py"])]
        result = filter_conflicting_nodes(db, "chain-1", candidates)

        assert len(result) == 1
        assert result[0]["node_id"] == "a"

    def test_defers_candidate_that_overlaps_with_running_file(self) -> None:
        db = MagicMock()
        db.chain_signals.get_file_claims.return_value = {"running.py": ["node-running"]}

        candidates = [_candidate("new-node", ["running.py"])]
        result = filter_conflicting_nodes(db, "chain-1", candidates)

        # Only one candidate → short-circuit returns it regardless
        assert len(result) == 1

    def test_defers_second_candidate_when_it_overlaps_with_already_dispatched(self) -> None:
        db = MagicMock()
        db.chain_signals.get_file_claims.return_value = {}

        # a takes shared.py; b also wants shared.py
        candidates = [
            _candidate("a", ["shared.py", "other.py"]),
            _candidate("b", ["shared.py"]),
        ]
        result = filter_conflicting_nodes(db, "chain-1", candidates)

        node_ids = {n["node_id"] for n in result}
        assert "a" in node_ids
        assert "b" not in node_ids

    def test_falls_back_to_first_candidate_when_all_conflict(self) -> None:
        db = MagicMock()
        db.chain_signals.get_file_claims.return_value = {}

        candidates = [_candidate("a", ["f.py"]), _candidate("b", ["f.py"])]
        result = filter_conflicting_nodes(db, "chain-1", candidates)

        # All conflicted, but fallback returns first
        assert result[0]["node_id"] == "a"

    def test_nodes_without_file_scope_do_not_conflict(self) -> None:
        db = MagicMock()
        db.chain_signals.get_file_claims.return_value = {}

        candidates = [
            {"node_id": "a", "metadata": {}},
            {"node_id": "b", "metadata": {}},
        ]
        result = filter_conflicting_nodes(db, "chain-1", candidates)

        node_ids = {n["node_id"] for n in result}
        assert node_ids == {"a", "b"}


# ===========================================================================
# Section 6: conflict_detector.py — emit_file_claims
# ===========================================================================


class TestEmitFileClaims:
    def test_emits_file_claim_signal_for_listed_files(self) -> None:
        db = MagicMock()
        feature = {"metadata": {"work_scope": {"files": ["a.py", "b.py"]}}}

        emit_file_claims(db, "chain-1", "node-1", feature)

        db.chain_signals.emit_signal.assert_called_once()
        call_args = db.chain_signals.emit_signal.call_args
        assert call_args[0][2] == "file_claim"
        payload = call_args[0][3]
        assert "a.py" in payload["files"]
        assert "b.py" in payload["files"]

    def test_does_not_emit_when_no_files(self) -> None:
        db = MagicMock()
        feature = {"metadata": {"work_scope": {}}}

        emit_file_claims(db, "chain-1", "node-1", feature)

        db.chain_signals.emit_signal.assert_not_called()

    def test_handles_feature_without_metadata_gracefully(self) -> None:
        db = MagicMock()
        feature: dict = {}

        # Should not raise
        emit_file_claims(db, "chain-1", "node-1", feature)

    def test_does_not_raise_when_emit_signal_fails(self) -> None:
        db = MagicMock()
        db.chain_signals.emit_signal.side_effect = RuntimeError("signal failure")
        feature = {"metadata": {"work_scope": {"files": ["a.py"]}}}

        # Should not raise
        emit_file_claims(db, "chain-1", "node-1", feature)


# ===========================================================================
# Section 7: conflict_detector.py — extract_and_persist_signals
# ===========================================================================


class TestExtractAndPersistSignals:
    def _make_baton(self, files: list[str], current_state: str = "Done") -> str:
        return json.dumps({
            "work_scope": {"files_modified": files},
            "current_state": current_state,
        })

    def test_emits_file_modified_and_status_update_signals(self) -> None:
        db = MagicMock()
        db.sessions.get_session.return_value = {"baton": self._make_baton(["x.py"])}

        extract_and_persist_signals(db, "chain-1", "node-1", "session-1")

        assert db.chain_signals.emit_signal.call_count == 2
        signal_types = [c[0][2] for c in db.chain_signals.emit_signal.call_args_list]
        assert "file_modified" in signal_types
        assert "status_update" in signal_types

    def test_does_not_emit_when_session_not_found(self) -> None:
        db = MagicMock()
        db.sessions.get_session.return_value = None

        extract_and_persist_signals(db, "chain-1", "node-1", "session-1")

        db.chain_signals.emit_signal.assert_not_called()

    def test_does_not_emit_when_baton_is_absent(self) -> None:
        db = MagicMock()
        db.sessions.get_session.return_value = {"baton": None}

        extract_and_persist_signals(db, "chain-1", "node-1", "session-1")

        db.chain_signals.emit_signal.assert_not_called()

    def test_handles_dict_baton_directly(self) -> None:
        db = MagicMock()
        db.sessions.get_session.return_value = {
            "baton": {"work_scope": {"files_modified": ["y.py"]}, "current_state": "ok"}
        }

        extract_and_persist_signals(db, "chain-1", "node-1", "session-1")

        assert db.chain_signals.emit_signal.call_count == 2

    def test_does_not_raise_when_session_lookup_fails(self) -> None:
        db = MagicMock()
        db.sessions.get_session.side_effect = RuntimeError("db error")

        # Should not raise
        extract_and_persist_signals(db, "chain-1", "node-1", "session-1")


# ===========================================================================
# Section 8: conflict_detector.py — refresh_file_claims_from_session
# ===========================================================================


class TestRefreshFileClaimsFromSession:
    def test_emits_file_claim_for_work_scope_as_list(self) -> None:
        db = MagicMock()
        baton = json.dumps({"work_scope": ["a.py", "b.py"]})
        db.sessions.get_session.return_value = {"baton": baton}

        refresh_file_claims_from_session(db, "chain-1", "node-1", "session-1")

        db.chain_signals.emit_signal.assert_called_once()
        payload = db.chain_signals.emit_signal.call_args[0][3]
        assert "a.py" in payload["files"]
        assert payload["source"] == "baton_refresh"

    def test_emits_file_claim_for_work_scope_as_dict_with_files_key(self) -> None:
        db = MagicMock()
        baton = json.dumps({"work_scope": {"files": ["c.py"]}})
        db.sessions.get_session.return_value = {"baton": baton}

        refresh_file_claims_from_session(db, "chain-1", "node-1", "session-1")

        db.chain_signals.emit_signal.assert_called_once()
        payload = db.chain_signals.emit_signal.call_args[0][3]
        assert "c.py" in payload["files"]

    def test_does_not_emit_when_work_scope_is_empty(self) -> None:
        db = MagicMock()
        db.sessions.get_session.return_value = {"baton": json.dumps({"work_scope": []})}

        refresh_file_claims_from_session(db, "chain-1", "node-1", "session-1")

        db.chain_signals.emit_signal.assert_not_called()

    def test_does_not_emit_when_session_missing(self) -> None:
        db = MagicMock()
        db.sessions.get_session.return_value = None

        refresh_file_claims_from_session(db, "chain-1", "node-1", "session-1")

        db.chain_signals.emit_signal.assert_not_called()


# ===========================================================================
# Section 9: budget.py — BudgetConfig model (pure)
# ===========================================================================


class TestBudgetConfig:
    def test_remaining_usd_is_infinity_when_no_limit_set(self) -> None:
        cfg = BudgetConfig(monthly_usd=0.0, spent_monthly_usd=10.0)

        assert cfg.remaining_usd == float("inf")

    def test_remaining_usd_computed_correctly(self) -> None:
        cfg = BudgetConfig(monthly_usd=100.0, spent_monthly_usd=30.0)

        assert cfg.remaining_usd == pytest.approx(70.0)

    def test_remaining_usd_floors_at_zero_when_over_budget(self) -> None:
        cfg = BudgetConfig(monthly_usd=50.0, spent_monthly_usd=80.0)

        assert cfg.remaining_usd == 0.0

    def test_is_exceeded_false_when_no_limit(self) -> None:
        cfg = BudgetConfig(monthly_usd=0.0, spent_monthly_usd=999.0)

        assert cfg.is_exceeded is False

    def test_is_exceeded_false_when_under_budget(self) -> None:
        cfg = BudgetConfig(monthly_usd=100.0, spent_monthly_usd=99.99)

        assert cfg.is_exceeded is False

    def test_is_exceeded_true_when_at_limit(self) -> None:
        cfg = BudgetConfig(monthly_usd=100.0, spent_monthly_usd=100.0)

        assert cfg.is_exceeded is True

    def test_is_exceeded_true_when_over_limit(self) -> None:
        cfg = BudgetConfig(monthly_usd=100.0, spent_monthly_usd=101.0)

        assert cfg.is_exceeded is True


class TestCheckBudget:
    def test_returns_true_when_no_budget_set(self) -> None:
        cfg = BudgetConfig(monthly_usd=0.0, spent_monthly_usd=500.0)

        assert check_budget(cfg) is True

    def test_returns_true_when_cost_fits_within_budget(self) -> None:
        cfg = BudgetConfig(monthly_usd=100.0, spent_monthly_usd=50.0)

        assert check_budget(cfg, additional_cost=10.0) is True

    def test_returns_false_when_cost_exceeds_budget(self) -> None:
        cfg = BudgetConfig(monthly_usd=100.0, spent_monthly_usd=95.0)

        assert check_budget(cfg, additional_cost=10.0) is False

    def test_returns_false_at_exact_boundary(self) -> None:
        cfg = BudgetConfig(monthly_usd=100.0, spent_monthly_usd=90.0)

        # 90 + 10 = 100, which is NOT < 100
        assert check_budget(cfg, additional_cost=10.0) is False


# ===========================================================================
# Section 10: budget.py — get_budget, set_budget, record_cost
# ===========================================================================


class TestGetBudget:
    def test_returns_budget_config_from_db(self) -> None:
        db = MagicMock()
        db.get_config.return_value = "50.0"
        db.cost_events.total_cost_for_month.return_value = 20.0

        result = get_budget(db)

        assert result.monthly_usd == pytest.approx(50.0)
        assert result.spent_monthly_usd == pytest.approx(20.0)

    def test_defaults_monthly_usd_to_zero_when_not_configured(self) -> None:
        db = MagicMock()
        db.get_config.return_value = "0"
        db.cost_events.total_cost_for_month.return_value = 0.0

        result = get_budget(db)

        assert result.monthly_usd == pytest.approx(0.0)


class TestSetBudget:
    def test_stores_budget_as_string_in_config(self) -> None:
        db = MagicMock()

        set_budget(db, 75.5)

        db.set_config.assert_called_once_with("budget:monthly_usd", "75.5")


class TestRecordCost:
    def _make_db(self, monthly_usd: float = 0.0, spent: float = 0.0) -> MagicMock:
        db = MagicMock()
        db.get_config.return_value = str(monthly_usd)
        db.cost_events.total_cost_for_month.return_value = spent
        return db

    def test_records_cost_event_and_returns_true_when_within_budget(self) -> None:
        db = self._make_db(monthly_usd=100.0, spent=10.0)

        result = record_cost(db, "session-1", cost_usd=5.0)

        assert result is True
        db.cost_events.record.assert_called_once()

    def test_returns_false_and_pauses_session_when_budget_exceeded(self) -> None:
        db = self._make_db(monthly_usd=100.0, spent=105.0)

        result = record_cost(db, "session-1", cost_usd=1.0)

        assert result is False
        db.sessions.update_session.assert_called_once()
        call_kwargs = db.sessions.update_session.call_args[1]
        assert call_kwargs.get("pause_reason") == "budget_exceeded"

    def test_returns_true_when_no_budget_configured(self) -> None:
        db = self._make_db(monthly_usd=0.0, spent=9999.0)

        result = record_cost(db, "session-1", cost_usd=100.0)

        assert result is True

    def test_increments_heartbeat_run_when_run_id_provided(self) -> None:
        db = self._make_db(monthly_usd=0.0)

        record_cost(db, "session-1", run_id="run-abc", cost_usd=1.0)

        db.heartbeat_runs.increment_usage.assert_called_once()

    def test_does_not_call_heartbeat_when_no_run_id(self) -> None:
        db = self._make_db(monthly_usd=0.0)

        record_cost(db, "session-1", cost_usd=1.0)

        db.heartbeat_runs.increment_usage.assert_not_called()

    def test_emits_budget_exceeded_event_when_exceeded(self) -> None:
        db = self._make_db(monthly_usd=10.0, spent=15.0)

        record_cost(db, "session-1", cost_usd=0.0)

        event_calls = [
            c for c in db.events.emit.call_args_list
            if c[1].get("event_type") == "budget_exceeded"
        ]
        assert len(event_calls) == 1


# ===========================================================================
# Section 11: tokens.py — estimate_tokens
# ===========================================================================


class TestEstimateTokens:
    def test_returns_zero_for_empty_string(self) -> None:
        assert estimate_tokens("") == 0

    def test_returns_at_least_one_for_non_empty_string(self) -> None:
        assert estimate_tokens("x") >= 1

    def test_longer_text_yields_more_tokens(self) -> None:
        short = estimate_tokens("hello")
        long = estimate_tokens("hello " * 100)

        assert long > short

    def test_code_content_type_uses_lower_ratio_than_prose(self) -> None:
        text = "a" * 420
        code_tokens = estimate_tokens(text, content_type="code")
        prose_tokens = estimate_tokens(text, content_type="prose")

        # code ratio=3.5 → more tokens; prose ratio=4.2 → fewer tokens
        assert code_tokens >= prose_tokens

    def test_default_content_type_matches_json_ratio(self) -> None:
        text = "a" * 380
        default_tokens = estimate_tokens(text)
        json_tokens = estimate_tokens(text, content_type="json")

        assert default_tokens == json_tokens

    def test_markdown_returns_fewer_tokens_than_code_for_same_text(self) -> None:
        text = "x" * 400
        md_tokens = estimate_tokens(text, content_type="markdown")
        code_tokens = estimate_tokens(text, content_type="code")

        # markdown ratio=4.0 > code ratio=3.5 → fewer tokens per char
        assert md_tokens <= code_tokens


# ===========================================================================
# Section 12: versioning.py — parse_version
# ===========================================================================


class TestParseVersion:
    def test_parses_standard_version_string(self) -> None:
        v = parse_version("1.2.3")

        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3

    def test_parses_zero_version(self) -> None:
        v = parse_version("0.0.0")

        assert v.major == 0
        assert v.minor == 0
        assert v.patch == 0

    def test_parses_large_version_numbers(self) -> None:
        v = parse_version("100.200.300")

        assert v.major == 100
        assert v.minor == 200
        assert v.patch == 300

    def test_strips_whitespace_before_parsing(self) -> None:
        v = parse_version("  1.0.0  ")

        assert v.major == 1

    def test_raises_versioning_error_for_empty_string(self) -> None:
        with pytest.raises(VersioningError):
            parse_version("")

    def test_raises_versioning_error_for_missing_patch(self) -> None:
        with pytest.raises(VersioningError):
            parse_version("1.2")

    def test_raises_versioning_error_for_alpha_suffix(self) -> None:
        with pytest.raises(VersioningError):
            parse_version("1.0.0-alpha")

    def test_raises_versioning_error_for_non_numeric_parts(self) -> None:
        with pytest.raises(VersioningError):
            parse_version("a.b.c")


# ===========================================================================
# Section 13: versioning.py — SemanticVersion comparison and bump
# ===========================================================================


class TestSemanticVersionComparison:
    def test_str_produces_dotted_version(self) -> None:
        v = SemanticVersion(1, 2, 3)

        assert str(v) == "1.2.3"

    def test_less_than_by_major(self) -> None:
        assert SemanticVersion(1, 0, 0) < SemanticVersion(2, 0, 0)

    def test_less_than_by_minor(self) -> None:
        assert SemanticVersion(1, 0, 0) < SemanticVersion(1, 1, 0)

    def test_less_than_by_patch(self) -> None:
        assert SemanticVersion(1, 0, 0) < SemanticVersion(1, 0, 1)

    def test_equality(self) -> None:
        assert SemanticVersion(2, 3, 4) == SemanticVersion(2, 3, 4)

    def test_greater_than(self) -> None:
        assert SemanticVersion(3, 0, 0) > SemanticVersion(2, 9, 9)

    def test_bump_major_resets_minor_and_patch(self) -> None:
        v = SemanticVersion(1, 5, 3).bump_major()

        assert v == SemanticVersion(2, 0, 0)

    def test_bump_minor_resets_patch(self) -> None:
        v = SemanticVersion(1, 5, 3).bump_minor()

        assert v == SemanticVersion(1, 6, 0)

    def test_bump_patch_increments_only_patch(self) -> None:
        v = SemanticVersion(1, 5, 3).bump_patch()

        assert v == SemanticVersion(1, 5, 4)


# ===========================================================================
# Section 14: versioning.py — validate_version, compare_versions
# ===========================================================================


class TestValidateVersion:
    def test_returns_true_for_valid_version(self) -> None:
        assert validate_version("1.0.0") is True

    def test_returns_false_for_invalid_version(self) -> None:
        assert validate_version("not-a-version") is False

    def test_returns_false_for_empty_string(self) -> None:
        assert validate_version("") is False


class TestCompareVersions:
    def test_returns_negative_one_when_v1_less_than_v2(self) -> None:
        assert compare_versions("1.0.0", "2.0.0") == -1

    def test_returns_zero_when_versions_equal(self) -> None:
        assert compare_versions("1.2.3", "1.2.3") == 0

    def test_returns_one_when_v1_greater_than_v2(self) -> None:
        assert compare_versions("2.0.0", "1.9.9") == 1

    def test_raises_for_invalid_version_string(self) -> None:
        with pytest.raises(VersioningError):
            compare_versions("invalid", "1.0.0")


# ===========================================================================
# Section 15: versioning.py — get_next_version, version_to_tuple, etc.
# ===========================================================================


class TestGetNextVersion:
    def test_patch_bump_by_default(self) -> None:
        assert get_next_version("1.2.3") == "1.2.4"

    def test_minor_bump(self) -> None:
        assert get_next_version("1.2.3", "minor") == "1.3.0"

    def test_major_bump(self) -> None:
        assert get_next_version("1.2.3", "major") == "2.0.0"

    def test_raises_for_unknown_bump_type(self) -> None:
        with pytest.raises(VersioningError):
            get_next_version("1.0.0", "unknown")


class TestVersionToTupleAndBack:
    def test_version_to_tuple(self) -> None:
        assert version_to_tuple("3.4.5") == (3, 4, 5)

    def test_tuple_to_version(self) -> None:
        assert tuple_to_version((3, 4, 5)) == "3.4.5"

    def test_round_trip(self) -> None:
        original = "7.8.9"
        assert tuple_to_version(version_to_tuple(original)) == original


class TestGetLatestVersion:
    def test_returns_none_for_empty_list(self) -> None:
        assert get_latest_version([]) is None

    def test_returns_single_version_in_list(self) -> None:
        assert get_latest_version(["1.0.0"]) == "1.0.0"

    def test_returns_highest_version(self) -> None:
        versions = ["1.0.0", "2.0.0", "1.5.0"]
        assert get_latest_version(versions) == "2.0.0"


class TestIsVersionConflict:
    def test_returns_true_when_version_exists(self) -> None:
        assert is_version_conflict("1.0.0", ["0.9.0", "1.0.0"]) is True

    def test_returns_false_when_version_not_present(self) -> None:
        assert is_version_conflict("2.0.0", ["1.0.0", "1.5.0"]) is False


class TestSuggestNextVersion:
    def test_returns_initial_version_for_empty_list(self) -> None:
        assert suggest_next_version([]) == "1.0.0"

    def test_suggests_patch_bump_by_default(self) -> None:
        assert suggest_next_version(["1.2.3"]) == "1.2.4"

    def test_suggests_minor_bump_when_requested(self) -> None:
        assert suggest_next_version(["1.2.3"], change_type="minor") == "1.3.0"


# ===========================================================================
# Section 16: thread_hooks.py — install_thread_excepthook
# ===========================================================================


class TestInstallThreadExcepthook:
    def test_installs_excepthook_on_threading_module(self) -> None:
        install_thread_excepthook()

        assert threading.excepthook is not None

    def test_hook_logs_error_for_non_system_exit_exception(self) -> None:
        install_thread_excepthook()

        # ExceptHookArgs is a C structseq — construct via positional tuple
        # signature: (exc_type, exc_value, exc_traceback, thread)
        hook_args = threading.ExceptHookArgs(
            (RuntimeError, RuntimeError("oops"), None, None)
        )

        with patch.object(logging.getLogger("pixl.utils.thread_hooks"), "error") as mock_log:
            threading.excepthook(hook_args)
            mock_log.assert_called_once()

    def test_hook_does_not_log_for_system_exit(self) -> None:
        install_thread_excepthook()

        hook_args = threading.ExceptHookArgs(
            (SystemExit, SystemExit(0), None, None)
        )

        with patch.object(logging.getLogger("pixl.utils.thread_hooks"), "error") as mock_log:
            threading.excepthook(hook_args)
            mock_log.assert_not_called()

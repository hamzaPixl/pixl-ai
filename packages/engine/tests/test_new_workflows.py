"""Tests for new workflow templates and the findings-gate hook.

Covers:
- review.yaml — structure, stages, loop, findings-gate hook reference
- security-audit.yaml — structure, stages, loop, findings-gate hook reference
- refactor.yaml — structure, stages, loop, gate
- tdd.yaml v2.1.0 — new evaluate stage, new loop
- debug.yaml v2.1.0 — new regression-test stage, new loop
- findings-gate hook — pass/fail logic, severity threshold, stage hint forwarding
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml
from pixl.execution.hooks import HOOK_REGISTRY, HookContext

WORKFLOWS_DIR = Path(__file__).resolve().parent.parent / "pixl" / "assets" / "workflows"


def _load_workflow(name: str) -> dict:
    path = WORKFLOWS_DIR / f"{name}.yaml"
    assert path.exists(), f"{name}.yaml not found at {path}"
    with path.open() as f:
        return yaml.safe_load(f)


def _make_ctx(
    tmp_path: Path,
    *,
    baton: dict | None = None,
    params: dict | None = None,
) -> HookContext:
    session = MagicMock()
    session.id = "sess-test"
    session.baton = baton
    return HookContext(
        session=session,
        project_root=tmp_path,
        session_dir=tmp_path / ".pixl" / "sessions" / "sess-test",
        artifacts_dir=tmp_path / ".pixl" / "artifacts",
        feature_id="feat-1",
        params=params or {},
    )


# ── Review Workflow ──────────────────────────────────────────────


class TestReviewWorkflow:
    @pytest.fixture()
    def config(self) -> dict:
        return _load_workflow("review")

    def test_id_and_format(self, config: dict) -> None:
        assert config["id"] == "review"
        assert config["workflow_format"] == "v2"

    def test_stage_ids(self, config: dict) -> None:
        ids = [s["id"] for s in config["stages"]]
        assert "analyze" in ids
        assert "findings-gate" in ids

    def test_findings_gate_hook(self, config: dict) -> None:
        stages = {s["id"]: s for s in config["stages"]}
        gate = stages["findings-gate"]
        assert gate["type"] == "hook"
        assert gate["hook"] == "findings-gate"

    def test_has_loop(self, config: dict) -> None:
        assert len(config["loops"]) >= 1
        loop = config["loops"][0]
        assert loop["trigger"] == "failure"
        assert loop["from"] == "findings-gate"

    def test_has_approve_gate(self, config: dict) -> None:
        stages = {s["id"]: s for s in config["stages"]}
        assert stages["approve"]["type"] == "gate"


# ── Security Audit Workflow ──────────────────────────────────────


class TestSecurityAuditWorkflow:
    @pytest.fixture()
    def config(self) -> dict:
        return _load_workflow("security-audit")

    def test_id_and_format(self, config: dict) -> None:
        assert config["id"] == "security-audit"
        assert config["workflow_format"] == "v2"

    def test_has_five_stages(self, config: dict) -> None:
        ids = [s["id"] for s in config["stages"]]
        assert "scan" in ids
        assert "remediate" in ids
        assert "verify" in ids
        assert "findings-gate" in ids
        assert "approve" in ids

    def test_findings_gate_targets_remediate(self, config: dict) -> None:
        stages = {s["id"]: s for s in config["stages"]}
        gate = stages["findings-gate"]
        assert gate["hook"] == "findings-gate"
        assert gate["hook_params"]["target_stage"] == "remediate"

    def test_loop_from_gate_to_remediate(self, config: dict) -> None:
        loops = config["loops"]
        sec_loop = next(lp for lp in loops if lp["id"] == "security-fix-loop")
        assert sec_loop["from"] == "findings-gate"
        assert sec_loop["to"] == "remediate"
        assert sec_loop["max_iterations"] == 2

    def test_scan_has_contract(self, config: dict) -> None:
        stages = {s["id"]: s for s in config["stages"]}
        assert "must_write" in stages["scan"].get("contract", {})


# ── Refactor Workflow ────────────────────────────────────────────


class TestRefactorWorkflow:
    @pytest.fixture()
    def config(self) -> dict:
        return _load_workflow("refactor")

    def test_id_and_format(self, config: dict) -> None:
        assert config["id"] == "refactor"
        assert config["workflow_format"] == "v2"

    def test_has_six_stages(self, config: dict) -> None:
        ids = [s["id"] for s in config["stages"]]
        assert len(ids) == 6
        assert "analyze" in ids
        assert "plan" in ids
        assert "approve-plan" in ids
        assert "implement" in ids
        assert "verify" in ids
        assert "finalize" in ids

    def test_approve_gate_freezes_plan(self, config: dict) -> None:
        stages = {s["id"]: s for s in config["stages"]}
        gate = stages["approve-plan"]
        assert gate["type"] == "gate"
        assert "refactor-plan.md" in gate.get("freeze_artifacts", [])

    def test_loop_from_verify_to_implement(self, config: dict) -> None:
        loops = config["loops"]
        ref_loop = next(lp for lp in loops if "fix" in lp["id"] or "regression" in lp["id"])
        assert ref_loop["from"] == "verify"
        assert ref_loop["to"] == "implement"
        assert ref_loop["trigger"] == "failure"

    def test_edges_chain(self, config: dict) -> None:
        edges = config["edges"]
        assert "plan" in edges.get("analyze", [])
        assert "approve-plan" in edges.get("plan", [])


# ── TDD v2.1 Improvement ────────────────────────────────────────


class TestTddWorkflowImproved:
    @pytest.fixture()
    def config(self) -> dict:
        return _load_workflow("tdd")

    def test_has_evaluate_stage(self, config: dict) -> None:
        ids = [s["id"] for s in config["stages"]]
        assert "evaluate" in ids

    def test_evaluate_between_implement_and_finalize(self, config: dict) -> None:
        ids = [s["id"] for s in config["stages"]]
        impl_idx = ids.index("implement")
        eval_idx = ids.index("evaluate")
        final_idx = ids.index("finalize")
        assert impl_idx < eval_idx < final_idx

    def test_has_evaluate_loop(self, config: dict) -> None:
        loop_ids = [lp["id"] for lp in config["loops"]]
        assert any("evaluate" in lid or "eval" in lid for lid in loop_ids)

    def test_version_bumped(self, config: dict) -> None:
        assert config["version"] != "2.0.0"


# ── Debug v2.1 Improvement ───────────────────────────────────────


class TestDebugWorkflowImproved:
    @pytest.fixture()
    def config(self) -> dict:
        return _load_workflow("debug")

    def test_has_regression_test_stage(self, config: dict) -> None:
        ids = [s["id"] for s in config["stages"]]
        assert "regression-test" in ids

    def test_regression_test_between_fix_and_finalize(self, config: dict) -> None:
        ids = [s["id"] for s in config["stages"]]
        fix_idx = ids.index("fix")
        reg_idx = ids.index("regression-test")
        final_idx = ids.index("finalize")
        assert fix_idx < reg_idx < final_idx

    def test_has_regression_loop(self, config: dict) -> None:
        loop_ids = [lp["id"] for lp in config["loops"]]
        assert any("regression" in lid for lid in loop_ids)

    def test_original_debug_loop_preserved(self, config: dict) -> None:
        loop_ids = [lp["id"] for lp in config["loops"]]
        assert "debug-loop" in loop_ids

    def test_version_bumped(self, config: dict) -> None:
        assert config["version"] != "2.0.0"


# ── Findings-Gate Hook ───────────────────────────────────────────


class TestFindingsGateHook:
    def test_registered(self) -> None:
        assert "findings-gate" in HOOK_REGISTRY

    def test_passes_when_zero_findings(self, tmp_path: Path) -> None:
        from pixl.execution.hooks.harness_hooks import findings_gate_hook

        baton = {"quality_signals": {"open_findings": 0, "max_severity": "none"}}
        ctx = _make_ctx(tmp_path, baton=baton)
        result = findings_gate_hook(ctx)
        assert result.success is True

    def test_fails_when_p0_findings(self, tmp_path: Path) -> None:
        from pixl.execution.hooks.harness_hooks import findings_gate_hook

        baton = {
            "quality_signals": {
                "open_findings": 3,
                "max_severity": "P0",
                "findings_summary": "3 critical issues found.",
            },
            "stage_hints": {},
        }
        ctx = _make_ctx(tmp_path, baton=baton)
        result = findings_gate_hook(ctx)
        assert result.success is False
        assert result.data["open_findings"] == 3

    def test_forwards_summary_to_target_stage(self, tmp_path: Path) -> None:
        from pixl.execution.hooks.harness_hooks import findings_gate_hook

        baton = {
            "quality_signals": {
                "open_findings": 2,
                "max_severity": "P1",
                "findings_summary": "Fix auth bypass and XSS.",
            },
            "stage_hints": {},
        }
        ctx = _make_ctx(tmp_path, baton=baton, params={"target_stage": "remediate"})
        findings_gate_hook(ctx)
        assert baton["stage_hints"]["remediate"] == "Fix auth bypass and XSS."

    def test_passes_when_severity_below_threshold(self, tmp_path: Path) -> None:
        from pixl.execution.hooks.harness_hooks import findings_gate_hook

        baton = {
            "quality_signals": {"open_findings": 5, "max_severity": "P3"},
        }
        ctx = _make_ctx(tmp_path, baton=baton, params={"severity_threshold": "P1"})
        result = findings_gate_hook(ctx)
        assert result.success is True

    def test_fails_when_severity_at_threshold(self, tmp_path: Path) -> None:
        from pixl.execution.hooks.harness_hooks import findings_gate_hook

        baton = {
            "quality_signals": {
                "open_findings": 1,
                "max_severity": "P1",
                "findings_summary": "One high-impact issue.",
            },
            "stage_hints": {},
        }
        ctx = _make_ctx(tmp_path, baton=baton, params={"severity_threshold": "P1"})
        result = findings_gate_hook(ctx)
        assert result.success is False

    def test_missing_baton_returns_failure(self, tmp_path: Path) -> None:
        from pixl.execution.hooks.harness_hooks import findings_gate_hook

        ctx = _make_ctx(tmp_path, baton=None)
        result = findings_gate_hook(ctx)
        assert result.success is False
        assert "baton" in result.error.lower()

    def test_custom_p0_only_threshold(self, tmp_path: Path) -> None:
        from pixl.execution.hooks.harness_hooks import findings_gate_hook

        baton = {
            "quality_signals": {"open_findings": 3, "max_severity": "P1"},
        }
        ctx = _make_ctx(tmp_path, baton=baton, params={"severity_threshold": "P0"})
        result = findings_gate_hook(ctx)
        # P1 is below the P0-only threshold, so it passes
        assert result.success is True

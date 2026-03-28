"""Tests for harness_hooks — score-gate hook.

Covers:
- All criteria pass threshold → success
- Some criteria fail threshold → failure with details
- Missing baton → failure
- Missing quality_signals → failure
- Custom threshold and criteria via params
- Stage hint forwarded from critique summary
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from pixl.execution.hooks import HookContext


def _make_session(
    *,
    baton: dict | None = None,
    session_id: str = "sess-001",
) -> MagicMock:
    session = MagicMock()
    session.id = session_id
    session.baton = baton
    return session


def _make_ctx(
    tmp_path: Path,
    *,
    baton: dict | None = None,
    params: dict | None = None,
) -> HookContext:
    session = _make_session(baton=baton)
    return HookContext(
        session=session,
        project_root=tmp_path,
        session_dir=tmp_path / ".pixl" / "sessions" / session.id,
        artifacts_dir=tmp_path / ".pixl" / "artifacts",
        feature_id="feat-1",
        params=params or {},
    )


class TestScoreGateHook:
    """Tests for the score-gate hook."""

    def test_all_criteria_pass(self, tmp_path: Path) -> None:
        """When all criteria meet or exceed the threshold, hook returns success."""
        from pixl.execution.hooks.harness_hooks import score_gate_hook

        baton = {
            "quality_signals": {
                "design_quality": 8,
                "originality": 7,
                "craft": 9,
                "functionality": 8,
                "iteration": 2,
                "critique_summary": "Good overall quality.",
            },
        }
        ctx = _make_ctx(tmp_path, baton=baton)
        result = score_gate_hook(ctx)

        assert result.success is True
        assert result.data["passed"] is True
        assert result.data["design_quality"] == 8
        assert result.data["iteration"] == 2

    def test_some_criteria_fail(self, tmp_path: Path) -> None:
        """When any criterion is below threshold, hook returns failure."""
        from pixl.execution.hooks.harness_hooks import score_gate_hook

        baton = {
            "quality_signals": {
                "design_quality": 8,
                "originality": 5,
                "craft": 6,
                "functionality": 9,
                "iteration": 1,
                "critique_summary": "Originality and craft need work.",
            },
        }
        ctx = _make_ctx(tmp_path, baton=baton)
        result = score_gate_hook(ctx)

        assert result.success is False
        assert "originality" in result.error
        assert "craft" in result.error
        assert set(result.data["failed_criteria"]) == {"originality", "craft"}

    def test_updates_stage_hint_on_failure(self, tmp_path: Path) -> None:
        """On failure, the baton's stage_hints['generate'] is set to critique summary."""
        from pixl.execution.hooks.harness_hooks import score_gate_hook

        baton = {
            "quality_signals": {
                "design_quality": 5,
                "originality": 5,
                "craft": 5,
                "functionality": 5,
                "iteration": 1,
                "critique_summary": "Everything needs improvement.",
            },
            "stage_hints": {},
        }
        ctx = _make_ctx(tmp_path, baton=baton)
        score_gate_hook(ctx)

        assert baton["stage_hints"]["generate"] == "Everything needs improvement."

    def test_does_not_set_stage_hint_on_success(self, tmp_path: Path) -> None:
        """On success, stage_hints['generate'] is not set."""
        from pixl.execution.hooks.harness_hooks import score_gate_hook

        baton = {
            "quality_signals": {
                "design_quality": 10,
                "originality": 10,
                "craft": 10,
                "functionality": 10,
                "iteration": 1,
                "critique_summary": "Perfect.",
            },
            "stage_hints": {},
        }
        ctx = _make_ctx(tmp_path, baton=baton)
        score_gate_hook(ctx)

        assert "generate" not in baton["stage_hints"]

    def test_missing_baton_returns_failure(self, tmp_path: Path) -> None:
        """When session.baton is None, hook returns failure."""
        from pixl.execution.hooks.harness_hooks import score_gate_hook

        ctx = _make_ctx(tmp_path, baton=None)
        result = score_gate_hook(ctx)

        assert result.success is False
        assert "baton" in result.error.lower()

    def test_missing_quality_signals_returns_failure(self, tmp_path: Path) -> None:
        """When baton has no quality_signals, hook returns failure."""
        from pixl.execution.hooks.harness_hooks import score_gate_hook

        baton: dict = {"stage_hints": {}}
        ctx = _make_ctx(tmp_path, baton=baton)
        result = score_gate_hook(ctx)

        assert result.success is False
        assert "quality_signals" in result.error.lower()

    def test_custom_threshold(self, tmp_path: Path) -> None:
        """Custom threshold from params overrides default of 7."""
        from pixl.execution.hooks.harness_hooks import score_gate_hook

        baton = {
            "quality_signals": {
                "design_quality": 8,
                "originality": 8,
                "craft": 8,
                "functionality": 8,
                "iteration": 1,
            },
        }
        # Threshold of 9 — all scores at 8 should fail
        ctx = _make_ctx(tmp_path, baton=baton, params={"threshold": 9})
        result = score_gate_hook(ctx)

        assert result.success is False
        assert len(result.data["failed_criteria"]) == 4

    def test_custom_criteria(self, tmp_path: Path) -> None:
        """Custom criteria from params limits which scores are checked."""
        from pixl.execution.hooks.harness_hooks import score_gate_hook

        baton = {
            "quality_signals": {
                "design_quality": 5,
                "originality": 5,
                "craft": 9,
                "functionality": 9,
                "iteration": 1,
            },
        }
        # Only check craft and functionality — both pass
        ctx = _make_ctx(
            tmp_path,
            baton=baton,
            params={"criteria": ["craft", "functionality"]},
        )
        result = score_gate_hook(ctx)

        assert result.success is True

    def test_missing_criterion_in_signals_treated_as_zero(self, tmp_path: Path) -> None:
        """If a required criterion is absent from quality_signals, it scores 0."""
        from pixl.execution.hooks.harness_hooks import score_gate_hook

        baton = {
            "quality_signals": {
                "design_quality": 10,
                # originality, craft, functionality are missing
                "iteration": 1,
            },
        }
        ctx = _make_ctx(tmp_path, baton=baton)
        result = score_gate_hook(ctx)

        assert result.success is False
        assert "originality" in result.data["failed_criteria"]
        assert "craft" in result.data["failed_criteria"]
        assert "functionality" in result.data["failed_criteria"]

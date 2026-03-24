"""Tests for routing classifier, models, state_router, and recovery helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pixl.errors import (
    ContractError,
    PixlError,
    ProviderError,
    StateError,
)
from pixl.errors import TimeoutError as PixlTimeoutError
from pixl.execution.recovery.error_classifier import (
    error_from_result,
    extract_affected_files_from_diff,
    extract_diff_from_output,
)
from pixl.routing.models import (
    _FALLBACK_WORKFLOWS,
    RouterResult,
    WorkKind,
    get_allowed_workflows,
)
from pixl.routing.state_router import (
    EntityMatch,
    StateAwareRouter,
    StateContext,
    map_entity_type_to_work_kind,
    suggest_workflow_for_state,
    title_similarity,
)

# ---------------------------------------------------------------------------
# RouterResult / WorkKind / get_allowed_workflows
# ---------------------------------------------------------------------------


class TestWorkKind:
    def test_has_expected_values(self) -> None:
        assert WorkKind.FEATURE == "feature"
        assert WorkKind.BUG == "bug"
        assert WorkKind.EPIC == "epic"
        assert WorkKind.ROADMAP == "roadmap"


class TestGetAllowedWorkflows:
    def test_returns_a_set(self) -> None:
        result = get_allowed_workflows()
        assert isinstance(result, set)

    def test_returns_non_empty_set(self) -> None:
        result = get_allowed_workflows()
        assert len(result) > 0

    def test_fallback_workflows_are_subset(self) -> None:
        # At minimum the fallback workflows should always be present
        result = get_allowed_workflows()
        assert _FALLBACK_WORKFLOWS.issubset(result) or _FALLBACK_WORKFLOWS == result


class TestRouterResultValidation:
    def _valid_payload(self, **overrides: Any) -> dict:
        base = {
            "kind": "feature",
            "confidence": 0.9,
            "title": "Add login page",
            "why": ["needs auth"],
            "suggested_workflow": "tdd",
            "estimated_features": 1,
        }
        base.update(overrides)
        return base

    def test_valid_payload_creates_model(self) -> None:
        r = RouterResult.model_validate(self._valid_payload())
        assert r.kind == WorkKind.FEATURE
        assert r.confidence == 0.9
        assert r.title == "Add login page"

    def test_confidence_below_0_raises(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RouterResult.model_validate(self._valid_payload(confidence=-0.1))

    def test_confidence_above_1_raises(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RouterResult.model_validate(self._valid_payload(confidence=1.1))

    def test_empty_title_raises(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RouterResult.model_validate(self._valid_payload(title=""))

    def test_empty_why_list_raises(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RouterResult.model_validate(self._valid_payload(why=[]))

    def test_unknown_workflow_raises(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RouterResult.model_validate(
                self._valid_payload(suggested_workflow="nonexistent-workflow-xyz")
            )

    def test_defaults_risk_flags_to_empty_list(self) -> None:
        r = RouterResult.model_validate(self._valid_payload())
        assert r.risk_flags == []

    def test_defaults_next_inputs_to_empty_dict(self) -> None:
        r = RouterResult.model_validate(self._valid_payload())
        assert r.next_inputs == {}

    def test_defaults_estimated_features_to_1(self) -> None:
        payload = self._valid_payload()
        del payload["estimated_features"]
        r = RouterResult.model_validate(payload)
        assert r.estimated_features == 1

    def test_estimated_features_below_1_raises(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RouterResult.model_validate(self._valid_payload(estimated_features=0))


# ---------------------------------------------------------------------------
# PromptClassifier._parse_response (pure logic only)
# ---------------------------------------------------------------------------


class TestPromptClassifierParseResponse:
    def _make_classifier(self) -> Any:
        from pixl.routing.classifier import PromptClassifier

        with patch("pixl.routing.classifier.load_providers_config") as mock_cfg:
            mock_cfg.return_value = MagicMock(default_model="claude-sonnet-4-6")
            clf = PromptClassifier.__new__(PromptClassifier)
            clf.project_path = Path("/fake")
            clf.model = "claude-sonnet-4-6"
        return clf

    def _valid_json(self, **overrides: Any) -> str:
        payload = {
            "kind": "feature",
            "confidence": 0.85,
            "title": "Build search",
            "why": ["user asked for it"],
            "suggested_workflow": "tdd",
            "estimated_features": 1,
        }
        payload.update(overrides)
        return json.dumps(payload)

    def test_parses_valid_json_response(self) -> None:
        clf = self._make_classifier()
        result = clf._parse_response(self._valid_json())
        assert result.title == "Build search"

    def test_strips_markdown_code_fence(self) -> None:
        clf = self._make_classifier()
        fenced = f"```json\n{self._valid_json()}\n```"
        result = clf._parse_response(fenced)
        assert result.kind == WorkKind.FEATURE

    def test_strips_generic_code_fence(self) -> None:
        clf = self._make_classifier()
        fenced = f"```\n{self._valid_json()}\n```"
        result = clf._parse_response(fenced)
        assert result.confidence == 0.85

    def test_raises_on_invalid_json(self) -> None:
        from pixl.routing.classifier import ClassificationError

        clf = self._make_classifier()
        with pytest.raises(ClassificationError, match="Failed to parse router response"):
            clf._parse_response("not json at all")

    def test_raises_on_valid_json_but_invalid_schema(self) -> None:
        from pixl.routing.classifier import ClassificationError

        clf = self._make_classifier()
        with pytest.raises(ClassificationError, match="failed validation"):
            clf._parse_response('{"kind": "feature"}')

    def test_builds_prompt_with_user_input(self) -> None:
        clf = self._make_classifier()
        with patch.object(clf, "_load_prompt_template", return_value="classify: {user_prompt}"):
            built = clf._build_prompt("fix auth")
            assert "fix auth" in built
            assert "{user_prompt}" not in built


# ---------------------------------------------------------------------------
# StateContext
# ---------------------------------------------------------------------------


class TestStateContext:
    def test_best_match_returns_first_match(self) -> None:
        m1 = EntityMatch("feat-001", "feature", "Login page", "backlog", 0.9)
        m2 = EntityMatch("feat-002", "feature", "Logout page", "backlog", 0.6)
        ctx = StateContext(matches=[m1, m2])
        assert ctx.best_match is m1

    def test_best_match_returns_none_when_no_matches(self) -> None:
        ctx = StateContext()
        assert ctx.best_match is None

    def test_has_blocked_true_when_blocked_features_present(self) -> None:
        ctx = StateContext(blocked_features=["feat-001"])
        assert ctx.has_blocked is True

    def test_has_blocked_false_when_no_blocked_features(self) -> None:
        ctx = StateContext()
        assert ctx.has_blocked is False


# ---------------------------------------------------------------------------
# suggest_workflow_for_state (state_router)
# ---------------------------------------------------------------------------


class TestSuggestWorkflowForStateRouter:
    def test_feature_backlog_suggests_tdd(self) -> None:
        result = suggest_workflow_for_state("feature", "backlog")
        assert result == "tdd"

    def test_feature_blocked_suggests_debug(self) -> None:
        result = suggest_workflow_for_state("feature", "blocked")
        assert result == "debug"

    def test_feature_in_progress_suggests_simple(self) -> None:
        result = suggest_workflow_for_state("feature", "in_progress")
        assert result == "simple"

    def test_epic_drafting_suggests_decompose(self) -> None:
        result = suggest_workflow_for_state("epic", "drafting")
        assert result == "decompose"

    def test_roadmap_drafting_suggests_roadmap(self) -> None:
        result = suggest_workflow_for_state("roadmap", "drafting")
        assert result == "roadmap"

    def test_unknown_entity_type_returns_none(self) -> None:
        result = suggest_workflow_for_state("unknown", "backlog")
        assert result is None

    def test_unknown_status_returns_none(self) -> None:
        result = suggest_workflow_for_state("feature", "nonexistent_status")
        assert result is None


# ---------------------------------------------------------------------------
# map_entity_type_to_work_kind
# ---------------------------------------------------------------------------


class TestMapEntityTypeToWorkKind:
    def test_feature_maps_to_feature(self) -> None:
        assert map_entity_type_to_work_kind("feature") == WorkKind.FEATURE

    def test_epic_maps_to_epic(self) -> None:
        assert map_entity_type_to_work_kind("epic") == WorkKind.EPIC

    def test_roadmap_maps_to_roadmap(self) -> None:
        assert map_entity_type_to_work_kind("roadmap") == WorkKind.ROADMAP

    def test_unknown_defaults_to_feature(self) -> None:
        assert map_entity_type_to_work_kind("unknown") == WorkKind.FEATURE


# ---------------------------------------------------------------------------
# title_similarity (state_router)
# ---------------------------------------------------------------------------


class TestTitleSimilarityRouter:
    def test_identical_strings_score_1(self) -> None:
        assert title_similarity("fix the login bug", "fix the login bug") == 1.0

    def test_no_overlap_scores_0(self) -> None:
        score = title_similarity("user authentication flow", "database migration script")
        assert score == 0.0

    def test_partial_overlap_between_0_and_1(self) -> None:
        score = title_similarity("fix the login page", "fix the signup page")
        assert 0.0 < score < 1.0

    def test_empty_prompt_scores_0(self) -> None:
        assert title_similarity("", "fix auth") == 0.0

    def test_empty_title_scores_0(self) -> None:
        assert title_similarity("fix auth", "") == 0.0

    def test_short_tokens_below_threshold_ignored(self) -> None:
        # Regex [a-z][a-z0-9_]{2,} requires at least 3 chars
        # All tokens here are 2 chars max so both sets are empty → score is 0
        assert title_similarity("a b to or", "a b to or") == 0.0


# ---------------------------------------------------------------------------
# StateAwareRouter.adjust
# ---------------------------------------------------------------------------


class TestStateAwareRouterAdjust:
    def _make_base_result(self, workflow: str = "tdd") -> RouterResult:
        return RouterResult(
            kind=WorkKind.FEATURE,
            confidence=0.8,
            title="Fix login",
            why=["user asked"],
            suggested_workflow=workflow,
        )

    def _make_router(self) -> StateAwareRouter:
        router = StateAwareRouter.__new__(StateAwareRouter)
        router.project_path = Path("/fake")
        return router

    def test_returns_base_when_no_matches(self) -> None:
        router = self._make_router()
        ctx = StateContext()
        result, reasons = router.adjust(self._make_base_result(), ctx)
        assert result.suggested_workflow == "tdd"
        assert reasons == []

    def test_adjusts_workflow_when_entity_match_with_different_status(self) -> None:
        router = self._make_router()
        ctx = StateContext(
            matches=[EntityMatch("feat-001", "feature", "Fix login", "blocked", 0.9)]
        )
        # base suggests tdd, but blocked feature should suggest debug
        result, reasons = router.adjust(self._make_base_result("tdd"), ctx)
        assert result.suggested_workflow == "debug"
        assert reasons

    def test_returns_base_when_same_workflow_suggested(self) -> None:
        router = self._make_router()
        # feature in backlog → suggests tdd, which is same as base
        ctx = StateContext(
            matches=[EntityMatch("feat-001", "feature", "Fix login", "backlog", 0.9)]
        )
        result, reasons = router.adjust(self._make_base_result("tdd"), ctx)
        assert result.suggested_workflow == "tdd"

    def test_appends_blocked_note_even_without_workflow_change(self) -> None:
        router = self._make_router()
        ctx = StateContext(
            matches=[EntityMatch("feat-001", "feature", "Fix login", "backlog", 0.9)],
            blocked_features=["feat-002"],
        )
        _result, reasons = router.adjust(self._make_base_result("tdd"), ctx)
        assert any("blocked" in r for r in reasons)

    def test_appends_in_progress_note_even_without_workflow_change(self) -> None:
        router = self._make_router()
        ctx = StateContext(
            matches=[EntityMatch("feat-001", "feature", "Fix login", "backlog", 0.9)],
            in_progress_count=3,
        )
        _result, reasons = router.adjust(self._make_base_result("tdd"), ctx)
        assert any("in progress" in r for r in reasons)

    def test_adjusted_result_includes_reasons_in_why(self) -> None:
        router = self._make_router()
        ctx = StateContext(
            matches=[EntityMatch("feat-001", "feature", "Fix login", "blocked", 0.9)]
        )
        result, reasons = router.adjust(self._make_base_result("tdd"), ctx)
        for reason in reasons:
            assert reason in result.why


# ---------------------------------------------------------------------------
# error_from_result
# ---------------------------------------------------------------------------


class TestErrorFromResult:
    def test_returns_provider_error_for_provider_error_type(self) -> None:
        result = {"error": "Rate limited", "error_type": "provider_error"}
        err = error_from_result(result)
        assert isinstance(err, ProviderError)

    def test_returns_provider_error_for_provider_failure_kind(self) -> None:
        result = {"error": "API down", "failure_kind": "provider"}
        err = error_from_result(result)
        assert isinstance(err, ProviderError)

    def test_provider_error_extracts_http_status(self) -> None:
        result = {
            "error": "Rate limited",
            "error_type": "provider_error",
            "error_metadata": {"http_status": 429},
        }
        err = error_from_result(result)
        assert isinstance(err, ProviderError)
        assert err.metadata.get("http_status") == 429

    def test_returns_timeout_error_for_timeout_error_type(self) -> None:
        result = {"error": "timed out", "error_type": "timeout_error"}
        err = error_from_result(result)
        assert isinstance(err, PixlTimeoutError)

    def test_returns_timeout_error_for_timeout_failure_kind(self) -> None:
        result = {"error": "timed out", "failure_kind": "timeout"}
        err = error_from_result(result)
        assert isinstance(err, PixlTimeoutError)

    def test_returns_contract_error_for_contract_violation(self) -> None:
        result = {"error": "contract broken", "failure_kind": "contract_violation"}
        err = error_from_result(result)
        assert isinstance(err, ContractError)

    def test_returns_contract_error_for_contract_error_type(self) -> None:
        result = {"error": "contract broken", "error_type": "contract_error"}
        err = error_from_result(result)
        assert isinstance(err, ContractError)

    def test_contract_error_uses_rule_from_metadata(self) -> None:
        result = {
            "error": "broken",
            "error_type": "contract_error",
            "error_metadata": {"rule": "artifact-required"},
        }
        err = error_from_result(result)
        assert isinstance(err, ContractError)
        assert err.metadata.get("rule") == "artifact-required"

    def test_returns_state_error_for_state_error_type(self) -> None:
        result = {"error": "invalid state", "error_type": "state_error"}
        err = error_from_result(result)
        assert isinstance(err, StateError)

    def test_returns_base_pixl_error_for_unknown_type(self) -> None:
        result = {"error": "something weird", "error_type": "some_other_error"}
        err = error_from_result(result)
        assert isinstance(err, PixlError)
        assert not isinstance(err, (ProviderError, PixlTimeoutError, ContractError, StateError))

    def test_base_pixl_error_is_transient_for_transient_failure_kind(self) -> None:
        result = {"error": "flaky", "failure_kind": "transient"}
        err = error_from_result(result)
        assert err.is_transient is True

    def test_base_pixl_error_not_transient_for_unknown_failure_kind(self) -> None:
        result = {"error": "unknown failure"}
        err = error_from_result(result)
        assert err.is_transient is False

    def test_uses_unknown_error_message_when_error_missing(self) -> None:
        err = error_from_result({})
        assert "Unknown error" in err.message


# ---------------------------------------------------------------------------
# extract_diff_from_output
# ---------------------------------------------------------------------------


class TestExtractDiffFromOutput:
    def test_extracts_diff_from_code_fence(self) -> None:
        text = "Here is the diff:\n```diff\n+added line\n-removed line\n```\nDone."
        result = extract_diff_from_output(text)
        assert "+added line" in result
        assert "-removed line" in result

    def test_strips_fence_markers(self) -> None:
        text = "```diff\n+added\n```"
        result = extract_diff_from_output(text)
        assert "```" not in result

    def test_extracts_bare_diff_lines_fallback(self) -> None:
        text = "@@ -1,3 +1,4 @@\n-old line\n+new line\n context line"
        result = extract_diff_from_output(text)
        assert "@@" in result
        assert "+new line" in result

    def test_returns_empty_when_no_diff_content(self) -> None:
        result = extract_diff_from_output("no diff here at all")
        assert result == ""

    def test_returns_empty_for_empty_input(self) -> None:
        result = extract_diff_from_output("")
        assert result == ""

    def test_extracts_generic_code_fence_with_diff_markers(self) -> None:
        text = "```\n--- a/foo.py\n+++ b/foo.py\n@@ -1 +1 @@\n+hello\n```"
        result = extract_diff_from_output(text)
        assert result  # Should extract something

    def test_prefers_named_diff_fence_over_bare_fence(self) -> None:
        text = "```diff\n+explicit\n-removed\n```"
        result = extract_diff_from_output(text)
        assert "+explicit" in result


# ---------------------------------------------------------------------------
# extract_affected_files_from_diff
# ---------------------------------------------------------------------------


class TestExtractAffectedFilesFromDiff:
    def test_extracts_file_from_triple_plus_header(self) -> None:
        diff = "+++ b/src/foo.py\n@@ -1 +1 @@\n+line"
        files = extract_affected_files_from_diff(diff)
        assert "src/foo.py" in files

    def test_extracts_file_from_triple_minus_header(self) -> None:
        diff = "--- a/src/foo.py\n+++ b/src/foo.py\n"
        files = extract_affected_files_from_diff(diff)
        assert "src/foo.py" in files

    def test_deduplicates_same_file_in_plus_and_minus(self) -> None:
        diff = "--- a/src/foo.py\n+++ b/src/foo.py\n"
        files = extract_affected_files_from_diff(diff)
        assert files.count("src/foo.py") == 1

    def test_excludes_dev_null(self) -> None:
        diff = "--- /dev/null\n+++ b/src/new_file.py\n"
        files = extract_affected_files_from_diff(diff)
        assert "/dev/null" not in files
        assert "src/new_file.py" in files

    def test_returns_sorted_list(self) -> None:
        diff = "+++ b/src/z_file.py\n+++ b/src/a_file.py\n"
        files = extract_affected_files_from_diff(diff)
        assert files == sorted(files)

    def test_returns_empty_list_for_empty_diff(self) -> None:
        files = extract_affected_files_from_diff("")
        assert files == []

    def test_handles_multiple_files(self) -> None:
        diff = "--- a/foo.py\n+++ b/foo.py\n--- a/bar.py\n+++ b/bar.py\n"
        files = extract_affected_files_from_diff(diff)
        assert len(files) == 2

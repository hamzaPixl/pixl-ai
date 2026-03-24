"""Unit tests for the Baton and ArtifactRef models.

Pure-Python tests — no I/O, no database.  All tests follow Arrange-Act-Assert
and are isolated from each other (no shared mutable state).
"""

from __future__ import annotations

import pytest

from pixl.models.baton import ArtifactRef, Baton


# ---------------------------------------------------------------------------
# ArtifactRef
# ---------------------------------------------------------------------------


class TestArtifactRef:
    def test_to_inline_renders_id_type_and_hash(self) -> None:
        # Arrange
        ref = ArtifactRef(id="art-0001", hash="abcdef123456789012", type="code")

        # Act
        result = ref.to_inline()

        # Assert
        assert "art-0001" in result
        assert "code" in result
        assert "abcdef123456" in result  # first 12 chars of hash

    def test_to_inline_includes_summary_ref_when_present(self) -> None:
        ref = ArtifactRef(
            id="art-0002",
            hash="fedcba9876543210ab",
            type="document",
            summary_ref="summaries/art-0002.md",
        )
        result = ref.to_inline()
        assert "summary:" in result
        assert "summaries/art-0002.md" in result

    def test_to_inline_omits_summary_section_when_none(self) -> None:
        ref = ArtifactRef(id="art-0003", hash="aaaa1111bbbb2222cc", type="test")
        result = ref.to_inline()
        assert "summary:" not in result


# ---------------------------------------------------------------------------
# Baton construction
# ---------------------------------------------------------------------------


class TestBatonConstruction:
    def test_requires_goal_field(self) -> None:
        with pytest.raises(Exception):  # pydantic ValidationError
            Baton()  # type: ignore[call-arg]

    def test_list_fields_default_to_empty(self) -> None:
        baton = Baton(goal="Ship the feature")
        assert baton.current_state == []
        assert baton.decision_log == []
        assert baton.open_questions == []
        assert baton.constraints == []
        assert baton.artifacts == []
        assert baton.work_scope == []
        assert baton.acceptance == []

    def test_dict_fields_default_to_empty(self) -> None:
        baton = Baton(goal="Ship the feature")
        assert baton.stage_hints == {}
        assert baton.quality_signals == {}

    def test_from_feature_sets_goal_to_title(self) -> None:
        baton = Baton.from_feature("Add authentication", "Users should be able to log in")
        assert baton.goal == "Add authentication"

    def test_from_feature_sets_initial_current_state(self) -> None:
        baton = Baton.from_feature("Add auth", "Some description")
        assert "Workflow starting" in baton.current_state


# ---------------------------------------------------------------------------
# Baton.to_prompt_section
# ---------------------------------------------------------------------------


class TestToPromptSection:
    def test_always_includes_goal(self) -> None:
        baton = Baton(goal="Implement payments")
        result = baton.to_prompt_section()
        assert "Implement payments" in result

    def test_includes_current_state_when_set(self) -> None:
        baton = Baton(goal="Goal", current_state=["Step 1 done", "Step 2 pending"])
        result = baton.to_prompt_section()
        assert "Step 1 done" in result
        assert "Step 2 pending" in result

    def test_includes_baton_header(self) -> None:
        baton = Baton(goal="G")
        result = baton.to_prompt_section()
        assert "Baton" in result

    def test_omits_empty_list_fields(self) -> None:
        baton = Baton(goal="G")
        result = baton.to_prompt_section()
        # No artifacts section when list is empty
        assert "**Artifacts:**" not in result

    def test_includes_constraints_when_set(self) -> None:
        baton = Baton(goal="G", constraints=["No breaking changes", "Must pass CI"])
        result = baton.to_prompt_section()
        assert "No breaking changes" in result

    def test_emphasis_renders_emphasized_field_in_full(self) -> None:
        baton = Baton(
            goal="G",
            constraints=["Rule 1", "Rule 2", "Rule 3", "Rule 4"],
        )
        # With emphasis on constraints, all items should appear
        result = baton.to_prompt_section(emphasis=["constraints"])
        for rule in ["Rule 1", "Rule 2", "Rule 3", "Rule 4"]:
            assert rule in result

    def test_emphasis_compacts_non_emphasized_fields(self) -> None:
        baton = Baton(
            goal="G",
            constraints=["Rule A", "Rule B"],
            open_questions=["Q1", "Q2", "Q3", "Q4"],
        )
        # Emphasize constraints — open_questions should be in compact form
        result = baton.to_prompt_section(emphasis=["constraints"])
        # Compact format uses semicolons for non-emphasized fields
        # Q4 appears only in "(+N more)" if compacted
        assert "Q4" not in result or "+1 more" in result

    def test_decision_log_shows_last_five_entries(self) -> None:
        decisions = [f"Decision {i}" for i in range(10)]
        baton = Baton(goal="G", decision_log=decisions)
        result = baton.to_prompt_section()
        # Most recent 5 decisions (index 5-9) should appear
        for i in range(5, 10):
            assert f"Decision {i}" in result
        # Older decisions should not appear
        assert "Decision 0" not in result

    def test_artifacts_rendered_with_inline_format(self) -> None:
        ref = ArtifactRef(id="art-9999", hash="xyz123" * 4, type="plan")
        baton = Baton(goal="G", artifacts=[ref])
        result = baton.to_prompt_section()
        assert "art-9999" in result


# ---------------------------------------------------------------------------
# Baton.apply_patch
# ---------------------------------------------------------------------------


class TestApplyPatch:
    def test_patch_updates_goal(self) -> None:
        baton = Baton(goal="Old goal")
        updated = baton.apply_patch({"goal": "New goal"})
        assert updated.goal == "New goal"

    def test_patch_replaces_list_entirely(self) -> None:
        baton = Baton(goal="G", current_state=["old state"])
        updated = baton.apply_patch({"current_state": ["new state A", "new state B"]})
        assert updated.current_state == ["new state A", "new state B"]

    def test_patch_none_resets_list_to_empty(self) -> None:
        baton = Baton(goal="G", constraints=["hard rule"])
        updated = baton.apply_patch({"constraints": None})
        assert updated.constraints == []

    def test_patch_ignores_unknown_keys(self) -> None:
        baton = Baton(goal="G")
        # Should not raise, unknown key is silently dropped
        updated = baton.apply_patch({"nonexistent_field": "value"})
        assert updated.goal == "G"

    def test_original_baton_is_not_mutated(self) -> None:
        baton = Baton(goal="Original")
        baton.apply_patch({"goal": "Mutated"})
        assert baton.goal == "Original"

    def test_patch_preserves_unpatched_fields(self) -> None:
        baton = Baton(goal="G", constraints=["stay"], work_scope=["src/app.py"])
        updated = baton.apply_patch({"goal": "Updated G"})
        assert updated.constraints == ["stay"]
        assert updated.work_scope == ["src/app.py"]


# ---------------------------------------------------------------------------
# Baton serialization round-trip
# ---------------------------------------------------------------------------


class TestSerialization:
    def test_to_json_and_from_json_roundtrip(self) -> None:
        baton = Baton(
            goal="Round-trip goal",
            current_state=["state 1"],
            decision_log=["decided X"],
            constraints=["no regressions"],
        )
        json_str = baton.to_json()
        restored = Baton.from_json(json_str)

        assert restored.goal == baton.goal
        assert restored.current_state == baton.current_state
        assert restored.decision_log == baton.decision_log
        assert restored.constraints == baton.constraints

    def test_from_dict_creates_baton_correctly(self) -> None:
        data = {
            "goal": "Dict goal",
            "current_state": ["in progress"],
            "decision_log": [],
            "open_questions": [],
            "constraints": ["rule 1"],
            "artifacts": [],
            "work_scope": ["src/"],
            "acceptance": [],
            "stage_hints": {},
            "quality_signals": {},
        }
        baton = Baton.from_dict(data)
        assert baton.goal == "Dict goal"
        assert baton.work_scope == ["src/"]
        assert baton.constraints == ["rule 1"]

    def test_to_json_excludes_none_values(self) -> None:
        baton = Baton(goal="G")
        json_str = baton.to_json()
        assert "null" not in json_str

    def test_from_json_handles_minimal_payload(self) -> None:
        json_str = '{"goal": "Minimal"}'
        baton = Baton.from_json(json_str)
        assert baton.goal == "Minimal"
        assert baton.current_state == []


# ---------------------------------------------------------------------------
# Baton.apply_patch — stage_hints and quality_signals
# ---------------------------------------------------------------------------


class TestApplyPatchDictFields:
    def test_patch_replaces_stage_hints(self) -> None:
        baton = Baton(goal="G", stage_hints={"implement": "focus on auth"})
        updated = baton.apply_patch({"stage_hints": {"review": "check edge cases"}})
        assert updated.stage_hints == {"review": "check edge cases"}
        assert "implement" not in updated.stage_hints

    def test_patch_replaces_quality_signals(self) -> None:
        baton = Baton(goal="G", quality_signals={"test_count": 42})
        updated = baton.apply_patch({"quality_signals": {"lint_issues": 0}})
        assert updated.quality_signals == {"lint_issues": 0}

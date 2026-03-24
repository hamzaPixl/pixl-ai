"""Tests for state machine, guards, engine, effects, and workflow bridge."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pixl.state.effects import (
    AddTransitionNote,
    ClearBlockedFields,
    RecordTransition,
    SetBlockedFields,
    SetTimestamps,
)
from pixl.state.engine import TransitionEngine, TransitionResult
from pixl.state.guards import (
    BlockReasonRequired,
    DependenciesMet,
    EpicAllFeaturesDone,
    EpicHasFeatures,
    GuardResult,
    HasPlan,
    RoadmapAllEpicsDone,
    RoadmapHasEpics,
    Severity,
)
from pixl.state.machine import (
    EPIC_MACHINE,
    FEATURE_MACHINE,
    MACHINES,
    ROADMAP_MACHINE,
    Transition,
    get_machine,
)
from pixl.state.workflow_bridge import (
    TransitionSpec,
    WorkflowStateBridge,
    _match_implicit,
)

# ---------------------------------------------------------------------------
# StateMachine / Transition
# ---------------------------------------------------------------------------


class TestTransition:
    def test_equality_same_values(self) -> None:
        assert Transition("backlog", "planned") == Transition("backlog", "planned")

    def test_inequality_different_from(self) -> None:
        assert Transition("backlog", "planned") != Transition("planned", "planned")

    def test_inequality_different_to(self) -> None:
        assert Transition("backlog", "planned") != Transition("backlog", "in_progress")

    def test_repr_contains_arrow(self) -> None:
        t = Transition("backlog", "planned")
        assert "→" in repr(t)
        assert "backlog" in repr(t)
        assert "planned" in repr(t)

    def test_hashable_for_set_membership(self) -> None:
        s = {Transition("a", "b"), Transition("a", "b")}
        assert len(s) == 1


class TestStateMachineIsAllowed:
    def test_allowed_transition_returns_true(self) -> None:
        assert FEATURE_MACHINE.is_allowed("backlog", "planned")

    def test_disallowed_transition_returns_false(self) -> None:
        # done → planned is not in the feature machine
        assert not FEATURE_MACHINE.is_allowed("done", "planned")

    def test_same_state_is_not_a_defined_transition(self) -> None:
        # No self-loops defined
        assert not FEATURE_MACHINE.is_allowed("backlog", "backlog")


class TestStateMachineGetReachable:
    def test_backlog_can_reach_planned_and_in_progress(self) -> None:
        reachable = FEATURE_MACHINE.get_reachable("backlog")
        assert "planned" in reachable
        assert "in_progress" in reachable

    def test_done_can_reach_in_progress_for_rework(self) -> None:
        reachable = FEATURE_MACHINE.get_reachable("done")
        assert "in_progress" in reachable

    def test_unknown_status_returns_empty_set(self) -> None:
        assert FEATURE_MACHINE.get_reachable("nonexistent") == set()


class TestStateMachineGetAllStatuses:
    def test_feature_machine_contains_expected_statuses(self) -> None:
        statuses = FEATURE_MACHINE.get_all_statuses()
        for expected in (
            "backlog",
            "planned",
            "in_progress",
            "review",
            "done",
            "blocked",
            "failed",
            "deferred",
        ):
            assert expected in statuses

    def test_epic_machine_contains_expected_statuses(self) -> None:
        statuses = EPIC_MACHINE.get_all_statuses()
        for expected in ("drafting", "decomposed", "in_progress", "completed", "failed"):
            assert expected in statuses

    def test_roadmap_machine_contains_expected_statuses(self) -> None:
        statuses = ROADMAP_MACHINE.get_all_statuses()
        for expected in ("drafting", "planned", "in_progress", "completed", "failed"):
            assert expected in statuses


class TestFeatureMachineTransitions:
    """Verify specific allowed / disallowed feature transitions."""

    @pytest.mark.parametrize(
        "from_s,to_s",
        [
            ("backlog", "planned"),
            ("planned", "in_progress"),
            ("in_progress", "review"),
            ("review", "done"),
            ("backlog", "in_progress"),  # skip plan
            ("review", "in_progress"),  # back to work
            ("in_progress", "blocked"),
            ("blocked", "in_progress"),
            ("blocked", "backlog"),
            ("in_progress", "failed"),
            ("failed", "backlog"),
            ("done", "in_progress"),  # rework
            ("backlog", "deferred"),
            ("deferred", "backlog"),
            ("deferred", "planned"),
        ],
    )
    def test_allowed(self, from_s: str, to_s: str) -> None:
        assert FEATURE_MACHINE.is_allowed(from_s, to_s)

    @pytest.mark.parametrize(
        "from_s,to_s",
        [
            ("done", "backlog"),  # not listed
            ("done", "planned"),
            ("review", "backlog"),
            ("in_progress", "deferred"),
            ("deferred", "in_progress"),  # not listed
        ],
    )
    def test_disallowed(self, from_s: str, to_s: str) -> None:
        assert not FEATURE_MACHINE.is_allowed(from_s, to_s)


class TestEpicMachineTransitions:
    @pytest.mark.parametrize(
        "from_s,to_s",
        [
            ("drafting", "decomposed"),
            ("decomposed", "in_progress"),
            ("in_progress", "completed"),
            ("drafting", "in_progress"),
            ("in_progress", "failed"),
            ("failed", "drafting"),
        ],
    )
    def test_allowed(self, from_s: str, to_s: str) -> None:
        assert EPIC_MACHINE.is_allowed(from_s, to_s)

    @pytest.mark.parametrize(
        "from_s,to_s",
        [
            ("completed", "drafting"),
            ("drafting", "completed"),
        ],
    )
    def test_disallowed(self, from_s: str, to_s: str) -> None:
        assert not EPIC_MACHINE.is_allowed(from_s, to_s)


class TestRoadmapMachineTransitions:
    @pytest.mark.parametrize(
        "from_s,to_s",
        [
            ("drafting", "planned"),
            ("planned", "in_progress"),
            ("in_progress", "completed"),
            ("drafting", "in_progress"),
            ("planned", "completed"),
            ("in_progress", "failed"),
            ("failed", "drafting"),
        ],
    )
    def test_allowed(self, from_s: str, to_s: str) -> None:
        assert ROADMAP_MACHINE.is_allowed(from_s, to_s)

    def test_disallowed_completed_to_planned(self) -> None:
        assert not ROADMAP_MACHINE.is_allowed("completed", "planned")


class TestGetMachine:
    def test_returns_feature_machine_for_feat_prefix(self) -> None:
        machine = get_machine("feat-001")
        assert machine is FEATURE_MACHINE

    def test_returns_epic_machine_for_epic_prefix(self) -> None:
        machine = get_machine("epic-001")
        assert machine is EPIC_MACHINE

    def test_returns_roadmap_machine_for_roadmap_prefix(self) -> None:
        machine = get_machine("roadmap-001")
        assert machine is ROADMAP_MACHINE

    def test_raises_for_unknown_prefix(self) -> None:
        with pytest.raises(ValueError, match="Unknown entity prefix"):
            get_machine("unknown-001")

    def test_machines_registry_has_all_three_types(self) -> None:
        assert "feature" in MACHINES
        assert "epic" in MACHINES
        assert "roadmap" in MACHINES


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------


def _make_store() -> MagicMock:
    return MagicMock()


class TestGuardResult:
    def test_ok_result_is_passed(self) -> None:
        r = GuardResult.ok("my_guard")
        assert r.passed is True
        assert r.guard_name == "my_guard"

    def test_fail_result_is_not_passed(self) -> None:
        r = GuardResult.fail("my_guard", "some reason")
        assert r.passed is False
        assert r.reason == "some reason"

    def test_fail_defaults_to_hard_severity(self) -> None:
        r = GuardResult.fail("g", "reason")
        assert r.severity == Severity.HARD

    def test_fail_accepts_soft_severity(self) -> None:
        r = GuardResult.fail("g", "reason", severity=Severity.SOFT)
        assert r.severity == Severity.SOFT


class TestDependenciesMetGuard:
    def test_passes_when_transitioning_to_other_status(self) -> None:
        guard = DependenciesMet()
        store = _make_store()
        result = guard.check({"id": "feat-001"}, "planned", store)
        assert result.passed
        store.check_dependencies_met.assert_not_called()

    def test_passes_when_all_dependencies_met(self) -> None:
        guard = DependenciesMet()
        store = _make_store()
        store.check_dependencies_met.return_value = (True, [])
        result = guard.check({"id": "feat-001"}, "in_progress", store)
        assert result.passed

    def test_fails_when_dependencies_not_met(self) -> None:
        guard = DependenciesMet()
        store = _make_store()
        store.check_dependencies_met.return_value = (False, ["feat-002", "feat-003"])
        result = guard.check({"id": "feat-001"}, "in_progress", store)
        assert not result.passed
        assert "feat-002" in (result.reason or "")

    def test_severity_is_hard(self) -> None:
        assert DependenciesMet.severity == Severity.HARD


class TestHasPlanGuard:
    def test_passes_when_transitioning_to_other_status(self) -> None:
        guard = HasPlan()
        store = _make_store()
        result = guard.check({"id": "feat-001"}, "review", store)
        assert result.passed

    def test_passes_when_plan_path_set(self) -> None:
        guard = HasPlan()
        store = _make_store()
        result = guard.check({"id": "feat-001", "plan_path": "/some/plan.md"}, "in_progress", store)
        assert result.passed

    def test_fails_softly_when_no_plan_path(self) -> None:
        guard = HasPlan()
        store = _make_store()
        result = guard.check({"id": "feat-001"}, "in_progress", store)
        assert not result.passed
        assert result.severity == Severity.SOFT

    def test_severity_is_soft(self) -> None:
        assert HasPlan.severity == Severity.SOFT


class TestBlockReasonRequiredGuard:
    def test_passes_when_not_transitioning_to_blocked(self) -> None:
        guard = BlockReasonRequired()
        store = _make_store()
        result = guard.check({"id": "feat-001"}, "planned", store)
        assert result.passed

    def test_passes_when_blocked_by_is_set(self) -> None:
        guard = BlockReasonRequired()
        store = _make_store()
        result = guard.check({"id": "feat-001", "blocked_by": "feat-002"}, "blocked", store)
        assert result.passed

    def test_passes_when_blocked_reason_is_set(self) -> None:
        guard = BlockReasonRequired()
        store = _make_store()
        result = guard.check(
            {"id": "feat-001", "blocked_reason": "waiting for API"}, "blocked", store
        )
        assert result.passed

    def test_fails_softly_when_no_blocked_context(self) -> None:
        guard = BlockReasonRequired()
        store = _make_store()
        result = guard.check({"id": "feat-001"}, "blocked", store)
        assert not result.passed
        assert result.severity == Severity.SOFT

    def test_severity_is_soft(self) -> None:
        assert BlockReasonRequired.severity == Severity.SOFT


class TestEpicHasFeaturesGuard:
    def test_passes_when_transitioning_to_unrelated_status(self) -> None:
        guard = EpicHasFeatures()
        result = guard.check({"id": "epic-001", "feature_ids": []}, "failed", _make_store())
        assert result.passed

    def test_passes_when_features_present_and_going_to_decomposed(self) -> None:
        guard = EpicHasFeatures()
        result = guard.check(
            {"id": "epic-001", "feature_ids": ["feat-001"]}, "decomposed", _make_store()
        )
        assert result.passed

    def test_fails_when_no_features_and_going_to_in_progress(self) -> None:
        guard = EpicHasFeatures()
        result = guard.check({"id": "epic-001", "feature_ids": []}, "in_progress", _make_store())
        assert not result.passed

    def test_fails_when_feature_ids_missing_from_entity(self) -> None:
        guard = EpicHasFeatures()
        result = guard.check({"id": "epic-001"}, "decomposed", _make_store())
        assert not result.passed

    def test_severity_is_hard(self) -> None:
        assert EpicHasFeatures.severity == Severity.HARD


class TestEpicAllFeaturesDoneGuard:
    def test_passes_when_not_transitioning_to_completed(self) -> None:
        guard = EpicAllFeaturesDone()
        result = guard.check({"id": "epic-001"}, "in_progress", _make_store())
        assert result.passed

    def test_passes_when_no_features(self) -> None:
        guard = EpicAllFeaturesDone()
        result = guard.check({"id": "epic-001", "feature_ids": []}, "completed", _make_store())
        assert result.passed

    def test_passes_when_all_features_done(self) -> None:
        guard = EpicAllFeaturesDone()
        entity = {
            "id": "epic-001",
            "feature_ids": ["feat-001", "feat-002"],
            "progress": {"total": 2, "done": 2},
        }
        result = guard.check(entity, "completed", _make_store())
        assert result.passed

    def test_fails_when_some_features_not_done(self) -> None:
        guard = EpicAllFeaturesDone()
        entity = {
            "id": "epic-001",
            "feature_ids": ["feat-001", "feat-002", "feat-003"],
            "progress": {"total": 3, "done": 1},
        }
        result = guard.check(entity, "completed", _make_store())
        assert not result.passed
        assert "2 of 3" in (result.reason or "")

    def test_severity_is_hard(self) -> None:
        assert EpicAllFeaturesDone.severity == Severity.HARD


class TestRoadmapHasEpicsGuard:
    def test_passes_when_not_transitioning_to_planned_or_in_progress(self) -> None:
        guard = RoadmapHasEpics()
        result = guard.check({"id": "roadmap-001", "epic_ids": []}, "failed", _make_store())
        assert result.passed

    def test_passes_when_epics_present(self) -> None:
        guard = RoadmapHasEpics()
        result = guard.check(
            {"id": "roadmap-001", "epic_ids": ["epic-001"]}, "planned", _make_store()
        )
        assert result.passed

    def test_fails_when_no_epics_and_going_to_planned(self) -> None:
        guard = RoadmapHasEpics()
        result = guard.check({"id": "roadmap-001", "epic_ids": []}, "planned", _make_store())
        assert not result.passed

    def test_fails_when_no_epics_and_going_to_in_progress(self) -> None:
        guard = RoadmapHasEpics()
        result = guard.check({"id": "roadmap-001", "epic_ids": []}, "in_progress", _make_store())
        assert not result.passed

    def test_severity_is_hard(self) -> None:
        assert RoadmapHasEpics.severity == Severity.HARD


class TestRoadmapAllEpicsDoneGuard:
    def test_passes_when_not_transitioning_to_completed(self) -> None:
        guard = RoadmapAllEpicsDone()
        result = guard.check({"id": "roadmap-001"}, "in_progress", _make_store())
        assert result.passed

    def test_passes_when_no_epics(self) -> None:
        guard = RoadmapAllEpicsDone()
        result = guard.check({"id": "roadmap-001", "epic_ids": []}, "completed", _make_store())
        assert result.passed

    def test_passes_when_all_epics_completed(self) -> None:
        guard = RoadmapAllEpicsDone()
        store = _make_store()
        store.get_epic.side_effect = lambda eid: {"id": eid, "status": "completed"}
        entity = {"id": "roadmap-001", "epic_ids": ["epic-001", "epic-002"]}
        result = guard.check(entity, "completed", store)
        assert result.passed

    def test_fails_when_some_epics_not_completed(self) -> None:
        guard = RoadmapAllEpicsDone()
        store = _make_store()
        store.get_epic.side_effect = lambda eid: {
            "id": eid,
            "status": "in_progress" if eid == "epic-002" else "completed",
        }
        entity = {"id": "roadmap-001", "epic_ids": ["epic-001", "epic-002"]}
        result = guard.check(entity, "completed", store)
        assert not result.passed
        assert "epic-002" in (result.reason or "")

    def test_severity_is_hard(self) -> None:
        assert RoadmapAllEpicsDone.severity == Severity.HARD


# ---------------------------------------------------------------------------
# TransitionEngine
# ---------------------------------------------------------------------------


def _make_feature_entity(
    entity_id: str = "feat-001",
    status: str = "backlog",
    **kwargs,
) -> dict:
    return {"id": entity_id, "status": status, **kwargs}


def _make_epic_entity(
    entity_id: str = "epic-001",
    status: str = "drafting",
    **kwargs,
) -> dict:
    return {"id": entity_id, "status": status, **kwargs}


def _make_store_with_entity(entity: dict, entity_type: str = "feature") -> MagicMock:
    store = MagicMock()
    store._conn = MagicMock()
    store._conn.execute.return_value = MagicMock()
    if entity_type == "feature":
        store.get_feature.return_value = entity
        store.get_epic.return_value = None
        store.get_roadmap.return_value = None
    elif entity_type == "epic":
        store.get_feature.return_value = None
        store.get_epic.return_value = entity
        store.get_roadmap.return_value = None
    elif entity_type == "roadmap":
        store.get_feature.return_value = None
        store.get_epic.return_value = None
        store.get_roadmap.return_value = entity
    store.check_dependencies_met.return_value = (True, [])
    return store


def _make_engine_no_effects(store: MagicMock, entity_type: str = "feature") -> TransitionEngine:
    """Engine with empty effects to avoid DB side-effect calls."""
    return TransitionEngine(store, effects=[])


class TestTransitionEngineTransition:
    def test_returns_success_for_valid_transition(self) -> None:
        entity = _make_feature_entity(status="backlog")
        store = _make_store_with_entity(entity)
        engine = _make_engine_no_effects(store)

        result = engine.transition("feat-001", "planned")
        assert result.success is True
        assert result.from_status == "backlog"
        assert result.to_status == "planned"

    def test_returns_success_true_for_same_status_noop(self) -> None:
        entity = _make_feature_entity(status="backlog")
        store = _make_store_with_entity(entity)
        engine = _make_engine_no_effects(store)

        result = engine.transition("feat-001", "backlog")
        assert result.success is True
        # No DB write for no-op
        store._conn.execute.assert_not_called()

    def test_fails_for_unknown_entity_prefix(self) -> None:
        store = _make_store()
        engine = _make_engine_no_effects(store)

        result = engine.transition("unknown-001", "done")
        assert result.success is False
        assert "Unknown entity type" in (result.error or "")

    def test_fails_when_entity_not_found(self) -> None:
        store = _make_store()
        store.get_feature.return_value = None
        engine = _make_engine_no_effects(store)

        result = engine.transition("feat-001", "planned")
        assert result.success is False
        assert "not found" in (result.error or "")

    def test_fails_for_disallowed_transition(self) -> None:
        entity = _make_feature_entity(status="done")
        store = _make_store_with_entity(entity)
        engine = _make_engine_no_effects(store)

        result = engine.transition("feat-001", "backlog")
        assert result.success is False
        assert "not allowed" in (result.error or "")

    def test_fails_when_hard_guard_fails(self) -> None:
        entity = _make_feature_entity(status="backlog")
        store = _make_store_with_entity(entity)
        store.check_dependencies_met.return_value = (False, ["feat-002"])
        engine = _make_engine_no_effects(store)

        result = engine.transition("feat-001", "in_progress")
        assert result.success is False
        assert result.hard_failures

    def test_succeeds_with_soft_guard_warning(self) -> None:
        # No plan_path → HasPlan soft warning but should still succeed
        entity = _make_feature_entity(status="backlog")
        store = _make_store_with_entity(entity)
        store.check_dependencies_met.return_value = (True, [])
        engine = _make_engine_no_effects(store)

        result = engine.transition("feat-001", "in_progress")
        assert result.success is True
        assert result.warnings  # HasPlan fires as a warning

    def test_persists_status_change(self) -> None:
        entity = _make_feature_entity(status="backlog")
        store = _make_store_with_entity(entity)
        engine = _make_engine_no_effects(store)

        engine.transition("feat-001", "planned")
        store._conn.execute.assert_called_once()
        call_args = store._conn.execute.call_args[0]
        assert "planned" in call_args[1]

    def test_result_contains_entity_id(self) -> None:
        entity = _make_feature_entity(status="backlog")
        store = _make_store_with_entity(entity)
        engine = _make_engine_no_effects(store)

        result = engine.transition("feat-001", "planned")
        assert result.entity_id == "feat-001"


class TestTransitionEngineCanTransition:
    def test_returns_true_for_valid_transition(self) -> None:
        entity = _make_feature_entity(status="backlog")
        store = _make_store_with_entity(entity)
        engine = _make_engine_no_effects(store)

        can, reasons = engine.can_transition("feat-001", "planned")
        assert can is True
        assert reasons == []

    def test_returns_true_for_same_status(self) -> None:
        entity = _make_feature_entity(status="backlog")
        store = _make_store_with_entity(entity)
        engine = _make_engine_no_effects(store)

        can, reasons = engine.can_transition("feat-001", "backlog")
        assert can is True

    def test_returns_false_for_disallowed_transition(self) -> None:
        entity = _make_feature_entity(status="done")
        store = _make_store_with_entity(entity)
        engine = _make_engine_no_effects(store)

        can, reasons = engine.can_transition("feat-001", "backlog")
        assert can is False
        assert reasons

    def test_returns_false_for_unknown_entity(self) -> None:
        store = _make_store()
        store.get_feature.return_value = None
        engine = _make_engine_no_effects(store)

        can, reasons = engine.can_transition("feat-001", "planned")
        assert can is False

    def test_returns_false_when_hard_guard_blocks(self) -> None:
        entity = _make_feature_entity(status="backlog")
        store = _make_store_with_entity(entity)
        store.check_dependencies_met.return_value = (False, ["feat-002"])
        engine = _make_engine_no_effects(store)

        can, reasons = engine.can_transition("feat-001", "in_progress")
        assert can is False
        assert reasons


class TestTransitionEngineGetAvailableTransitions:
    def test_returns_list_for_feature_in_backlog(self) -> None:
        entity = _make_feature_entity(status="backlog")
        store = _make_store_with_entity(entity)
        store.check_dependencies_met.return_value = (True, [])
        engine = _make_engine_no_effects(store)

        available = engine.get_available_transitions("feat-001")
        assert isinstance(available, list)
        assert "planned" in available

    def test_returns_empty_for_unknown_entity_type(self) -> None:
        store = _make_store()
        engine = _make_engine_no_effects(store)

        available = engine.get_available_transitions("unknown-001")
        assert available == []

    def test_returns_empty_when_entity_not_found(self) -> None:
        store = _make_store()
        store.get_feature.return_value = None
        engine = _make_engine_no_effects(store)

        available = engine.get_available_transitions("feat-001")
        assert available == []


class TestTransitionEngineGuardAndEffectRegistration:
    def test_register_guard_appends_to_type(self) -> None:
        store = _make_store()
        engine = TransitionEngine(store, guards={}, effects=[])

        custom_guard = MagicMock()
        custom_guard.name = "custom"
        engine.register_guard("feature", custom_guard)

        assert custom_guard in engine._guards["feature"]

    def test_register_effect_appends_to_list(self) -> None:
        store = _make_store()
        engine = TransitionEngine(store, guards={}, effects=[])

        custom_effect = MagicMock()
        engine.register_effect(custom_effect)

        assert custom_effect in engine._effects


class TestTransitionResultProperties:
    def test_warnings_returns_only_soft_failures(self) -> None:
        hard_fail = GuardResult.fail("g1", "hard reason", severity=Severity.HARD)
        soft_fail = GuardResult.fail("g2", "soft reason", severity=Severity.SOFT)
        ok = GuardResult.ok("g3")

        result = TransitionResult(
            success=False,
            entity_id="feat-001",
            from_status="backlog",
            to_status="in_progress",
            guard_results=[hard_fail, soft_fail, ok],
        )
        assert result.warnings == [soft_fail]

    def test_hard_failures_returns_only_hard_failures(self) -> None:
        hard_fail = GuardResult.fail("g1", "hard reason", severity=Severity.HARD)
        soft_fail = GuardResult.fail("g2", "soft reason", severity=Severity.SOFT)

        result = TransitionResult(
            success=False,
            entity_id="feat-001",
            from_status="backlog",
            to_status="in_progress",
            guard_results=[hard_fail, soft_fail],
        )
        assert result.hard_failures == [hard_fail]


# ---------------------------------------------------------------------------
# Effects
# ---------------------------------------------------------------------------


class TestSetTimestampsEffect:
    def test_sets_planned_at_for_feature(self) -> None:
        effect = SetTimestamps()
        store = MagicMock()
        result = effect.execute("feature", "feat-001", "backlog", "planned", store, {})
        assert result.applied is True
        assert result.detail == "set planned_at"
        store.update_feature.assert_called_once()
        kwargs = store.update_feature.call_args[1]
        assert "planned_at" in kwargs

    def test_sets_started_at_when_in_progress(self) -> None:
        effect = SetTimestamps()
        store = MagicMock()
        effect.execute("feature", "feat-001", "planned", "in_progress", store, {})
        store.update_feature.assert_called_once()
        kwargs = store.update_feature.call_args[1]
        assert "started_at" in kwargs

    def test_sets_completed_at_for_epic(self) -> None:
        effect = SetTimestamps()
        store = MagicMock()
        result = effect.execute("epic", "epic-001", "in_progress", "completed", store, {})
        assert result.applied is True
        store.update_epic.assert_called_once()

    def test_not_applied_when_no_timestamp_mapping(self) -> None:
        effect = SetTimestamps()
        store = MagicMock()
        result = effect.execute("feature", "feat-001", "backlog", "blocked", store, {})
        assert result.applied is False

    def test_not_applied_for_unknown_entity_type(self) -> None:
        effect = SetTimestamps()
        store = MagicMock()
        result = effect.execute("unknown", "unk-001", "a", "b", store, {})
        assert result.applied is False


class TestAddTransitionNoteEffect:
    def test_adds_note_when_provided_in_context(self) -> None:
        effect = AddTransitionNote()
        store = MagicMock()
        result = effect.execute("feature", "feat-001", "backlog", "planned", store, {"note": "hi"})
        assert result.applied is True
        store.add_note.assert_called_once_with("feature", "feat-001", "hi")

    def test_not_applied_when_no_note_in_context(self) -> None:
        effect = AddTransitionNote()
        store = MagicMock()
        result = effect.execute("feature", "feat-001", "backlog", "planned", store, {})
        assert result.applied is False
        store.add_note.assert_not_called()

    def test_not_applied_when_note_is_empty_string(self) -> None:
        effect = AddTransitionNote()
        store = MagicMock()
        result = effect.execute("feature", "feat-001", "backlog", "planned", store, {"note": ""})
        assert result.applied is False


class TestClearBlockedFieldsEffect:
    def test_clears_fields_when_unblocking_feature(self) -> None:
        effect = ClearBlockedFields()
        store = MagicMock()
        result = effect.execute("feature", "feat-001", "blocked", "backlog", store, {})
        assert result.applied is True
        store.update_feature.assert_called_once_with(
            "feat-001", blocked_by=None, blocked_reason=None
        )

    def test_not_applied_when_old_status_is_not_blocked(self) -> None:
        effect = ClearBlockedFields()
        store = MagicMock()
        result = effect.execute("feature", "feat-001", "backlog", "planned", store, {})
        assert result.applied is False
        store.update_feature.assert_not_called()

    def test_not_applied_for_non_feature_entity(self) -> None:
        effect = ClearBlockedFields()
        store = MagicMock()
        result = effect.execute("epic", "epic-001", "blocked", "drafting", store, {})
        assert result.applied is False


class TestSetBlockedFieldsEffect:
    def test_sets_blocked_by_from_context(self) -> None:
        effect = SetBlockedFields()
        store = MagicMock()
        result = effect.execute(
            "feature", "feat-001", "backlog", "blocked", store, {"blocked_by": "feat-002"}
        )
        assert result.applied is True
        store.update_feature.assert_called_once()
        kwargs = store.update_feature.call_args[1]
        assert kwargs.get("blocked_by") == "feat-002"

    def test_sets_blocked_reason_from_context(self) -> None:
        effect = SetBlockedFields()
        store = MagicMock()
        result = effect.execute(
            "feature", "feat-001", "backlog", "blocked", store, {"blocked_reason": "API down"}
        )
        assert result.applied is True
        kwargs = store.update_feature.call_args[1]
        assert kwargs.get("blocked_reason") == "API down"

    def test_not_applied_when_new_status_is_not_blocked(self) -> None:
        effect = SetBlockedFields()
        store = MagicMock()
        result = effect.execute("feature", "feat-001", "backlog", "planned", store, {})
        assert result.applied is False

    def test_not_applied_for_non_feature_entity(self) -> None:
        effect = SetBlockedFields()
        store = MagicMock()
        result = effect.execute("epic", "epic-001", "drafting", "blocked", store, {})
        assert result.applied is False

    def test_not_applied_when_no_blocking_context(self) -> None:
        effect = SetBlockedFields()
        store = MagicMock()
        result = effect.execute("feature", "feat-001", "backlog", "blocked", store, {})
        assert result.applied is False


class TestRecordTransitionEffect:
    def test_inserts_row_into_state_transitions(self) -> None:
        effect = RecordTransition()
        store = MagicMock()
        store._conn = MagicMock()
        result = effect.execute(
            "feature", "feat-001", "backlog", "planned", store, {"trigger": "user"}
        )
        assert result.applied is True
        store._conn.execute.assert_called_once()
        sql = store._conn.execute.call_args[0][0]
        assert "INSERT INTO state_transitions" in sql

    def test_uses_default_trigger_when_not_provided(self) -> None:
        effect = RecordTransition()
        store = MagicMock()
        store._conn = MagicMock()
        effect.execute("feature", "feat-001", "backlog", "planned", store, {})
        params = store._conn.execute.call_args[0][1]
        # trigger is 5th param in the SQL tuple
        assert params[4] == "user"

    def test_includes_session_id_in_metadata_when_provided(self) -> None:
        effect = RecordTransition()
        store = MagicMock()
        store._conn = MagicMock()
        effect.execute(
            "feature", "feat-001", "backlog", "planned", store, {"session_id": "sess-abc"}
        )
        params = store._conn.execute.call_args[0][1]
        metadata_json = params[6]
        assert metadata_json is not None
        import json

        metadata = json.loads(metadata_json)
        assert metadata.get("session_id") == "sess-abc"


# ---------------------------------------------------------------------------
# WorkflowStateBridge
# ---------------------------------------------------------------------------


class TestMatchImplicit:
    def test_exact_match_returns_mapping(self) -> None:
        result = _match_implicit("implement")
        assert "on_start" in result
        assert "on_complete" in result

    def test_suffix_match_works(self) -> None:
        result = _match_implicit("tdd-implement")
        assert "on_start" in result
        assert result["on_start"] == "in_progress"

    def test_unknown_stage_returns_empty(self) -> None:
        result = _match_implicit("unknown-stage-xyz")
        assert result == {}

    def test_plan_stage_maps_on_complete_to_planned(self) -> None:
        result = _match_implicit("plan")
        assert result.get("on_complete") == "planned"

    def test_decompose_stage_maps_on_complete_to_decomposed(self) -> None:
        result = _match_implicit("decompose")
        assert result.get("on_complete") == "decomposed"

    def test_complete_stage_maps_on_complete_to_done(self) -> None:
        result = _match_implicit("complete")
        assert result.get("on_complete") == "done"


class TestTransitionSpec:
    def test_from_config_with_string(self) -> None:
        spec = TransitionSpec.from_config("in_progress")
        assert spec.status == "in_progress"
        assert spec.note is None

    def test_from_config_with_dict(self) -> None:
        spec = TransitionSpec.from_config({"status": "review", "note": "done"})
        assert spec.status == "review"
        assert spec.note == "done"

    def test_from_config_with_extra_context(self) -> None:
        spec = TransitionSpec.from_config({"status": "blocked", "blocked_by": "feat-002"})
        assert spec.extra_context.get("blocked_by") == "feat-002"

    def test_from_config_excludes_status_from_extra_context(self) -> None:
        spec = TransitionSpec.from_config({"status": "planned", "note": "x"})
        assert "status" not in spec.extra_context
        assert "note" not in spec.extra_context


class TestWorkflowStateBridge:
    def _make_bridge(self) -> tuple[WorkflowStateBridge, MagicMock]:
        engine = MagicMock()
        engine.transition.return_value = TransitionResult(
            success=True,
            entity_id="feat-001",
            from_status="backlog",
            to_status="in_progress",
        )
        bridge = WorkflowStateBridge(engine)
        return bridge, engine

    def test_on_stage_start_triggers_on_start_event(self) -> None:
        bridge, engine = self._make_bridge()
        result = bridge.on_stage_start("feat-001", "implement")
        engine.transition.assert_called_once()
        assert result is not None
        assert result.to_status == "in_progress"

    def test_on_stage_complete_triggers_on_complete_event(self) -> None:
        bridge, engine = self._make_bridge()
        engine.transition.return_value = TransitionResult(
            success=True,
            entity_id="feat-001",
            from_status="in_progress",
            to_status="review",
        )
        result = bridge.on_stage_complete("feat-001", "implement")
        assert result is not None
        assert result.to_status == "review"

    def test_returns_none_when_no_transition_mapped(self) -> None:
        bridge, engine = self._make_bridge()
        result = bridge.on_stage_start("feat-001", "some-unmapped-stage-xyz")
        assert result is None
        engine.transition.assert_not_called()

    def test_explicit_config_overrides_implicit_map(self) -> None:
        bridge, engine = self._make_bridge()
        stage_config = {"transitions": {"on_complete": {"status": "done", "note": "custom done"}}}
        bridge.on_stage_complete("feat-001", "implement", stage_config=stage_config)
        call_args = engine.transition.call_args
        assert call_args[0][1] == "done"

    def test_resolve_target_status_returns_spec_for_known_stage(self) -> None:
        bridge, _ = self._make_bridge()
        spec = bridge.resolve_target_status("on_complete", "plan")
        assert spec is not None
        assert spec.status == "planned"

    def test_resolve_target_status_returns_none_for_unknown_stage(self) -> None:
        bridge, _ = self._make_bridge()
        spec = bridge.resolve_target_status("on_complete", "unknown-xyz")
        assert spec is None

    def test_event_callback_not_called_on_failure(self) -> None:
        engine = MagicMock()
        engine.transition.return_value = TransitionResult(
            success=False,
            entity_id="feat-001",
            from_status="backlog",
            to_status="in_progress",
            error="guard blocked",
        )
        callback = MagicMock()
        bridge = WorkflowStateBridge(engine, event_callback=callback)
        bridge.on_stage_start("feat-001", "implement")
        callback.assert_not_called()

    def test_set_session_id_updates_internal_session_id(self) -> None:
        bridge, _ = self._make_bridge()
        bridge.set_session_id("sess-xyz")
        assert bridge._session_id == "sess-xyz"

    def test_set_event_callback_replaces_callback(self) -> None:
        bridge, _ = self._make_bridge()
        new_cb = MagicMock()
        bridge.set_event_callback(new_cb)
        assert bridge._event_callback is new_cb

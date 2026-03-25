"""Tests for config/workflow_loader.py — YAML workflow loading and graph conversion.

Tests cover:
- WorkflowLoadError construction
- ModelValidationResult properties
- WorkflowLoader.load_workflow() — ID lookup with precedence, direct path, not-found
- WorkflowLoader.list_workflows() — multi-source enumeration with override
- WorkflowLoader.convert_to_graph() — node/edge construction, loops, validation errors
- WorkflowLoader.validate_models() — valid/invalid/missing models
- Helpers: _describe_model_source, _stage_to_node (gate/hook/task/sub_workflow)
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from pixl.config.workflow_loader import (
    ModelIssueSeverity,
    ModelValidationIssue,
    ModelValidationResult,
    WorkflowLoader,
    WorkflowLoadError,
)
from pixl.models.workflow import EdgeTrigger, NodeType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MINIMAL_YAML = textwrap.dedent("""\
    id: test-wf
    name: Test Workflow
    version: 1.0.0
    stages:
      - id: plan
        name: Plan
        type: task
        agent: architect
""")

_TWO_STAGE_YAML = textwrap.dedent("""\
    id: two-stage
    name: Two-Stage Workflow
    version: 1.0.0
    stages:
      - id: plan
        name: Plan
        type: task
        agent: architect
      - id: implement
        name: Implement
        type: task
        agent: backend-engineer
""")

_GATE_YAML = textwrap.dedent("""\
    id: gate-wf
    name: Gate Workflow
    version: 1.0.0
    stages:
      - id: build
        name: Build
        type: task
        agent: backend-engineer
      - id: review
        name: Review Gate
        type: gate
        timeout_minutes: 60
        timeout_policy: reject
""")

_LOOP_YAML = textwrap.dedent("""\
    id: loop-wf
    name: Loop Workflow
    version: 1.0.0
    stages:
      - id: implement
        name: Implement
        type: task
        agent: backend-engineer
      - id: review
        name: Review Gate
        type: gate
        timeout_minutes: 60
        timeout_policy: reject
    loops:
      - id: fix-loop
        from: review
        to: implement
        trigger: failure
        max_iterations: 3
""")

_HOOK_YAML = textwrap.dedent("""\
    id: hook-wf
    name: Hook Workflow
    version: 1.0.0
    stages:
      - id: notify
        name: Notify
        type: hook
        hook: slack-notify
""")

_SUBWORKFLOW_YAML = textwrap.dedent("""\
    id: sub-wf
    name: Sub Workflow
    version: 1.0.0
    stages:
      - id: child
        name: Child
        type: sub_workflow
        sub_workflow: debug
""")

_EXPLICIT_EDGES_YAML = textwrap.dedent("""\
    id: edges-wf
    name: Edges Workflow
    version: 1.0.0
    stages:
      - id: step-a
        name: Step A
        type: task
        agent: architect
      - id: step-b
        name: Step B
        type: task
        agent: backend-engineer
      - id: step-c
        name: Step C
        type: task
        agent: qa-engineer
    edges:
      step-a: [step-b]
      step-b: [step-c]
""")


def _make_loader(tmp_path: Path) -> WorkflowLoader:
    """Create a WorkflowLoader with all dirs pointing to empty temp paths."""
    global_dir = tmp_path / "global"
    global_dir.mkdir()
    bundled_dir = tmp_path / "bundled"
    bundled_dir.mkdir()
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    pixl_dir = project_dir / ".pixl"
    pixl_dir.mkdir()

    loader = WorkflowLoader(
        project_path=project_dir,
        global_workflows_dir=global_dir,
        bundled_workflows_dir=bundled_dir,
    )
    return loader


def _write_workflow(directory: Path, filename: str, content: str) -> Path:
    """Write a YAML workflow file to a directory."""
    path = directory / filename
    path.write_text(content)
    return path


# ---------------------------------------------------------------------------
# WorkflowLoadError
# ---------------------------------------------------------------------------


class TestWorkflowLoadError:
    def test_message_without_path(self) -> None:
        err = WorkflowLoadError("something went wrong")
        assert "something went wrong" in str(err)
        assert err.path is None

    def test_message_with_path(self) -> None:
        err = WorkflowLoadError("bad yaml", path="/some/path/wf.yaml")
        assert "/some/path/wf.yaml" in str(err)
        assert err.message == "bad yaml"

    def test_path_stored_as_string(self) -> None:
        err = WorkflowLoadError("oops", path=Path("/a/b/c.yaml"))
        assert err.path == "/a/b/c.yaml"

    def test_inherits_from_exception(self) -> None:
        err = WorkflowLoadError("test")
        assert isinstance(err, Exception)


# ---------------------------------------------------------------------------
# ModelValidationResult
# ---------------------------------------------------------------------------


class TestModelValidationResult:
    def _make_issue(self, severity: ModelIssueSeverity) -> ModelValidationIssue:
        return ModelValidationIssue(
            stage_id="stage-1",
            severity=severity,
            message="test message",
            model_input="some-model",
        )

    def test_has_errors_false_when_no_issues(self) -> None:
        result = ModelValidationResult()
        assert result.has_errors is False

    def test_has_errors_true_when_error_present(self) -> None:
        result = ModelValidationResult()
        result.issues.append(self._make_issue(ModelIssueSeverity.ERROR))
        assert result.has_errors is True

    def test_has_warnings_false_when_no_warnings(self) -> None:
        result = ModelValidationResult()
        assert result.has_warnings is False

    def test_has_warnings_true_when_warning_present(self) -> None:
        result = ModelValidationResult()
        result.issues.append(self._make_issue(ModelIssueSeverity.WARNING))
        assert result.has_warnings is True

    def test_errors_property_filters_correctly(self) -> None:
        result = ModelValidationResult()
        result.issues.append(self._make_issue(ModelIssueSeverity.ERROR))
        result.issues.append(self._make_issue(ModelIssueSeverity.INFO))
        assert len(result.errors) == 1
        assert result.errors[0].severity == ModelIssueSeverity.ERROR

    def test_warnings_property_filters_correctly(self) -> None:
        result = ModelValidationResult()
        result.issues.append(self._make_issue(ModelIssueSeverity.WARNING))
        result.issues.append(self._make_issue(ModelIssueSeverity.ERROR))
        assert len(result.warnings) == 1

    def test_is_valid_true_with_no_errors(self) -> None:
        result = ModelValidationResult()
        result.issues.append(self._make_issue(ModelIssueSeverity.INFO))
        assert result.is_valid() is True

    def test_is_valid_false_with_errors(self) -> None:
        result = ModelValidationResult()
        result.issues.append(self._make_issue(ModelIssueSeverity.ERROR))
        assert result.is_valid() is False


# ---------------------------------------------------------------------------
# WorkflowLoader.load_workflow
# ---------------------------------------------------------------------------


class TestLoadWorkflow:
    def test_loads_from_direct_yaml_path(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        yaml_file = tmp_path / "my_wf.yaml"
        yaml_file.write_text(_MINIMAL_YAML)

        config = loader.load_workflow(yaml_file)
        assert config.id == "test-wf"

    def test_loads_from_bundled_by_id(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        bundled_dir = tmp_path / "bundled"
        _write_workflow(bundled_dir, "my-workflow.yaml", _MINIMAL_YAML)

        config = loader.load_workflow("my-workflow")
        assert config.id == "test-wf"

    def test_loads_from_global_by_id(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        global_dir = tmp_path / "global"
        _write_workflow(global_dir, "global-wf.yaml", _MINIMAL_YAML)

        config = loader.load_workflow("global-wf")
        assert config.id == "test-wf"

    def test_loads_from_project_by_id(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        project_workflows = tmp_path / "project" / ".pixl" / "workflows"
        project_workflows.mkdir(parents=True, exist_ok=True)
        _write_workflow(project_workflows, "proj-wf.yaml", _MINIMAL_YAML)

        config = loader.load_workflow("proj-wf")
        assert config.id == "test-wf"

    def test_project_overrides_bundled_with_same_id(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        bundled_dir = tmp_path / "bundled"
        _write_workflow(bundled_dir, "shared.yaml", _MINIMAL_YAML)

        project_workflows = tmp_path / "project" / ".pixl" / "workflows"
        project_workflows.mkdir(parents=True, exist_ok=True)
        override_yaml = _MINIMAL_YAML.replace("Test Workflow", "Project Override")
        _write_workflow(project_workflows, "shared.yaml", override_yaml)

        config = loader.load_workflow("shared")
        assert config.name == "Project Override"

    def test_raises_workflow_load_error_when_not_found(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        with pytest.raises(WorkflowLoadError, match="not found"):
            loader.load_workflow("nonexistent-workflow")

    def test_raises_for_missing_direct_path(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        with pytest.raises(WorkflowLoadError):
            loader.load_workflow("definitely-not-there")


# ---------------------------------------------------------------------------
# WorkflowLoader.list_workflows
# ---------------------------------------------------------------------------


class TestListWorkflows:
    def test_returns_empty_list_when_no_workflows(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        result = loader.list_workflows()
        assert result == []

    def test_lists_bundled_workflow(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        _write_workflow(tmp_path / "bundled", "wf1.yaml", _MINIMAL_YAML)

        result = loader.list_workflows()
        assert len(result) == 1
        assert result[0]["id"] == "test-wf"

    def test_lists_multiple_workflows(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        bundled = tmp_path / "bundled"
        _write_workflow(bundled, "wf1.yaml", _MINIMAL_YAML)
        _write_workflow(bundled, "wf2.yaml", _TWO_STAGE_YAML)

        result = loader.list_workflows()
        ids = [w["id"] for w in result]
        assert "test-wf" in ids
        assert "two-stage" in ids

    def test_project_source_overrides_bundled(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        _write_workflow(tmp_path / "bundled", "shared.yaml", _MINIMAL_YAML)

        project_workflows = tmp_path / "project" / ".pixl" / "workflows"
        project_workflows.mkdir(parents=True, exist_ok=True)
        override_yaml = _MINIMAL_YAML.replace("Test Workflow", "Project Version")
        _write_workflow(project_workflows, "shared.yaml", override_yaml)

        result = loader.list_workflows()
        matching = [w for w in result if w["id"] == "test-wf"]
        assert len(matching) == 1
        assert matching[0]["source"] == "project"
        assert matching[0]["name"] == "Project Version"

    def test_entry_has_expected_keys(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        _write_workflow(tmp_path / "bundled", "wf1.yaml", _MINIMAL_YAML)

        result = loader.list_workflows()
        entry = result[0]
        for key in ("id", "name", "description", "path", "version", "source"):
            assert key in entry, f"Missing key: {key}"

    def test_skips_invalid_yaml_file(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        bad_file = tmp_path / "bundled" / "bad.yaml"
        bad_file.write_text(":::not valid yaml:::")

        result = loader.list_workflows()
        assert result == []


# ---------------------------------------------------------------------------
# WorkflowLoader.convert_to_graph
# ---------------------------------------------------------------------------


class TestConvertToGraph:
    def test_single_stage_creates_one_node(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        yaml_file = tmp_path / "single.yaml"
        yaml_file.write_text(_MINIMAL_YAML)
        config = loader.load_workflow(yaml_file)

        graph = loader.convert_to_graph(config, skip_model_validation=True)
        assert "plan" in graph.nodes

    def test_two_stages_creates_sequential_edges(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        yaml_file = tmp_path / "two.yaml"
        yaml_file.write_text(_TWO_STAGE_YAML)
        config = loader.load_workflow(yaml_file)

        graph = loader.convert_to_graph(config, skip_model_validation=True)
        edges = graph.get_successors("plan")
        assert any(e.to == "implement" for e in edges)

    def test_gate_stage_creates_gate_node(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        yaml_file = tmp_path / "gate.yaml"
        yaml_file.write_text(_GATE_YAML)
        config = loader.load_workflow(yaml_file)

        graph = loader.convert_to_graph(config, skip_model_validation=True)
        review_node = graph.nodes["review"]
        assert review_node.type == NodeType.GATE

    def test_hook_stage_creates_hook_node(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        yaml_file = tmp_path / "hook.yaml"
        yaml_file.write_text(_HOOK_YAML)
        config = loader.load_workflow(yaml_file)

        graph = loader.convert_to_graph(config, skip_model_validation=True)
        notify_node = graph.nodes["notify"]
        assert notify_node.type == NodeType.HOOK

    def test_sub_workflow_stage_creates_sub_workflow_node(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        yaml_file = tmp_path / "sub.yaml"
        yaml_file.write_text(_SUBWORKFLOW_YAML)
        config = loader.load_workflow(yaml_file)

        graph = loader.convert_to_graph(config, skip_model_validation=True)
        child_node = graph.nodes["child"]
        assert child_node.type == NodeType.SUB_WORKFLOW

    def test_loop_creates_loop_constraint(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        yaml_file = tmp_path / "loop.yaml"
        yaml_file.write_text(_LOOP_YAML)
        config = loader.load_workflow(yaml_file)

        graph = loader.convert_to_graph(config, skip_model_validation=True)
        assert len(graph.loop_constraints) == 1
        lc = graph.loop_constraints[0]
        assert lc.id == "fix-loop"
        assert lc.from_node == "review"
        assert lc.to_node == "implement"
        assert lc.max_iterations == 3

    def test_loop_trigger_maps_to_failure_edge(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        yaml_file = tmp_path / "loop.yaml"
        yaml_file.write_text(_LOOP_YAML)
        config = loader.load_workflow(yaml_file)

        graph = loader.convert_to_graph(config, skip_model_validation=True)
        lc = graph.loop_constraints[0]
        assert lc.edge_trigger == EdgeTrigger.FAILURE

    def test_explicit_edges_used_when_provided(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        yaml_file = tmp_path / "edges.yaml"
        yaml_file.write_text(_EXPLICIT_EDGES_YAML)
        config = loader.load_workflow(yaml_file)

        graph = loader.convert_to_graph(config, skip_model_validation=True)
        successors_a = graph.get_successors("step-a")
        assert any(e.to == "step-b" for e in successors_a)
        # step-c should NOT be a direct successor of step-a
        assert not any(e.to == "step-c" for e in successors_a)

    def test_invalid_edge_source_raises_error(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        bad_edges_yaml = textwrap.dedent("""\
            id: bad-edges
            name: Bad Edges
            version: 1.0.0
            stages:
              - id: step-a
                name: Step A
                type: task
                agent: architect
            edges:
              nonexistent-node: [step-a]
        """)
        yaml_file = tmp_path / "bad.yaml"
        yaml_file.write_text(bad_edges_yaml)
        config = loader.load_workflow(yaml_file)

        with pytest.raises(WorkflowLoadError, match="not found"):
            loader.convert_to_graph(config, skip_model_validation=True)

    def test_invalid_edge_target_raises_error(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        bad_target_yaml = textwrap.dedent("""\
            id: bad-target
            name: Bad Target
            version: 1.0.0
            stages:
              - id: step-a
                name: Step A
                type: task
                agent: architect
            edges:
              step-a: [missing-target]
        """)
        yaml_file = tmp_path / "bad2.yaml"
        yaml_file.write_text(bad_target_yaml)
        config = loader.load_workflow(yaml_file)

        with pytest.raises(WorkflowLoadError, match="not found"):
            loader.convert_to_graph(config, skip_model_validation=True)

    def test_loop_from_stage_not_found_raises_error(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        bad_loop_yaml = textwrap.dedent("""\
            id: bad-loop
            name: Bad Loop
            version: 1.0.0
            stages:
              - id: step-a
                name: Step A
                type: task
                agent: architect
            loops:
              - id: bad-loop
                from: nonexistent
                to: step-a
                trigger: failure
                max_iterations: 3
        """)
        yaml_file = tmp_path / "bad_loop.yaml"
        yaml_file.write_text(bad_loop_yaml)
        config = loader.load_workflow(yaml_file)

        with pytest.raises(WorkflowLoadError, match="not found"):
            loader.convert_to_graph(config, skip_model_validation=True)

    def test_returns_execution_graph(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        yaml_file = tmp_path / "wf.yaml"
        yaml_file.write_text(_MINIMAL_YAML)
        config = loader.load_workflow(yaml_file)

        from pixl.models.workflow import ExecutionGraph

        graph = loader.convert_to_graph(config, skip_model_validation=True)
        assert isinstance(graph, ExecutionGraph)

    def test_node_priorities_set_sequentially(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        yaml_file = tmp_path / "two.yaml"
        yaml_file.write_text(_TWO_STAGE_YAML)
        config = loader.load_workflow(yaml_file)

        graph = loader.convert_to_graph(config, skip_model_validation=True)
        assert graph.nodes["plan"].priority == 0
        assert graph.nodes["implement"].priority == 1


# ---------------------------------------------------------------------------
# WorkflowLoader.validate_models
# ---------------------------------------------------------------------------


class TestValidateModels:
    def _make_loader_with_model(self, tmp_path: Path, model: str) -> WorkflowLoader:
        """Build a loader whose providers_config has a specific default_model."""
        loader = _make_loader(tmp_path)
        loader.providers_config.default_model = model
        loader.providers_config.models = [model]
        return loader

    def test_valid_model_produces_info_issue(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        model = loader.providers_config.default_model
        # Ensure the default model is in the allowlist
        if model not in loader.providers_config.models:
            loader.providers_config.models = [model]

        yaml_file = tmp_path / "wf.yaml"
        yaml_file.write_text(_MINIMAL_YAML)
        config = loader.load_workflow(yaml_file)

        result = loader.validate_models(config)
        assert not result.has_errors

    def test_model_not_in_allowlist_produces_error(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        loader.providers_config.default_model = "unknown/super-model"
        loader.providers_config.models = ["anthropic/claude-sonnet-4-6"]

        yaml_file = tmp_path / "wf.yaml"
        yaml_file.write_text(_MINIMAL_YAML)
        config = loader.load_workflow(yaml_file)

        result = loader.validate_models(config)
        assert result.has_errors

    def test_gate_and_hook_stages_skipped(self, tmp_path: Path) -> None:
        """Gate, hook, and sub_workflow stages don't need a model — no errors."""
        loader = _make_loader(tmp_path)
        loader.providers_config.default_model = None  # type: ignore[assignment]

        yaml_file = tmp_path / "gate.yaml"
        yaml_file.write_text(_GATE_YAML)
        config = loader.load_workflow(yaml_file)

        # Only gate and task stage — model=None should error for task only
        result = loader.validate_models(config)
        # Build stage has type=task so we expect an error, but review=gate is skipped
        error_stage_ids = [i.stage_id for i in result.errors]
        assert "review" not in error_stage_ids

    def test_none_model_produces_error(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        loader.providers_config.default_model = None  # type: ignore[assignment]

        yaml_file = tmp_path / "wf.yaml"
        yaml_file.write_text(_MINIMAL_YAML)
        config = loader.load_workflow(yaml_file)

        result = loader.validate_models(config)
        assert result.has_errors
        assert any("None" in i.message for i in result.errors)

    def test_unknown_provider_prefix_produces_error(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        loader.providers_config.default_model = "unknown-provider/model-x"
        loader.providers_config.models = ["anthropic/claude-sonnet-4-6"]

        yaml_file = tmp_path / "wf.yaml"
        yaml_file.write_text(_MINIMAL_YAML)
        config = loader.load_workflow(yaml_file)

        result = loader.validate_models(config)
        assert result.has_errors

    def test_returns_model_validation_result_instance(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        yaml_file = tmp_path / "wf.yaml"
        yaml_file.write_text(_MINIMAL_YAML)
        config = loader.load_workflow(yaml_file)

        result = loader.validate_models(config)
        assert isinstance(result, ModelValidationResult)


# ---------------------------------------------------------------------------
# WorkflowLoader.convert_to_graph — model validation triggering
# ---------------------------------------------------------------------------


class TestConvertToGraphModelValidation:
    def test_raises_when_model_validation_fails(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        loader.providers_config.default_model = "completely-invalid-model"
        loader.providers_config.models = ["anthropic/claude-sonnet-4-6"]

        yaml_file = tmp_path / "wf.yaml"
        yaml_file.write_text(_MINIMAL_YAML)
        config = loader.load_workflow(yaml_file)

        with pytest.raises(WorkflowLoadError, match="validation failed"):
            loader.convert_to_graph(config, skip_model_validation=False)

    def test_succeeds_when_skip_model_validation_true(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        loader.providers_config.default_model = "completely-invalid-model"
        loader.providers_config.models = ["anthropic/claude-sonnet-4-6"]

        yaml_file = tmp_path / "wf.yaml"
        yaml_file.write_text(_MINIMAL_YAML)
        config = loader.load_workflow(yaml_file)

        # Should not raise
        graph = loader.convert_to_graph(config, skip_model_validation=True)
        assert "plan" in graph.nodes

    def test_warning_emitted_for_warning_severity_model(self, tmp_path: Path, recwarn) -> None:
        """When validation returns warnings (not errors), convert_to_graph emits UserWarning."""
        loader = _make_loader(tmp_path)

        def patched_validate(config):
            result = ModelValidationResult()
            result.issues.append(
                ModelValidationIssue(
                    stage_id="plan",
                    severity=ModelIssueSeverity.WARNING,
                    message="Deprecated model alias",
                    model_input="old-model",
                )
            )
            return result

        loader.validate_models = patched_validate  # type: ignore[method-assign]

        yaml_file = tmp_path / "wf.yaml"
        yaml_file.write_text(_MINIMAL_YAML)
        config = loader.load_workflow(yaml_file)

        import warnings

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            loader.convert_to_graph(config, skip_model_validation=False)

        assert any("Deprecated model alias" in str(w.message) for w in caught)


# ---------------------------------------------------------------------------
# Stage node type mapping
# ---------------------------------------------------------------------------


class TestStageToNode:
    def test_task_node_has_task_config(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        yaml_file = tmp_path / "wf.yaml"
        yaml_file.write_text(_MINIMAL_YAML)
        config = loader.load_workflow(yaml_file)

        graph = loader.convert_to_graph(config, skip_model_validation=True)
        plan_node = graph.nodes["plan"]
        assert plan_node.task_config is not None
        assert plan_node.task_config.agent == "architect"

    def test_gate_node_has_gate_config(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        yaml_file = tmp_path / "gate.yaml"
        yaml_file.write_text(_GATE_YAML)
        config = loader.load_workflow(yaml_file)

        graph = loader.convert_to_graph(config, skip_model_validation=True)
        gate_node = graph.nodes["review"]
        assert gate_node.gate_config is not None
        assert gate_node.gate_config.timeout_minutes == 60

    def test_hook_node_has_hook_config(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        yaml_file = tmp_path / "hook.yaml"
        yaml_file.write_text(_HOOK_YAML)
        config = loader.load_workflow(yaml_file)

        graph = loader.convert_to_graph(config, skip_model_validation=True)
        hook_node = graph.nodes["notify"]
        assert hook_node.hook_config is not None
        assert hook_node.hook_config.hook_id == "slack-notify"

    def test_sub_workflow_node_has_metadata(self, tmp_path: Path) -> None:
        loader = _make_loader(tmp_path)
        yaml_file = tmp_path / "sub.yaml"
        yaml_file.write_text(_SUBWORKFLOW_YAML)
        config = loader.load_workflow(yaml_file)

        graph = loader.convert_to_graph(config, skip_model_validation=True)
        sub_node = graph.nodes["child"]
        assert sub_node.metadata.get("sub_workflow") == "debug"

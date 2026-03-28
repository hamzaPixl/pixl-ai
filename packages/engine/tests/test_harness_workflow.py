"""Tests for harness workflow template loading and DAG structure.

Covers:
- YAML loads without errors
- Graph has expected nodes and edges
- Loop constraint is correctly defined
- Hook node references the score-gate hook
- Parameters are declared with correct defaults
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

HARNESS_YAML = (
    Path(__file__).resolve().parent.parent / "pixl" / "assets" / "workflows" / "harness.yaml"
)


@pytest.fixture()
def harness_config() -> dict:
    """Load the harness workflow YAML as a dict."""
    assert HARNESS_YAML.exists(), f"harness.yaml not found at {HARNESS_YAML}"
    with HARNESS_YAML.open() as f:
        return yaml.safe_load(f)


class TestHarnessWorkflowTemplate:
    """Validate the harness.yaml structure against workflow_format v2."""

    def test_loads_valid_yaml(self, harness_config: dict) -> None:
        """YAML parses without error and has required top-level keys."""
        assert harness_config["id"] == "harness"
        assert harness_config["workflow_format"] == "v2"
        assert "stages" in harness_config
        assert "loops" in harness_config
        assert "edges" in harness_config

    def test_has_four_stages(self, harness_config: dict) -> None:
        """Workflow defines exactly 4 stages: plan, generate, evaluate, score-gate."""
        stages = harness_config["stages"]
        stage_ids = [s["id"] for s in stages]
        assert stage_ids == ["plan", "generate", "evaluate", "score-gate"]

    def test_stage_types(self, harness_config: dict) -> None:
        """Each stage has the correct type."""
        stages = {s["id"]: s for s in harness_config["stages"]}
        assert stages["plan"]["type"] == "task"
        assert stages["generate"]["type"] == "task"
        assert stages["evaluate"]["type"] == "task"
        assert stages["score-gate"]["type"] == "hook"

    def test_score_gate_references_hook(self, harness_config: dict) -> None:
        """The score-gate stage references the registered score-gate hook."""
        stages = {s["id"]: s for s in harness_config["stages"]}
        assert stages["score-gate"]["hook"] == "score-gate"
        assert "threshold" in stages["score-gate"]["hook_params"]
        assert "criteria" in stages["score-gate"]["hook_params"]

    def test_loop_constraint(self, harness_config: dict) -> None:
        """Loop goes from score-gate back to generate on failure."""
        loops = harness_config["loops"]
        assert len(loops) == 1

        loop = loops[0]
        assert loop["id"] == "improve-quality"
        assert loop["from"] == "score-gate"
        assert loop["to"] == "generate"
        assert loop["trigger"] == "failure"

    def test_edges_form_linear_dag(self, harness_config: dict) -> None:
        """Edges define: plan → generate → evaluate → score-gate."""
        edges = harness_config["edges"]
        assert edges["plan"] == ["generate"]
        assert edges["generate"] == ["evaluate"]
        assert edges["evaluate"] == ["score-gate"]

    def test_parameters_declared(self, harness_config: dict) -> None:
        """Workflow declares prompt, threshold, and max_iterations parameters."""
        params = {p["id"]: p for p in harness_config["parameters"]}
        assert "prompt" in params
        assert params["prompt"]["required"] is True

        assert "threshold" in params
        assert params["threshold"]["default"] == 7

        assert "max_iterations" in params
        assert params["max_iterations"]["default"] == 5

    def test_plan_stage_uses_architect_agent(self, harness_config: dict) -> None:
        """Plan stage is assigned to the architect agent."""
        stages = {s["id"]: s for s in harness_config["stages"]}
        assert stages["plan"]["agent"] == "architect"

    def test_generate_stage_has_high_max_turns(self, harness_config: dict) -> None:
        """Generate stage allows enough turns for substantial implementation."""
        stages = {s["id"]: s for s in harness_config["stages"]}
        assert stages["generate"]["max_turns"] >= 100

    def test_prompt_refs_exist(self, harness_config: dict) -> None:
        """All prompt_ref files referenced in stages actually exist."""
        prompts_dir = HARNESS_YAML.parent.parent / "prompts"
        for stage in harness_config["stages"]:
            ref = stage.get("prompt_ref")
            if ref:
                ref_path = prompts_dir / ref
                assert ref_path.exists(), f"Missing prompt_ref: {ref} (at {ref_path})"


class TestScoreGateHookRegistered:
    """Verify the score-gate hook is registered in the hook registry."""

    def test_hook_registered(self) -> None:
        """score-gate hook is in HOOK_REGISTRY after import."""
        from pixl.execution.hooks import HOOK_REGISTRY

        assert "score-gate" in HOOK_REGISTRY

    def test_hook_callable(self) -> None:
        """Registered hook is a callable function."""
        from pixl.execution.hooks import get_hook

        hook = get_hook("score-gate")
        assert hook is not None
        assert callable(hook)

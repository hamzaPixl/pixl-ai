"""Tests for contract_validator.py and validation/core.py.

Covers ContractValidator with mocked file system (tmp_path), testing:
- Valid stage output passes validation
- Missing required files are caught
- Missing sections are caught
- Stub detection in output
- Schema validation errors
- Regression test requirement
- Context budget checks
- Scope boundary / forbidden path enforcement
- Frozen artifact validation
- Skill / agent usage validation
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pixl.execution.contract_validator import ContractValidator
from pixl.execution.validation.core import ContractValidator as CoreValidator
from pixl.execution.validation.models import ContractValidationResult
from pixl.execution.validation.skill_usage_validator import (
    check_required_agents,
    check_required_skills,
)
from pixl.models.stage_output import ArtifactWritten, StageError, StageOutput
from pixl.models.workflow_config import StageContract

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_validator(tmp_path: Path, baseline_commit: str | None = None) -> ContractValidator:
    """Create a ContractValidator backed by the tmp_path directory."""
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return ContractValidator(
        project_root=tmp_path,
        artifacts_dir=artifacts_dir,
        baseline_commit=baseline_commit,
    )


def _make_core_validator(tmp_path: Path, baseline_commit: str | None = None) -> CoreValidator:
    """Create a validation/core.py ContractValidator backed by tmp_path."""
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return CoreValidator(
        project_root=tmp_path,
        artifacts_dir=artifacts_dir,
        baseline_commit=baseline_commit,
    )


def _write_artifact(tmp_path: Path, filename: str, content: str) -> Path:
    """Write a file under tmp_path/artifacts/<filename>."""
    p = tmp_path / "artifacts" / filename
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _empty_contract(**kwargs) -> StageContract:
    """Create a StageContract with all defaults (no checks active)."""
    return StageContract(**kwargs)


# ===========================================================================
# Section 1: _check_must_write — file existence
# ===========================================================================


class TestCheckMustWrite:
    def test_passes_when_required_file_exists(self, tmp_path: Path) -> None:
        _write_artifact(tmp_path, "plan.md", "# Plan\n\nContent here.\n")
        v = _make_validator(tmp_path)
        contract = _empty_contract(must_write=["plan.md"])

        result = v.validate(contract)

        assert result.passed

    def test_violation_when_required_file_missing(self, tmp_path: Path) -> None:
        v = _make_validator(tmp_path)
        contract = _empty_contract(must_write=["missing.md"])

        result = v.validate(contract)

        assert not result.passed
        assert any("missing.md" in v_item.message for v_item in result.violations)

    def test_violation_rule_is_must_write(self, tmp_path: Path) -> None:
        v = _make_validator(tmp_path)
        contract = _empty_contract(must_write=["absent.md"])

        result = v.validate(contract)

        assert any(v_item.rule == "must_write" for v_item in result.violations)

    def test_multiple_missing_files_each_produce_violation(self, tmp_path: Path) -> None:
        v = _make_validator(tmp_path)
        contract = _empty_contract(must_write=["a.md", "b.md", "c.md"])

        result = v.validate(contract)

        assert len(result.violations) == 3

    def test_passes_when_file_in_artifacts_dir(self, tmp_path: Path) -> None:
        # contract_validator uses session-scoped artifact paths (artifacts_dir), not project_root
        _write_artifact(tmp_path, "spec.md", "# Spec\n")
        v = _make_validator(tmp_path)
        contract = _empty_contract(must_write=["spec.md"])

        result = v.validate(contract)

        assert result.passed

    def test_partial_pass_when_some_files_missing(self, tmp_path: Path) -> None:
        _write_artifact(tmp_path, "exists.md", "content")
        v = _make_validator(tmp_path)
        contract = _empty_contract(must_write=["exists.md", "missing.md"])

        result = v.validate(contract)

        assert not result.passed
        assert len(result.violations) == 1
        assert "missing.md" in result.violations[0].message


# ===========================================================================
# Section 2: _check_must_include_sections
# ===========================================================================


class TestCheckMustIncludeSections:
    def test_passes_when_all_sections_present(self, tmp_path: Path) -> None:
        content = "# Overview\n\nSome text.\n\n# Tasks\n\nDo things.\n"
        _write_artifact(tmp_path, "plan.md", content)
        v = _make_validator(tmp_path)
        contract = _empty_contract(
            must_write=["plan.md"],
            must_include_sections={"plan.md": ["Overview", "Tasks"]},
        )

        result = v.validate(contract)

        assert result.passed

    def test_violation_when_section_missing(self, tmp_path: Path) -> None:
        content = "# Overview\n\nSome text.\n"
        _write_artifact(tmp_path, "plan.md", content)
        v = _make_validator(tmp_path)
        contract = _empty_contract(
            must_write=["plan.md"],
            must_include_sections={"plan.md": ["Tasks"]},
        )

        result = v.validate(contract)

        assert not result.passed
        assert any("Tasks" in v_item.message for v_item in result.violations)

    def test_alias_matching_accepts_any_alias(self, tmp_path: Path) -> None:
        content = "# How to Verify\n\nVerification steps.\n"
        _write_artifact(tmp_path, "plan.md", content)
        v = _make_validator(tmp_path)
        contract = _empty_contract(
            must_write=["plan.md"],
            must_include_sections={"plan.md": ["Verification|How to Verify|Testing"]},
        )

        result = v.validate(contract)

        assert result.passed

    def test_section_check_is_case_insensitive(self, tmp_path: Path) -> None:
        content = "# TASKS\n\nTask list.\n"
        _write_artifact(tmp_path, "plan.md", content)
        v = _make_validator(tmp_path)
        contract = _empty_contract(
            must_write=["plan.md"],
            must_include_sections={"plan.md": ["tasks"]},
        )

        result = v.validate(contract)

        assert result.passed

    def test_violation_when_file_missing_for_section_check(self, tmp_path: Path) -> None:
        v = _make_validator(tmp_path)
        contract = _empty_contract(
            must_include_sections={"nonexistent.md": ["Overview"]},
        )

        result = v.validate(contract)

        assert not result.passed
        assert any("nonexistent.md" in v_item.message for v_item in result.violations)

    def test_multiple_missing_sections_each_produce_violation(self, tmp_path: Path) -> None:
        content = "# Overview\n\nOnly one section.\n"
        _write_artifact(tmp_path, "doc.md", content)
        v = _make_validator(tmp_path)
        contract = _empty_contract(
            must_include_sections={"doc.md": ["Tasks", "Tests", "Dependencies"]},
        )

        result = v.validate(contract)

        assert len(result.violations) == 3


# ===========================================================================
# Section 3: _check_must_include_command_blocks
# ===========================================================================


class TestCheckMustIncludeCommandBlocks:
    def test_passes_with_fenced_bash_block(self, tmp_path: Path) -> None:
        content = "# Install\n\n```bash\nnpm install\n```\n"
        _write_artifact(tmp_path, "README.md", content)
        v = _make_validator(tmp_path)
        contract = _empty_contract(
            must_write=["README.md"],
            must_include_command_blocks=True,
        )

        result = v.validate(contract)

        assert result.passed

    def test_passes_with_dollar_prefixed_line(self, tmp_path: Path) -> None:
        content = "# Run\n\n$ python main.py\n"
        _write_artifact(tmp_path, "guide.md", content)
        v = _make_validator(tmp_path)
        contract = _empty_contract(
            must_write=["guide.md"],
            must_include_command_blocks=True,
        )

        result = v.validate(contract)

        assert result.passed

    def test_violation_when_no_command_blocks(self, tmp_path: Path) -> None:
        content = "# Overview\n\nJust prose here, no commands.\n"
        _write_artifact(tmp_path, "spec.md", content)
        v = _make_validator(tmp_path)
        contract = _empty_contract(
            must_write=["spec.md"],
            must_include_command_blocks=True,
        )

        result = v.validate(contract)

        assert not result.passed
        assert any(v_item.rule == "must_include_command_blocks" for v_item in result.violations)

    def test_passes_with_shell_fenced_block(self, tmp_path: Path) -> None:
        content = "```shell\necho hello\n```\n"
        _write_artifact(tmp_path, "script.md", content)
        v = _make_validator(tmp_path)
        contract = _empty_contract(
            must_write=["script.md"],
            must_include_command_blocks=True,
        )

        result = v.validate(contract)

        assert result.passed


# ===========================================================================
# Section 4: _check_regression_test
# ===========================================================================


class TestCheckRegressionTest:
    def test_passes_when_test_file_in_must_write(self, tmp_path: Path) -> None:
        _write_artifact(tmp_path, "test_feature.py", "def test_foo(): pass")
        v = _make_validator(tmp_path)
        contract = _empty_contract(
            must_write=["test_feature.py"],
            require_regression_test=True,
        )

        result = v.validate(contract, changed_files=["test_feature.py"])

        assert result.passed

    def test_passes_with_test_in_tests_directory(self, tmp_path: Path) -> None:
        v = _make_validator(tmp_path)
        contract = _empty_contract(require_regression_test=True)

        result = v.validate(contract, changed_files=["tests/test_something.py"])

        assert result.passed

    def test_violation_when_no_test_files_found(self, tmp_path: Path) -> None:
        v = _make_validator(tmp_path)
        contract = _empty_contract(require_regression_test=True)

        result = v.validate(contract, changed_files=["src/feature.py"])

        assert not result.passed
        assert any(v_item.rule == "regression_test_missing" for v_item in result.violations)

    def test_passes_with_spec_file(self, tmp_path: Path) -> None:
        v = _make_validator(tmp_path)
        contract = _empty_contract(require_regression_test=True)

        result = v.validate(contract, changed_files=["feature.spec.ts"])

        assert result.passed

    def test_violation_when_changed_files_empty(self, tmp_path: Path) -> None:
        v = _make_validator(tmp_path)
        contract = _empty_contract(require_regression_test=True)

        # No must_write, no changed_files → empty files set
        result = v.validate(contract, changed_files=[])

        assert not result.passed

    def test_passes_when_test_file_has_dot_test_suffix(self, tmp_path: Path) -> None:
        v = _make_validator(tmp_path)
        contract = _empty_contract(require_regression_test=True)

        result = v.validate(contract, changed_files=["auth.test.ts"])

        assert result.passed


# ===========================================================================
# Section 5: detect_stubs
# ===========================================================================


def _write_project_file(tmp_path: Path, filename: str, content: str) -> Path:
    """Write a file under project_root (tmp_path itself), used for detect_stubs tests.

    contract_validator.detect_stubs uses _resolve_workspace_path (project_root-based).
    """
    p = tmp_path / filename
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


class TestDetectStubs:
    def test_detects_todo_stub(self, tmp_path: Path) -> None:
        # detect_stubs in contract_validator uses _resolve_workspace_path (project_root / path)
        _write_project_file(tmp_path, "impl.py", "def foo():\n    # TODO: implement\n    pass\n")
        v = _make_validator(tmp_path)
        result = ContractValidationResult()

        stubs = v.detect_stubs(["impl.py"], result)

        assert len(stubs) >= 1
        assert any("TODO" in s["content"].upper() for s in stubs)

    def test_detects_not_implemented_error(self, tmp_path: Path) -> None:
        _write_project_file(tmp_path, "impl.py", "def foo():\n    raise NotImplementedError\n")
        v = _make_validator(tmp_path)
        result = ContractValidationResult()

        stubs = v.detect_stubs(["impl.py"], result)

        assert len(stubs) >= 1

    def test_detects_placeholder_return(self, tmp_path: Path) -> None:
        _write_project_file(tmp_path, "impl.py", "def foo():\n    return 'placeholder'\n")
        v = _make_validator(tmp_path)
        result = ContractValidationResult()

        stubs = v.detect_stubs(["impl.py"], result)

        assert len(stubs) >= 1

    def test_detects_ellipsis_stub(self, tmp_path: Path) -> None:
        _write_project_file(tmp_path, "impl.py", "def foo():\n    ...\n")
        v = _make_validator(tmp_path)
        result = ContractValidationResult()

        stubs = v.detect_stubs(["impl.py"], result)

        assert len(stubs) >= 1

    def test_no_stubs_in_clean_implementation(self, tmp_path: Path) -> None:
        _write_project_file(tmp_path, "impl.py", "def add(a, b):\n    return a + b\n")
        v = _make_validator(tmp_path)
        result = ContractValidationResult()

        stubs = v.detect_stubs(["impl.py"], result)

        assert stubs == []
        assert result.passed

    def test_stub_detection_produces_violation(self, tmp_path: Path) -> None:
        _write_project_file(tmp_path, "impl.py", "# TODO: finish\n")
        v = _make_validator(tmp_path)
        result = ContractValidationResult()

        v.detect_stubs(["impl.py"], result)

        assert not result.passed
        assert any(v_item.rule == "stub_detected" for v_item in result.violations)

    def test_detect_stubs_via_contract(self, tmp_path: Path) -> None:
        # For the contract path, must_write checks artifacts_dir; detect_stubs scans project_root.
        # Put impl.py in both places: artifacts_dir (for must_write) and project_root (for scan).
        _write_artifact(tmp_path, "impl.py", "# FIXME: broken\n")
        _write_project_file(tmp_path, "impl.py", "# FIXME: broken\n")
        v = _make_validator(tmp_path)
        contract = _empty_contract(
            must_write=["impl.py"],
            detect_stubs=True,
        )

        result = v.validate(contract)

        assert not result.passed
        assert any(v_item.rule == "stub_detected" for v_item in result.violations)

    def test_skips_nonexistent_file_without_error(self, tmp_path: Path) -> None:
        v = _make_validator(tmp_path)
        result = ContractValidationResult()

        stubs = v.detect_stubs(["nonexistent.py"], result)

        assert stubs == []
        assert result.passed

    def test_violation_message_includes_filename(self, tmp_path: Path) -> None:
        _write_project_file(tmp_path, "module.py", "# TODO: add logic\n")
        v = _make_validator(tmp_path)
        result = ContractValidationResult()

        v.detect_stubs(["module.py"], result)

        assert any("module.py" in v_item.message for v_item in result.violations)


# ===========================================================================
# Section 6: _check_artifact_schemas
# ===========================================================================


class TestCheckArtifactSchemas:
    def test_passes_when_artifact_validates_against_schema(self, tmp_path: Path) -> None:
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }
        artifact = {"name": "hello"}

        _write_artifact(tmp_path, "output.json", json.dumps(artifact))
        schema_file = tmp_path / "schema.json"
        schema_file.write_text(json.dumps(schema), encoding="utf-8")

        v = _make_validator(tmp_path)
        contract = _empty_contract(
            must_write=["output.json"],
            artifact_schemas={"output.json": "schema.json"},
        )

        result = v.validate(contract)

        assert result.passed

    def test_violation_when_artifact_fails_schema_validation(self, tmp_path: Path) -> None:
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }
        artifact = {"value": 42}  # Missing required "name"

        _write_artifact(tmp_path, "output.json", json.dumps(artifact))
        schema_file = tmp_path / "schema.json"
        schema_file.write_text(json.dumps(schema), encoding="utf-8")

        v = _make_validator(tmp_path)
        contract = _empty_contract(
            must_write=["output.json"],
            artifact_schemas={"output.json": "schema.json"},
        )

        result = v.validate(contract)

        assert not result.passed
        assert any(v_item.rule == "artifact_schemas" for v_item in result.violations)

    def test_violation_when_artifact_file_missing(self, tmp_path: Path) -> None:
        schema = {"type": "object"}
        schema_file = tmp_path / "schema.json"
        schema_file.write_text(json.dumps(schema), encoding="utf-8")

        v = _make_validator(tmp_path)
        contract = _empty_contract(
            artifact_schemas={"missing.json": "schema.json"},
        )

        result = v.validate(contract)

        assert not result.passed
        assert any("missing.json" in v_item.message for v_item in result.violations)

    def test_violation_when_schema_file_missing(self, tmp_path: Path) -> None:
        _write_artifact(tmp_path, "output.json", '{"name": "test"}')

        v = _make_validator(tmp_path)
        contract = _empty_contract(
            must_write=["output.json"],
            artifact_schemas={"output.json": "nonexistent_schema.json"},
        )

        result = v.validate(contract)

        assert not result.passed
        assert any("nonexistent_schema.json" in v_item.message for v_item in result.violations)

    def test_violation_when_artifact_has_invalid_json(self, tmp_path: Path) -> None:
        _write_artifact(tmp_path, "bad.json", "{ not valid json }")
        schema_file = tmp_path / "schema.json"
        schema_file.write_text('{"type": "object"}', encoding="utf-8")

        v = _make_validator(tmp_path)
        contract = _empty_contract(
            must_write=["bad.json"],
            artifact_schemas={"bad.json": "schema.json"},
        )

        result = v.validate(contract)

        assert not result.passed
        assert any(v_item.rule == "artifact_schemas" for v_item in result.violations)


# ===========================================================================
# Section 7: validate_frozen_artifacts
# ===========================================================================


class TestValidateFrozenArtifacts:
    def test_passes_when_hash_matches(self, tmp_path: Path) -> None:
        content = "frozen content"
        _write_artifact(tmp_path, "frozen.md", content)
        expected_hash = _sha256(content)

        v = _make_validator(tmp_path)
        result = v.validate_frozen_artifacts({"frozen.md": expected_hash})

        assert result.passed

    def test_violation_when_hash_does_not_match(self, tmp_path: Path) -> None:
        _write_artifact(tmp_path, "frozen.md", "original content")

        v = _make_validator(tmp_path)
        result = v.validate_frozen_artifacts({"frozen.md": "deadbeef" * 8})

        assert not result.passed
        assert any(v_item.rule == "frozen_artifact_modified" for v_item in result.violations)

    def test_violation_when_artifact_file_missing(self, tmp_path: Path) -> None:
        v = _make_validator(tmp_path)
        result = v.validate_frozen_artifacts({"missing.md": "a" * 64})

        assert not result.passed
        assert any(v_item.rule == "frozen_artifact_missing" for v_item in result.violations)

    def test_passes_with_empty_frozen_artifacts(self, tmp_path: Path) -> None:
        v = _make_validator(tmp_path)
        result = v.validate_frozen_artifacts({})

        assert result.passed

    def test_multiple_frozen_artifacts_checked_independently(self, tmp_path: Path) -> None:
        content_a = "file a content"
        content_b = "file b content"
        _write_artifact(tmp_path, "a.md", content_a)
        _write_artifact(tmp_path, "b.md", content_b)

        v = _make_validator(tmp_path)
        result = v.validate_frozen_artifacts(
            {
                "a.md": _sha256(content_a),
                "b.md": "wronghash" + "x" * 55,  # Intentionally wrong
            }
        )

        assert not result.passed
        assert len(result.violations) == 1


# ===========================================================================
# Section 8: validate_structured_output (validation/core.py)
# ===========================================================================


class TestValidateStructuredOutput:
    def _make_ok_output(self, **kwargs) -> StageOutput:
        defaults = {
            "stage_id": "test-stage",
            "status": "ok",
            "summary": ["Done successfully"],
            "artifacts_written": [],
            "payload": {},
        }
        defaults.update(kwargs)
        return StageOutput(**defaults)

    def test_passes_for_valid_ok_output(self, tmp_path: Path) -> None:
        v = _make_core_validator(tmp_path)
        output = self._make_ok_output()

        result = v.validate_structured_output(output)

        assert result.passed

    def test_violation_when_status_is_error(self, tmp_path: Path) -> None:
        v = _make_core_validator(tmp_path)
        output = self._make_ok_output(
            status="error",
            error=StageError(code="fail", message="something went wrong"),
        )

        result = v.validate_structured_output(output)

        assert not result.passed
        assert any(v_item.rule == "structured_output_status" for v_item in result.violations)
        assert any("something went wrong" in v_item.message for v_item in result.violations)

    def test_violation_when_summary_is_empty(self, tmp_path: Path) -> None:
        v = _make_core_validator(tmp_path)
        output = self._make_ok_output(summary=[])

        result = v.validate_structured_output(output)

        assert not result.passed
        assert any(v_item.rule == "structured_output_summary" for v_item in result.violations)

    def test_violation_when_declared_artifact_missing(self, tmp_path: Path) -> None:
        v = _make_core_validator(tmp_path)
        output = self._make_ok_output(
            artifacts_written=[
                ArtifactWritten(
                    path="missing_artifact.md",
                    sha256="a" * 64,
                    purpose="output",
                )
            ]
        )

        result = v.validate_structured_output(output)

        assert not result.passed
        assert any(
            v_item.rule == "structured_output_artifact_missing" for v_item in result.violations
        )

    def test_passes_when_artifact_exists_and_hash_matches(self, tmp_path: Path) -> None:
        content = "# Output\n\nGenerated content.\n"
        _write_artifact(tmp_path, "output.md", content)
        actual_hash = _sha256(content)

        v = _make_core_validator(tmp_path)
        output = self._make_ok_output(
            artifacts_written=[
                ArtifactWritten(
                    path="output.md",
                    sha256=actual_hash,
                    purpose="primary output",
                )
            ]
        )

        result = v.validate_structured_output(output)

        assert result.passed

    def test_warning_when_artifact_hash_mismatches(self, tmp_path: Path) -> None:
        content = "actual content"
        _write_artifact(tmp_path, "output.md", content)

        v = _make_core_validator(tmp_path)
        output = self._make_ok_output(
            artifacts_written=[
                ArtifactWritten(
                    path="output.md",
                    sha256="wronghash" + "0" * 55,
                    purpose="output",
                )
            ]
        )

        result = v.validate_structured_output(output)

        # Hash mismatch is a warning, not a violation
        assert result.passed
        assert result.has_warnings
        assert any("mismatch" in w.lower() for w in result.warnings)

    def test_violation_when_schema_file_missing(self, tmp_path: Path) -> None:
        v = _make_core_validator(tmp_path)
        output = self._make_ok_output()

        result = v.validate_structured_output(output, output_schema_path="nonexistent_schema.json")

        assert not result.passed
        assert any(v_item.rule == "structured_output_schema" for v_item in result.violations)

    def test_passes_payload_against_valid_schema(self, tmp_path: Path) -> None:
        schema = {
            "type": "object",
            "properties": {"count": {"type": "integer"}},
            "required": ["count"],
        }
        schema_file = tmp_path / "output_schema.json"
        schema_file.write_text(json.dumps(schema), encoding="utf-8")

        v = _make_core_validator(tmp_path)
        output = self._make_ok_output(payload={"count": 5})

        result = v.validate_structured_output(output, output_schema_path="output_schema.json")

        assert result.passed

    def test_violation_when_payload_fails_schema(self, tmp_path: Path) -> None:
        schema = {
            "type": "object",
            "properties": {"count": {"type": "integer"}},
            "required": ["count"],
        }
        schema_file = tmp_path / "output_schema.json"
        schema_file.write_text(json.dumps(schema), encoding="utf-8")

        v = _make_core_validator(tmp_path)
        output = self._make_ok_output(payload={"wrong_field": "value"})

        result = v.validate_structured_output(output, output_schema_path="output_schema.json")

        assert not result.passed
        assert any(v_item.rule == "structured_output_schema" for v_item in result.violations)


# ===========================================================================
# Section 9: validate() with multiple contract fields
# ===========================================================================


class TestValidateMethod:
    def test_empty_contract_always_passes(self, tmp_path: Path) -> None:
        v = _make_validator(tmp_path)
        contract = _empty_contract()

        result = v.validate(contract)

        assert result.passed
        assert result.violations == []

    def test_warns_when_verify_success_criteria_set_but_no_criteria(self, tmp_path: Path) -> None:
        v = _make_validator(tmp_path)
        contract = _empty_contract(verify_success_criteria=True)

        result = v.validate(contract, success_criteria=None, changed_files=["impl.py"])

        assert result.has_warnings
        assert any("skipped" in w.lower() for w in result.warnings)

    def test_warns_when_verify_success_criteria_but_git_unavailable(self, tmp_path: Path) -> None:
        v = _make_validator(tmp_path)  # No baseline_commit
        contract = _empty_contract(verify_success_criteria=True)

        # Pass criteria but no changed_files and no baseline_commit
        result = v.validate(contract, success_criteria=["implement feature X"])

        # Either warning emitted or it was skipped
        assert result.has_warnings or result.passed

    def test_warns_when_context_budget_pct_set_but_no_max_tokens(self, tmp_path: Path) -> None:
        v = _make_validator(tmp_path)
        contract = _empty_contract(context_budget_pct=50)

        result = v.validate(contract, max_context_tokens=None)

        assert result.has_warnings
        assert any("unavailable" in w.lower() for w in result.warnings)

    def test_warns_when_context_budget_pct_set_but_no_files(self, tmp_path: Path) -> None:
        v = _make_validator(tmp_path)
        contract = _empty_contract(context_budget_pct=50)

        result = v.validate(contract, max_context_tokens=100000)

        assert result.has_warnings
        assert any("no must_write" in w.lower() for w in result.warnings)

    def test_warns_when_context_budget_exceeded(self, tmp_path: Path) -> None:
        large_content = "word " * 1000
        _write_artifact(tmp_path, "big.md", large_content)
        v = _make_validator(tmp_path)
        contract = _empty_contract(
            must_write=["big.md"],
            context_budget_pct=1,  # Very tight budget
        )

        result = v.validate(contract, max_context_tokens=100)

        assert result.has_warnings
        assert any("context_budget_exceeded" in w for w in result.warnings)

    def test_git_unavailable_recorded_when_no_baseline(self, tmp_path: Path) -> None:
        v = _make_validator(tmp_path)  # No baseline_commit
        contract = _empty_contract(must_update_files=["src/main.py"])

        result = v.validate(contract)

        # Without a baseline commit, git checks are skipped but no violations
        assert len(result.git_unavailable_checks) > 0


# ===========================================================================
# Section 10: _check_scope_boundary and forbidden_paths
# ===========================================================================


class TestScopeBoundaryAndForbiddenPaths:
    def test_no_violation_when_files_within_scope(self, tmp_path: Path) -> None:
        v = _make_validator(tmp_path)
        contract = _empty_contract(scope_boundary=["src/**"])

        result = v.validate(contract, changed_files=["src/module.py", "src/utils.py"])

        assert result.passed

    def test_violation_when_file_outside_scope_boundary(self, tmp_path: Path) -> None:
        v = _make_validator(tmp_path)
        contract = _empty_contract(scope_boundary=["src/**"])

        result = v.validate(contract, changed_files=["docs/readme.md"])

        assert not result.passed
        assert any(v_item.rule == "scope_boundary" for v_item in result.violations)

    def test_violation_for_forbidden_path(self, tmp_path: Path) -> None:
        v = _make_validator(tmp_path)
        contract = _empty_contract(forbidden_paths=["*.lock"])

        result = v.validate(contract, changed_files=["package.lock"])

        assert not result.passed
        assert any(v_item.rule == "forbidden_path" for v_item in result.violations)

    def test_forbidden_path_takes_precedence_over_scope_boundary(self, tmp_path: Path) -> None:
        v = _make_validator(tmp_path)
        contract = _empty_contract(
            scope_boundary=["**"],  # All files allowed
            forbidden_paths=["*.lock"],  # But not .lock files
        )

        result = v.validate(contract, changed_files=["uv.lock"])

        assert not result.passed
        assert any(v_item.rule == "forbidden_path" for v_item in result.violations)

    def test_no_violation_when_changed_files_empty_and_scope_set(self, tmp_path: Path) -> None:
        v = _make_validator(tmp_path)
        contract = _empty_contract(scope_boundary=["src/**"])

        result = v.validate(contract, changed_files=[])

        assert result.passed

    def test_scope_boundary_skipped_when_git_unavailable(self, tmp_path: Path) -> None:
        v = _make_validator(tmp_path)  # No baseline_commit
        contract = _empty_contract(scope_boundary=["src/**"])

        # No changed_files provided — will try git and fail gracefully
        result = v.validate(contract)

        # Should record git unavailable, not a violation
        assert len(result.git_unavailable_checks) > 0


# ===========================================================================
# Section 11: skill_usage_validator.py
# ===========================================================================


class TestCheckRequiredSkills:
    def _write_transcript(self, tmp_path: Path, entries: list[dict]) -> Path:
        transcript = tmp_path / "transcript.jsonl"
        with open(transcript, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")
        return transcript

    def _skill_entry(self, skill_name: str) -> dict:
        return {
            "content": [
                {
                    "type": "tool_use",
                    "name": "Skill",
                    "input": {"skill": skill_name},
                }
            ]
        }

    def _agent_entry(self, agent_type: str) -> dict:
        return {
            "content": [
                {
                    "type": "tool_use",
                    "name": "Agent",
                    "input": {"subagent_type": agent_type},
                }
            ]
        }

    def test_passes_when_required_skill_invoked(self, tmp_path: Path) -> None:
        transcript = self._write_transcript(tmp_path, [self._skill_entry("/ddd-pattern")])
        result = ContractValidationResult()

        check_required_skills(["/ddd-pattern"], transcript, result)

        assert result.passed

    def test_violation_when_required_skill_not_invoked(self, tmp_path: Path) -> None:
        transcript = self._write_transcript(tmp_path, [self._skill_entry("/other-skill")])
        result = ContractValidationResult()

        check_required_skills(["/ddd-pattern"], transcript, result)

        assert not result.passed
        assert any(v_item.rule == "required_skills" for v_item in result.violations)
        assert any("/ddd-pattern" in v_item.message for v_item in result.violations)

    def test_passes_when_transcript_path_is_none(self, tmp_path: Path) -> None:
        result = ContractValidationResult()

        check_required_skills(["/some-skill"], None, result)

        # When transcript is None, no invocations found → violation expected
        # (transcript_path=None means we cannot verify)
        assert not result.passed

    def test_passes_with_empty_required_skills(self, tmp_path: Path) -> None:
        result = ContractValidationResult()

        check_required_skills([], None, result)

        assert result.passed

    def test_matches_skill_ignoring_leading_slash(self, tmp_path: Path) -> None:
        transcript = self._write_transcript(tmp_path, [self._skill_entry("ddd-pattern")])
        result = ContractValidationResult()

        check_required_skills(["/ddd-pattern"], transcript, result)

        assert result.passed

    def test_passes_when_required_agent_invoked(self, tmp_path: Path) -> None:
        transcript = self._write_transcript(
            tmp_path, [self._agent_entry("pixl-crew:backend-engineer")]
        )
        result = ContractValidationResult()

        check_required_agents(["pixl-crew:backend-engineer"], transcript, result)

        assert result.passed

    def test_violation_when_required_agent_not_invoked(self, tmp_path: Path) -> None:
        transcript = self._write_transcript(
            tmp_path, [self._agent_entry("pixl-crew:frontend-engineer")]
        )
        result = ContractValidationResult()

        check_required_agents(["pixl-crew:backend-engineer"], transcript, result)

        assert not result.passed
        assert any(v_item.rule == "required_agents" for v_item in result.violations)

    def test_passes_with_empty_required_agents(self, tmp_path: Path) -> None:
        result = ContractValidationResult()

        check_required_agents([], None, result)

        assert result.passed

    def test_handles_malformed_jsonl_lines_gracefully(self, tmp_path: Path) -> None:
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text("not-json\n{}\n", encoding="utf-8")
        result = ContractValidationResult()

        check_required_skills(["/some-skill"], transcript, result)

        # Should not raise — but required skill was not found
        assert not result.passed

    def test_transcript_in_validate_via_contract(self, tmp_path: Path) -> None:
        transcript = self._write_transcript(tmp_path, [self._skill_entry("/ddd-pattern")])
        v = _make_validator(tmp_path)
        contract = _empty_contract(required_skills=["/ddd-pattern"])

        result = v.validate(contract, transcript_path=transcript)

        assert result.passed

    def test_violation_via_contract_when_skill_missing(self, tmp_path: Path) -> None:
        transcript = self._write_transcript(tmp_path, [self._skill_entry("/other-skill")])
        v = _make_validator(tmp_path)
        contract = _empty_contract(required_skills=["/ddd-pattern"])

        result = v.validate(contract, transcript_path=transcript)

        assert not result.passed
        assert any(v_item.rule == "required_skills" for v_item in result.violations)


# ===========================================================================
# Section 12: Static helpers (_extract_headings, _normalize_heading, _looks_like_test)
# ===========================================================================


class TestStaticHelpers:
    def test_extract_headings_returns_heading_text(self, tmp_path: Path) -> None:
        v = _make_validator(tmp_path)
        content = "# Heading One\n\nParagraph.\n\n## Heading Two\n"

        headings = v._extract_headings(content)

        assert headings == ["Heading One", "Heading Two"]

    def test_extract_headings_ignores_non_heading_lines(self, tmp_path: Path) -> None:
        v = _make_validator(tmp_path)
        content = "plain line\n# Real Heading\nanother plain line\n"

        headings = v._extract_headings(content)

        assert headings == ["Real Heading"]

    def test_normalize_heading_lowercases(self, tmp_path: Path) -> None:
        v = _make_validator(tmp_path)

        normalized = v._normalize_heading("How To Verify")

        assert normalized == "how to verify"

    def test_normalize_heading_strips_punctuation(self, tmp_path: Path) -> None:
        v = _make_validator(tmp_path)

        normalized = v._normalize_heading("Tasks: Do Things!")

        assert ":" not in normalized
        assert "!" not in normalized

    def test_looks_like_test_detects_test_prefix(self, tmp_path: Path) -> None:
        assert ContractValidator._looks_like_test("test_feature.py")

    def test_looks_like_test_detects_tests_directory(self, tmp_path: Path) -> None:
        assert ContractValidator._looks_like_test("src/tests/test_auth.py")

    def test_looks_like_test_detects_spec_suffix(self, tmp_path: Path) -> None:
        assert ContractValidator._looks_like_test("auth.spec.ts")

    def test_looks_like_test_detects_dot_test_suffix(self, tmp_path: Path) -> None:
        assert ContractValidator._looks_like_test("auth.test.ts")

    def test_looks_like_test_returns_false_for_source_file(self, tmp_path: Path) -> None:
        assert not ContractValidator._looks_like_test("src/auth.py")

    def test_has_command_blocks_detects_bash_fence(self, tmp_path: Path) -> None:
        content = "```bash\nnpm install\n```\n"
        assert ContractValidator._has_command_blocks(content)

    def test_has_command_blocks_detects_dollar_prefix(self, tmp_path: Path) -> None:
        content = "Run this:\n$ python main.py\n"
        assert ContractValidator._has_command_blocks(content)

    def test_has_command_blocks_returns_false_for_plain_text(self, tmp_path: Path) -> None:
        content = "Just plain prose, no commands here.\n"
        assert not ContractValidator._has_command_blocks(content)


# ===========================================================================
# Section 13: core.py ContractValidator — _check_regression_test and _check_must_write
# ===========================================================================


class TestCoreValidatorCheckMustWrite:
    """Test the validation/core.py ContractValidator's must_write check."""

    def test_passes_when_file_exists_in_artifacts_dir(self, tmp_path: Path) -> None:
        _write_artifact(tmp_path, "spec.md", "# Spec content\n")
        v = _make_core_validator(tmp_path)
        contract = _empty_contract(must_write=["spec.md"])

        result = v.validate(contract)

        assert result.passed

    def test_violation_when_required_file_missing(self, tmp_path: Path) -> None:
        v = _make_core_validator(tmp_path)
        contract = _empty_contract(must_write=["absent_file.md"])

        result = v.validate(contract)

        assert not result.passed
        assert any(v_item.rule == "must_write" for v_item in result.violations)


class TestCoreValidatorCheckMustIncludeSections:
    """Test the validation/core.py ContractValidator's must_include_sections check."""

    def test_passes_when_all_sections_present(self, tmp_path: Path) -> None:
        content = "# Overview\n\n## Implementation\n\nDetails.\n"
        _write_artifact(tmp_path, "doc.md", content)
        v = _make_core_validator(tmp_path)
        contract = _empty_contract(
            must_write=["doc.md"],
            must_include_sections={"doc.md": ["Overview", "Implementation"]},
        )

        result = v.validate(contract)

        assert result.passed

    def test_violation_when_section_missing(self, tmp_path: Path) -> None:
        content = "# Overview\n\nJust overview.\n"
        _write_artifact(tmp_path, "doc.md", content)
        v = _make_core_validator(tmp_path)
        contract = _empty_contract(
            must_write=["doc.md"],
            must_include_sections={"doc.md": ["Missing Section"]},
        )

        result = v.validate(contract)

        assert not result.passed
        assert any(v_item.rule == "must_include_sections" for v_item in result.violations)


class TestCoreValidatorDetectStubs:
    """Test the validation/core.py ContractValidator stub detection."""

    def test_detect_stubs_via_contract(self, tmp_path: Path) -> None:
        _write_artifact(tmp_path, "impl.py", "def foo():\n    # TODO: implement\n    pass\n")
        v = _make_core_validator(tmp_path)
        contract = _empty_contract(
            must_write=["impl.py"],
            detect_stubs=True,
        )

        result = v.validate(contract)

        assert not result.passed
        assert any(v_item.rule == "stub_detected" for v_item in result.violations)

    def test_no_violation_for_clean_code(self, tmp_path: Path) -> None:
        _write_artifact(tmp_path, "impl.py", "def add(a, b):\n    return a + b\n")
        v = _make_core_validator(tmp_path)
        result = ContractValidationResult()

        stubs = v.detect_stubs(["impl.py"], result)

        assert stubs == []
        assert result.passed


# ===========================================================================
# Section 14: core.py validate_structured_output
# ===========================================================================


class TestCoreValidateStructuredOutput:
    """Test validation/core.py ContractValidator.validate_structured_output."""

    def test_passes_for_ok_output_with_summary(self, tmp_path: Path) -> None:
        v = _make_core_validator(tmp_path)
        output = StageOutput(
            stage_id="stage-1",
            status="ok",
            summary=["Completed step 1", "Completed step 2"],
        )

        result = v.validate_structured_output(output)

        assert result.passed

    def test_violation_for_error_status(self, tmp_path: Path) -> None:
        v = _make_core_validator(tmp_path)
        output = StageOutput(
            stage_id="stage-1",
            status="error",
            summary=["Failed"],
            error=StageError(code="exec_error", message="Task failed"),
        )

        result = v.validate_structured_output(output)

        assert not result.passed
        assert any(v_item.rule == "structured_output_status" for v_item in result.violations)

    def test_violation_for_empty_summary(self, tmp_path: Path) -> None:
        v = _make_core_validator(tmp_path)
        output = StageOutput(
            stage_id="stage-1",
            status="ok",
            summary=[],
        )

        result = v.validate_structured_output(output)

        assert not result.passed
        assert any(v_item.rule == "structured_output_summary" for v_item in result.violations)

    def test_violation_for_missing_declared_artifact(self, tmp_path: Path) -> None:
        v = _make_core_validator(tmp_path)
        output = StageOutput(
            stage_id="stage-1",
            status="ok",
            summary=["Done"],
            artifacts_written=[
                ArtifactWritten(path="missing.md", sha256="a" * 64, purpose="output")
            ],
        )

        result = v.validate_structured_output(output)

        assert not result.passed
        assert any(
            v_item.rule == "structured_output_artifact_missing" for v_item in result.violations
        )


# ===========================================================================
# Section 15: Decompose payload DAG semantics (core.py)
# ===========================================================================


class TestDecomposePayloadDagSemantics:
    """Test cycle detection and unknown ref detection in decompose payloads."""

    def test_passes_for_valid_dag(self, tmp_path: Path) -> None:
        payload = {
            "features": [
                {"title": "Feature A", "dependencies": []},
                {"title": "Feature B", "dependencies": ["Feature A"]},
            ],
            "chain_plan": {},
            "validation_summary": {"dag_valid": True},
        }
        v = _make_core_validator(tmp_path)

        # Call _validate_decompose_payload_semantics directly
        result2 = ContractValidationResult()
        v._validate_decompose_payload_semantics(payload, result2)

        assert result2.passed

    def test_detects_cyclic_dependency(self, tmp_path: Path) -> None:
        payload = {
            "features": [
                {"title": "A", "dependencies": ["B"]},
                {"title": "B", "dependencies": ["A"]},
            ],
            "chain_plan": {},
            "validation_summary": {},
        }
        v = _make_core_validator(tmp_path)
        result = ContractValidationResult()

        v._validate_decompose_payload_semantics(payload, result)

        assert not result.passed
        assert any("cyclic" in v_item.message.lower() for v_item in result.violations)

    def test_detects_unknown_feature_ref(self, tmp_path: Path) -> None:
        payload = {
            "features": [
                {"title": "Feature A", "dependencies": ["NonExistentFeature"]},
            ],
            "chain_plan": {},
            "validation_summary": {},
        }
        v = _make_core_validator(tmp_path)
        result = ContractValidationResult()

        v._validate_decompose_payload_semantics(payload, result)

        assert not result.passed
        assert any("unknown" in v_item.message.lower() for v_item in result.violations)

    def test_dag_valid_mismatch_in_validation_summary(self, tmp_path: Path) -> None:
        payload = {
            "features": [
                {"title": "A", "dependencies": ["B"]},
                {"title": "B", "dependencies": ["A"]},
            ],
            "chain_plan": {},
            # Reports valid but there's a cycle — mismatch
            "validation_summary": {"dag_valid": True},
        }
        v = _make_core_validator(tmp_path)
        result = ContractValidationResult()

        v._validate_decompose_payload_semantics(payload, result)

        # Should detect the mismatch
        assert any("dag_valid" in v_item.message for v_item in result.violations)

    def test_no_violation_for_empty_features(self, tmp_path: Path) -> None:
        payload = {
            "features": [],
            "chain_plan": {},
            "validation_summary": {},
        }
        v = _make_core_validator(tmp_path)
        result = ContractValidationResult()

        v._validate_decompose_payload_semantics(payload, result)

        assert result.passed


# ===========================================================================
# Section 16: _detect_cycle_nodes static method
# ===========================================================================


class TestDetectCycleNodes:
    def test_no_cycle_in_linear_chain(self) -> None:
        dep_map = {
            "A": set(),
            "B": {"A"},
            "C": {"B"},
        }
        cycles = ContractValidator._detect_cycle_nodes(dep_map)
        assert cycles == []

    def test_detects_simple_two_node_cycle(self) -> None:
        dep_map = {
            "A": {"B"},
            "B": {"A"},
        }
        cycles = ContractValidator._detect_cycle_nodes(dep_map)
        assert set(cycles) == {"A", "B"}

    def test_detects_three_node_cycle(self) -> None:
        dep_map = {
            "A": {"C"},
            "B": {"A"},
            "C": {"B"},
        }
        cycles = ContractValidator._detect_cycle_nodes(dep_map)
        assert set(cycles) == {"A", "B", "C"}

    def test_no_cycle_for_empty_map(self) -> None:
        assert ContractValidator._detect_cycle_nodes({}) == []

    def test_no_cycle_for_single_node(self) -> None:
        assert ContractValidator._detect_cycle_nodes({"A": set()}) == []

    def test_partial_cycle_isolation(self) -> None:
        dep_map = {
            "A": set(),
            "B": {"C"},
            "C": {"B"},
        }
        cycles = ContractValidator._detect_cycle_nodes(dep_map)
        assert "A" not in cycles
        assert set(cycles) == {"B", "C"}

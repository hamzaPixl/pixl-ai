"""Contract validation engine for workflow stage output contracts.

After a task completes, the ContractValidator checks its outputs
against a declarative StageContract. Violations are accumulated
(no fail-on-first) and returned as a ContractValidationResult.

Git-based checks use a baseline commit for deterministic results.
If git is unavailable, checks are skipped with a GIT_UNAVAILABLE event.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import TYPE_CHECKING

from pixl.execution.contract_constants import STUB_PATTERNS
from pixl.execution.git_utils import git_changed_files, git_diff_line_count
from pixl.execution.review_validator import normalize_review_payload
from pixl.execution.validation.git_diff_validator import (
    check_max_diff_lines,
    check_max_files_changed,
    check_must_update_files,
)
from pixl.execution.validation.models import ContractValidationResult, ContractViolation
from pixl.execution.validation.stub_detector import detect_stubs as _detect_stubs
from pixl.execution.validation.success_criteria import (
    extract_key_terms,
)
from pixl.execution.validation.success_criteria import (
    verify_success_criteria as _verify_success_criteria,
)

if TYPE_CHECKING:
    from pixl.models.stage_output import StageOutput
    from pixl.models.workflow_config import StageContract

class ContractValidator:
    """Validates stage outputs against a StageContract.

    Args:
        project_root: Project root directory for resolving file paths
        artifacts_dir: Directory for stage artifacts
        baseline_commit: Git commit hash at workflow start (for diff checks)
    """

    STUB_PATTERNS = STUB_PATTERNS  # Re-exported from contract_constants

    def __init__(
        self,
        project_root: Path,
        artifacts_dir: Path,
        baseline_commit: str | None = None,
        agent_cwd: Path | None = None,
    ) -> None:
        self.project_root = project_root
        self.artifacts_dir = artifacts_dir
        self.baseline_commit = baseline_commit
        self.agent_cwd = agent_cwd

    def validate(
        self,
        contract: StageContract,
        *,
        success_criteria: list[str] | None = None,
        changed_files: list[str] | None = None,
        max_context_tokens: int | None = None,
        transcript_path: Path | None = None,
    ) -> ContractValidationResult:
        """Run all contract checks and accumulate violations.

        Args:
            contract: StageContract to validate against
            success_criteria: Optional success criteria for goal-backward verification
            changed_files: Optional list of changed files (overrides git diff)
            max_context_tokens: Optional context window size for budget checks

        Returns:
            ContractValidationResult with all violations
        """

        result = ContractValidationResult()

        if changed_files is None and (
            contract.must_update_files
            or contract.verify_success_criteria
            or contract.require_regression_test
        ):
            changed_files = self._git_changed_files(result)
            if changed_files is not None:
                changed_files = list(changed_files)

        if contract.must_write:
            self._check_must_write(contract.must_write, result)

        if contract.must_include_sections:
            self._check_must_include_sections(contract.must_include_sections, result)

        if contract.must_include_command_blocks and contract.must_write:
            self._check_must_include_command_blocks(contract.must_write, result)

        if contract.must_update_files:
            self._check_must_update_files(contract.must_update_files, result, changed_files)

        if contract.max_diff_lines is not None:
            self._check_max_diff_lines(contract.max_diff_lines, result)

        if contract.max_files_changed is not None:
            self._check_max_files_changed(contract.max_files_changed, result)

        if contract.artifact_schemas:
            self._check_artifact_schemas(contract.artifact_schemas, result)

        # Stub detection (optional)
        if contract.detect_stubs:
            files_to_scan = list(dict.fromkeys(contract.must_write + contract.must_update_files))
            if files_to_scan:
                self.detect_stubs(files_to_scan, result)

        # Require regression test (optional)
        if contract.require_regression_test:
            files_for_tests = set(contract.must_write + contract.must_update_files)
            if changed_files:
                files_for_tests.update(changed_files)
            self._check_regression_test(sorted(files_for_tests), result)

        # Goal-backward verification (optional)
        if contract.verify_success_criteria:
            if not success_criteria:
                result.warnings.append(
                    "verify_success_criteria skipped: no success criteria provided"
                )
            elif changed_files is None:
                result.warnings.append("verify_success_criteria skipped: git unavailable")
            else:
                self.verify_success_criteria(success_criteria, changed_files, result)

        # Context budget check (optional)
        if contract.context_budget_pct:
            self._check_context_budget(
                contract.context_budget_pct,
                contract.must_write,
                max_context_tokens,
                result,
            )

        # Skill/agent usage enforcement (optional)
        if contract.required_skills:
            from pixl.execution.validation.skill_usage_validator import check_required_skills

            check_required_skills(contract.required_skills, transcript_path, result)

        if contract.required_agents:
            from pixl.execution.validation.skill_usage_validator import check_required_agents

            check_required_agents(contract.required_agents, transcript_path, result)

        return result

    def validate_frozen_artifacts(
        self,
        frozen_artifacts: dict[str, str],
    ) -> ContractValidationResult:
        """Check that frozen artifacts haven't been modified.

        Args:
            frozen_artifacts: Dict of path -> expected SHA256 hash

        Returns:
            ContractValidationResult with violations for modified/missing files
        """
        result = ContractValidationResult()

        for path, expected_hash in frozen_artifacts.items():
            file_path = self._resolve_path(path)
            if not file_path.exists():
                result.violations.append(
                    ContractViolation(
                        rule="frozen_artifact_missing",
                        message=f"Frozen artifact missing: {path}",
                    )
                )
                continue

            actual_hash = self._compute_sha256(file_path)
            if actual_hash != expected_hash:
                result.violations.append(
                    ContractViolation(
                        rule="frozen_artifact_modified",
                        message=(
                            f"Frozen artifact modified: {path} "
                            f"(expected {expected_hash[:12]}..., got {actual_hash[:12]}...)"
                        ),
                    )
                )

        return result

    def validate_structured_output(
        self,
        stage_output: StageOutput,
        output_schema_path: str | None = None,
    ) -> ContractValidationResult:
        """Validate a structured StageOutput against expectations.

        Checks:
        1. Status is 'ok'
        2. Summary is non-empty
        3. Artifacts exist with matching SHA256 hashes
        4. Payload validates against JSON Schema (if schema path given)

        Args:
            stage_output: Parsed StageOutput from envelope extraction
            output_schema_path: Optional path to JSON Schema for payload validation

        Returns:
            ContractValidationResult with any violations
        """

        result = ContractValidationResult()

        # 1. Check status
        if stage_output.status != "ok":
            error_msg = "unknown error"
            if stage_output.error:
                error_msg = stage_output.error.message
            result.violations.append(
                ContractViolation(
                    rule="structured_output_status",
                    message=f"Stage reported error status: {error_msg}",
                )
            )

        # 2. Check summary non-empty
        if not stage_output.summary:
            result.violations.append(
                ContractViolation(
                    rule="structured_output_summary",
                    message="Structured output has empty summary",
                )
            )

        # 3. Check artifacts exist with matching hashes
        for artifact in stage_output.artifacts_written:
            file_path = self._resolve_path(artifact.path)
            if not file_path.exists():
                result.violations.append(
                    ContractViolation(
                        rule="structured_output_artifact_missing",
                        message=f"Declared artifact not found: {artifact.path}",
                    )
                )
                continue

            actual_hash = self._compute_sha256(file_path)
            if actual_hash != artifact.sha256:
                result.warnings.append(
                    f"Hash mismatch for {artifact.path}: "
                    f"declared {artifact.sha256[:12]}..., "
                    f"actual {actual_hash[:12]}..."
                )

        # 4. Validate payload against JSON Schema
        if output_schema_path:
            self._validate_payload_schema(
                stage_output.payload,
                output_schema_path,
                result,
            )
            self._validate_payload_semantics(
                stage_output.payload,
                output_schema_path,
                result,
            )

        return result

    def _validate_payload_schema(
        self,
        payload: dict,
        schema_path: str,
        result: ContractValidationResult,
    ) -> None:
        """Validate a stage output payload against a JSON Schema file."""
        try:
            import json

            import jsonschema
        except ImportError:
            result.warnings.append(
                "structured_output payload schema validation skipped: jsonschema not installed"
            )
            return

        resolved_schema = self._resolve_path(schema_path)
        if not resolved_schema.exists():
            result.violations.append(
                ContractViolation(
                    rule="structured_output_schema",
                    message=f"Output schema file not found: {schema_path}",
                )
            )
            return

        try:
            schema_data = json.loads(resolved_schema.read_text(encoding="utf-8"))
            if Path(schema_path).name == "review-payload.json":
                normalize_review_payload(payload)
            jsonschema.validate(instance=payload, schema=schema_data)
        except json.JSONDecodeError as e:
            result.violations.append(
                ContractViolation(
                    rule="structured_output_schema",
                    message=f"Invalid JSON in schema {schema_path}: {e}",
                )
            )
        except jsonschema.ValidationError as e:
            result.violations.append(
                ContractViolation(
                    rule="structured_output_schema",
                    message=f"Payload schema validation failed: {e.message}",
                )
            )

    def _validate_payload_semantics(
        self,
        payload: dict,
        schema_path: str,
        result: ContractValidationResult,
    ) -> None:
        """Apply schema-specific semantic validation after JSON Schema checks."""
        schema_name = Path(schema_path).name
        if schema_name == "decompose-payload.json":
            self._validate_decompose_payload_semantics(payload, result)
        if schema_name == "roadmap-plan-payload.json":
            self._validate_roadmap_plan_payload_semantics(payload, result)

    def _validate_decompose_payload_semantics(
        self,
        payload: dict,
        result: ContractValidationResult,
    ) -> None:
        """Validate DAG semantics for decompose payloads."""
        features = payload.get("features") or []
        chain_plan = payload.get("chain_plan") or {}
        validation_summary = payload.get("validation_summary") or {}

        if not isinstance(features, list) or not isinstance(chain_plan, dict):
            return

        feature_refs: set[str] = set()
        for feature in features:
            if not isinstance(feature, dict):
                continue
            ref = feature.get("title")
            if isinstance(ref, str) and ref:
                feature_refs.add(ref)

        if not feature_refs:
            return

        dependency_map: dict[str, set[str]] = {ref: set() for ref in feature_refs}
        unknown_refs: set[str] = set()

        # Feature-level dependencies
        for feature in features:
            if not isinstance(feature, dict):
                continue
            feature_ref = feature.get("title")
            if not isinstance(feature_ref, str) or feature_ref not in dependency_map:
                continue
            dependencies = feature.get("dependencies") or []
            if not isinstance(dependencies, list):
                continue
            for dep in dependencies:
                if isinstance(dep, str) and dep in dependency_map:
                    dependency_map[feature_ref].add(dep)
                else:
                    unknown_refs.add(str(dep))

        # Chain node references and node-level dependencies
        nodes = chain_plan.get("nodes") or []
        if isinstance(nodes, list):
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                feature_ref = node.get("feature_ref")
                if not isinstance(feature_ref, str) or not feature_ref:
                    continue
                if feature_ref not in dependency_map:
                    unknown_refs.add(feature_ref)
                    continue
                depends_on = node.get("depends_on") or []
                if not isinstance(depends_on, list):
                    continue
                for dep in depends_on:
                    if isinstance(dep, str) and dep in dependency_map:
                        dependency_map[feature_ref].add(dep)
                    else:
                        unknown_refs.add(str(dep))

        # Chain explicit edges
        edges = chain_plan.get("edges") or []
        if isinstance(edges, list):
            for edge in edges:
                if not isinstance(edge, dict):
                    continue
                src = edge.get("from")
                dst = edge.get("to")
                src_valid = isinstance(src, str) and src in dependency_map
                dst_valid = isinstance(dst, str) and dst in dependency_map
                if not src_valid:
                    unknown_refs.add(str(src))
                if not dst_valid:
                    unknown_refs.add(str(dst))
                if src_valid and dst_valid:
                    dependency_map[dst].add(src)  # dst depends on src

        # Chain waves
        waves = chain_plan.get("waves") or []
        if isinstance(waves, list):
            for wave in waves:
                if not isinstance(wave, list):
                    continue
                for ref in wave:
                    if not isinstance(ref, str) or ref not in dependency_map:
                        unknown_refs.add(str(ref))

        # Orphans from the merged dependency graph
        incoming: dict[str, int] = dict.fromkeys(dependency_map, 0)
        outgoing: dict[str, int] = dict.fromkeys(dependency_map, 0)
        for feature_ref, deps in dependency_map.items():
            for dep in deps:
                incoming[feature_ref] += 1
                outgoing[dep] += 1
        orphan_nodes = sorted(
            ref for ref in dependency_map if incoming.get(ref, 0) == 0 and outgoing.get(ref, 0) == 0
        )

        cycle_nodes = self._detect_cycle_nodes(dependency_map)
        computed_dag_valid = len(cycle_nodes) == 0 and len(unknown_refs) == 0

        # Compare with reported validation summary
        reported_dag_valid = validation_summary.get("dag_valid")
        if isinstance(reported_dag_valid, bool) and reported_dag_valid != computed_dag_valid:
            result.violations.append(
                ContractViolation(
                    rule="structured_output_semantics",
                    message=(
                        "validation_summary.dag_valid does not match computed DAG validity "
                        f"(reported={reported_dag_valid}, computed={computed_dag_valid})"
                    ),
                )
            )

        reported_cycles = validation_summary.get("cycles_detected")
        if isinstance(reported_cycles, list):
            reported_cycle_set = {str(item) for item in reported_cycles}
            computed_cycle_set = set(cycle_nodes)
            if reported_cycle_set != computed_cycle_set:
                result.violations.append(
                    ContractViolation(
                        rule="structured_output_semantics",
                        message=(
                            "validation_summary.cycles_detected does not match computed cycles "
                            f"(reported={sorted(reported_cycle_set)}, computed={sorted(computed_cycle_set)})"
                        ),
                    )
                )

        reported_orphans = validation_summary.get("orphan_nodes")
        if isinstance(reported_orphans, list):
            reported_orphan_set = {str(item) for item in reported_orphans}
            computed_orphan_set = set(orphan_nodes)
            if reported_orphan_set != computed_orphan_set:
                result.violations.append(
                    ContractViolation(
                        rule="structured_output_semantics",
                        message=(
                            "validation_summary.orphan_nodes does not match computed orphan nodes "
                            f"(reported={sorted(reported_orphan_set)}, computed={sorted(computed_orphan_set)})"
                        ),
                    )
                )

        if unknown_refs:
            result.violations.append(
                ContractViolation(
                    rule="structured_output_semantics",
                    message=f"Unknown feature references in decomposition graph: {sorted(unknown_refs)}",
                )
            )

        if cycle_nodes:
            result.violations.append(
                ContractViolation(
                    rule="structured_output_semantics",
                    message=f"Cyclic feature dependencies detected: {cycle_nodes}",
                )
            )

    @staticmethod
    def _detect_cycle_nodes(dependency_map: dict[str, set[str]]) -> list[str]:
        """Return feature refs that participate in dependency cycles."""
        color: dict[str, int] = dict.fromkeys(dependency_map, 0)
        path: list[str] = []
        cycle_nodes: set[str] = set()

        def dfs(node: str) -> None:
            color[node] = 1
            path.append(node)
            for dep in dependency_map.get(node, set()):
                if dep not in color:
                    continue
                if color[dep] == 0:
                    dfs(dep)
                elif color[dep] == 1:
                    idx = path.index(dep)
                    cycle_nodes.update(path[idx:])
            path.pop()
            color[node] = 2

        for node in sorted(dependency_map):
            if color[node] == 0:
                dfs(node)

        return sorted(cycle_nodes)

    def _validate_roadmap_plan_payload_semantics(
        self,
        payload: dict,
        result: ContractValidationResult,
    ) -> None:
        """Validate milestone dependency DAG semantics for roadmap plan payloads."""
        milestones = payload.get("milestones") or []
        if not isinstance(milestones, list) or not milestones:
            return

        milestone_names: set[str] = set()
        for ms in milestones:
            if not isinstance(ms, dict):
                continue
            name = ms.get("name")
            if isinstance(name, str) and name.strip():
                milestone_names.add(name.strip())

        if not milestone_names:
            return

        dependency_map: dict[str, set[str]] = {name: set() for name in milestone_names}
        unknown_refs: set[str] = set()

        for ms in milestones:
            if not isinstance(ms, dict):
                continue
            name = ms.get("name")
            if not isinstance(name, str) or name.strip() not in dependency_map:
                continue
            deps = ms.get("milestone_dependencies") or []
            if not isinstance(deps, list):
                continue
            for dep in deps:
                dep_name = str(dep).strip()
                if not dep_name:
                    continue
                if dep_name in dependency_map:
                    dependency_map[name.strip()].add(dep_name)
                else:
                    unknown_refs.add(dep_name)

        cycle_nodes = self._detect_cycle_nodes(dependency_map)
        if unknown_refs:
            result.violations.append(
                ContractViolation(
                    rule="structured_output_semantics",
                    message=f"Unknown milestone references in roadmap plan: {sorted(unknown_refs)}",
                )
            )
        if cycle_nodes:
            result.violations.append(
                ContractViolation(
                    rule="structured_output_semantics",
                    message=f"Cyclic milestone dependencies detected: {cycle_nodes}",
                )
            )

    # Individual Check Methods

    def _check_must_write(
        self,
        must_write: list[str],
        result: ContractValidationResult,
    ) -> None:
        """Check that required files exist."""
        for path in must_write:
            resolved = self._resolve_path(path)
            if not resolved.exists():
                result.violations.append(
                    ContractViolation(
                        rule="must_write",
                        message=f"Required file not found: {path}",
                    )
                )

    def _check_must_include_sections(
        self,
        must_include_sections: dict[str, list[str]],
        result: ContractValidationResult,
    ) -> None:
        """Check that files contain required section headings."""
        for file_path, required_sections in must_include_sections.items():
            resolved = self._resolve_path(file_path)
            if not resolved.exists():
                result.violations.append(
                    ContractViolation(
                        rule="must_include_sections",
                        message=f"File not found for section check: {file_path}",
                    )
                )
                continue

            content = resolved.read_text(encoding="utf-8")
            headings = self._extract_headings(content)
            normalized_headings = [self._normalize_heading(h) for h in headings]

            for required in required_sections:
                aliases = [alias.strip() for alias in required.split("|")]
                matched = False
                for alias in aliases:
                    normalized_alias = self._normalize_heading(alias)
                    if any(normalized_alias in h for h in normalized_headings):
                        matched = True
                        break
                if not matched:
                    result.violations.append(
                        ContractViolation(
                            rule="must_include_sections",
                            message=(
                                f"Missing required section in {file_path}: "
                                f"'{required}' (checked aliases: {aliases})"
                            ),
                        )
                    )

    def _check_must_include_command_blocks(
        self,
        must_write: list[str],
        result: ContractValidationResult,
    ) -> None:
        """Check that at least one must_write file contains command blocks."""
        found = False
        for path in must_write:
            resolved = self._resolve_path(path)
            if not resolved.exists():
                continue

            content = resolved.read_text(encoding="utf-8")
            if self._has_command_blocks(content):
                found = True
                break

        if not found:
            result.violations.append(
                ContractViolation(
                    rule="must_include_command_blocks",
                    message=(
                        "No command blocks found in must_write files. "
                        "Expected fenced ```bash/shell/sh blocks or lines starting with '$ '"
                    ),
                )
            )

    def _check_must_update_files(
        self,
        must_update_files: list[str],
        result: ContractValidationResult,
        changed_files: list[str] | None = None,
    ) -> None:
        """Check that specified files appear in git diff."""
        check_must_update_files(must_update_files, result, changed_files, self._git_changed_files)

    def _check_max_diff_lines(
        self,
        max_diff_lines: int,
        result: ContractValidationResult,
    ) -> None:
        """Check that diff size doesn't exceed limit."""
        check_max_diff_lines(max_diff_lines, result, self._git_diff_line_count)

    def _check_max_files_changed(
        self,
        max_files_changed: int,
        result: ContractValidationResult,
    ) -> None:
        """Check that number of changed files doesn't exceed limit."""
        check_max_files_changed(max_files_changed, result, self._git_changed_files)

    def _check_artifact_schemas(
        self,
        artifact_schemas: dict[str, str],
        result: ContractValidationResult,
    ) -> None:
        """Validate artifact JSON files against JSON schemas."""
        try:
            import json

            import jsonschema
        except ImportError:
            # jsonschema not installed, skip with warning
            result.git_unavailable_checks.append("artifact_schemas (jsonschema not installed)")
            return

        for artifact_path, schema_path in artifact_schemas.items():
            resolved_artifact = self._resolve_path(artifact_path)
            resolved_schema = self._resolve_path(schema_path)

            if not resolved_artifact.exists():
                result.violations.append(
                    ContractViolation(
                        rule="artifact_schemas",
                        message=f"Artifact not found for schema validation: {artifact_path}",
                    )
                )
                continue

            if not resolved_schema.exists():
                result.violations.append(
                    ContractViolation(
                        rule="artifact_schemas",
                        message=f"Schema file not found: {schema_path}",
                    )
                )
                continue

            try:
                artifact_data = json.loads(resolved_artifact.read_text(encoding="utf-8"))
                schema_data = json.loads(resolved_schema.read_text(encoding="utf-8"))
                jsonschema.validate(instance=artifact_data, schema=schema_data)
            except json.JSONDecodeError as e:
                result.violations.append(
                    ContractViolation(
                        rule="artifact_schemas",
                        message=f"Invalid JSON in {artifact_path}: {e}",
                    )
                )
            except jsonschema.ValidationError as e:
                result.violations.append(
                    ContractViolation(
                        rule="artifact_schemas",
                        message=f"Schema validation failed for {artifact_path}: {e.message}",
                    )
                )

    # Stub Detection (GAP-09: Distrust Model) — delegates to stub_detector

    def detect_stubs(
        self,
        files: list[str],
        result: ContractValidationResult,
    ) -> list[dict[str, str]]:
        """Scan files for stub/placeholder patterns indicating incomplete implementation."""
        return _detect_stubs(files, self._resolve_path, result, self.STUB_PATTERNS)

    # Goal-Backward Verification (GAP-02) — delegates to success_criteria

    def verify_success_criteria(
        self,
        success_criteria: list[str],
        changed_files: list[str],
        result: ContractValidationResult,
    ) -> dict[str, bool]:
        """Verify implementation against explicit success criteria."""
        return _verify_success_criteria(success_criteria, changed_files, self._resolve_path, result)

    @staticmethod
    def _extract_key_terms(text: str) -> list[str]:
        """Extract meaningful terms from a criterion for evidence search."""
        return extract_key_terms(text)

    # Regression Test Requirement (GAP-09)

    @staticmethod
    def _looks_like_test(path: str) -> bool:
        """Heuristic check for test file paths."""
        lowered = path.lower().replace("\\", "/")
        if "/test/" in lowered or "/tests/" in lowered:
            return True
        basename = Path(lowered).name
        if basename.startswith("test_"):
            return True
        if re.search(r"(_test|\.test)\.[a-z0-9]+$", basename):
            return True
        return bool(re.search(r"\.spec\.[a-z0-9]+$", basename))

    def _check_regression_test(
        self,
        files: list[str],
        result: ContractValidationResult,
    ) -> None:
        """Require at least one test file in the provided file list."""
        if not files:
            result.violations.append(
                ContractViolation(
                    rule="regression_test_missing",
                    message="No files available to verify regression test requirement",
                )
            )
            return

        if not any(self._looks_like_test(p) for p in files):
            result.violations.append(
                ContractViolation(
                    rule="regression_test_missing",
                    message="No test files found (expected at least one test file)",
                )
            )

    # Context Budget Check (GAP-01)

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Estimate tokens in text using content-type-aware ratio."""
        from pixl.utils.tokens import estimate_tokens

        return estimate_tokens(text, "default")

    def _check_context_budget(
        self,
        context_budget_pct: int,
        files: list[str],
        max_context_tokens: int | None,
        result: ContractValidationResult,
    ) -> None:
        """Warn if plan outputs exceed context budget."""
        if max_context_tokens is None:
            result.warnings.append("context_budget_pct set but max_context_tokens unavailable")
            return

        if not files:
            result.warnings.append("context_budget_pct set but no must_write files to measure")
            return

        total_tokens = 0
        for path in files:
            resolved = self._resolve_path(path)
            if not resolved.exists():
                continue
            try:
                content = resolved.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            total_tokens += self._estimate_tokens(content)

        if total_tokens == 0:
            return

        budget_tokens = int(max_context_tokens * (context_budget_pct / 100))
        if total_tokens > budget_tokens:
            result.warnings.append(
                f"context_budget_exceeded: {total_tokens} > {budget_tokens} tokens"
            )

    # Helpers

    def _resolve_path(self, path: str) -> Path:
        """Resolve a path, checking multiple locations.

        Search order:
        1. artifacts_dir / path
        2. project_root / path
        3. Absolute path (if path is absolute)
        4. CWD / path (agents may write relative to working directory)
        """
        # Check artifacts dir first
        artifacts_path = self.artifacts_dir / path
        if artifacts_path.exists():
            return artifacts_path

        # Handle agents declaring "artifacts/foo.md" when file is at {artifacts_dir}/foo.md
        if path.startswith("artifacts/"):
            stripped_path = self.artifacts_dir / path[len("artifacts/") :]
            if stripped_path.exists():
                return stripped_path

        # Check project root
        project_path = self.project_root / path
        if project_path.exists():
            return project_path

        # Check agent CWD (worktree subdirectory where agent was running)
        if self.agent_cwd is not None:
            agent_path = self.agent_cwd / path
            if agent_path.exists():
                return agent_path

        abs_path = Path(path)
        if abs_path.is_absolute() and abs_path.exists():
            return abs_path

        # Check CWD (agents may write relative to working directory)
        cwd_path = Path.cwd() / path
        if cwd_path.exists():
            return cwd_path

        # Last resort: search by stripping leading directory components one at a time.
        # Handles agents that cd into nested dirs and declare paths relative to their CWD.
        target_parts = Path(path).parts
        if len(target_parts) > 1:
            for i in range(1, len(target_parts)):
                candidate = self.project_root / Path(*target_parts[i:])
                if candidate.exists():
                    return candidate

        # Default to project root (caller handles non-existence)
        return project_path

    @staticmethod
    def _extract_headings(content: str) -> list[str]:
        """Extract markdown headings from content."""
        headings = []
        for line in content.splitlines():
            match = re.match(r"^#+\s+(.+)$", line)
            if match:
                headings.append(match.group(1))
        return headings

    @staticmethod
    def _normalize_heading(text: str) -> str:
        """Normalize a heading for comparison."""
        text = re.sub(r"[^\w\s]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text.lower()

    @staticmethod
    def _has_command_blocks(content: str) -> bool:
        """Check if content contains command blocks."""
        if re.search(r"```(?:bash|shell|sh)\b", content):
            return True

        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("$ "):
                return True

        return False

    @staticmethod
    def _compute_sha256(file_path: Path) -> str:
        """Compute SHA256 hash of a file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _git_changed_files(
        self,
        result: ContractValidationResult,
    ) -> set[str] | None:
        """Get set of changed files from git diff."""
        if not self.baseline_commit:
            result.git_unavailable_checks.append("must_update_files (no baseline_commit)")
            return None

        files, err = git_changed_files(self.project_root, self.baseline_commit)
        if err:
            result.git_unavailable_checks.append(err)
        return files

    def _git_diff_line_count(
        self,
        result: ContractValidationResult,
    ) -> int | None:
        """Get total diff line count (insertions + deletions)."""
        if not self.baseline_commit:
            result.git_unavailable_checks.append("max_diff_lines (no baseline_commit)")
            return None

        count, err = git_diff_line_count(self.project_root, self.baseline_commit)
        if err:
            result.git_unavailable_checks.append(err)
        return count

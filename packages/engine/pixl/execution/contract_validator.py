"""Contract validation engine for workflow stage output contracts.

After a task completes, the ContractValidator checks its outputs
against a declarative StageContract. Violations are accumulated
(no fail-on-first) and returned as a ContractValidationResult.

Git-based checks use a baseline commit for deterministic results.
If git is unavailable, checks are skipped with a GIT_UNAVAILABLE event.
"""

from __future__ import annotations

import fnmatch
import hashlib
import logging
import re
import subprocess
from collections.abc import Callable
from pathlib import Path, PurePath, PurePosixPath
from typing import TYPE_CHECKING

from pixl.execution.contract_constants import STUB_PATTERNS
from pixl.execution.review_validator import normalize_review_payload
from pixl.execution.validation.models import ContractValidationResult, ContractViolation

logger = logging.getLogger(__name__)

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

    def __init__(
        self,
        project_root: Path,
        artifacts_dir: Path,
        baseline_commit: str | None = None,
        artifact_loader: Callable[[str], str | None] | None = None,
        artifact_saver: Callable[[str, str], None] | None = None,
    ) -> None:
        self.project_root = project_root
        self.artifacts_dir = artifacts_dir
        self.baseline_commit = baseline_commit
        self._artifact_loader = artifact_loader
        self._artifact_saver = artifact_saver

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

        needs_changed_files = (
            contract.must_update_files
            or contract.verify_success_criteria
            or contract.require_regression_test
            or contract.scope_boundary
            or contract.forbidden_paths
        )
        if changed_files is None and needs_changed_files:
            changed_files = self._git_changed_files(result)

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

        if contract.scope_boundary or contract.forbidden_paths:
            self._check_scope_boundary(
                contract.scope_boundary, contract.forbidden_paths, result, changed_files
            )

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
            content, logical_path = self._load_artifact_text(path)
            if logical_path is None:
                result.violations.append(
                    ContractViolation(
                        rule="frozen_artifact_invalid_path",
                        message=f"Invalid frozen artifact path (session-scoped only): {path}",
                    )
                )
                continue

            if content is None:
                result.violations.append(
                    ContractViolation(
                        rule="frozen_artifact_missing",
                        message=f"Frozen artifact missing in session store: {path}",
                    )
                )
                continue

            actual_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            if actual_hash != expected_hash:
                result.violations.append(
                    ContractViolation(
                        rule="frozen_artifact_modified",
                        message=(
                            f"Frozen artifact modified: {logical_path} "
                            f"(expected {expected_hash[:12]}..., got {actual_hash[:12]}...)"
                        ),
                    )
                )

        return result

    def validate_structured_output(
        self,
        stage_output: StageOutput,
        output_schema_path: str | None = None,
        required_artifacts: list[str] | None = None,
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
            required_artifacts: Optional list of required artifacts expected to
                appear in included_sources provenance.

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
            content, logical_path = self._load_artifact_text(artifact.path)
            if logical_path is None:
                result.violations.append(
                    ContractViolation(
                        rule="structured_output_artifact_missing",
                        message=f"Declared artifact has invalid session path: {artifact.path}",
                    )
                )
                continue

            if content is None:
                # Auto-register fallback: if the file exists in the worktree,
                # register it into the session store automatically.
                content = self._try_auto_register_from_worktree(logical_path, result)

            if content is None:
                detail = (
                    "Declared artifact not found in session artifact store: "
                    if self._artifact_loader
                    else "Declared artifact not found: "
                )
                result.violations.append(
                    ContractViolation(
                        rule="structured_output_artifact_missing",
                        message=f"{detail}{artifact.path}",
                    )
                )
                continue

            actual_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            if actual_hash != artifact.sha256:
                result.warnings.append(
                    f"Hash mismatch for {logical_path}: "
                    f"declared {artifact.sha256[:12]}..., "
                    f"actual {actual_hash[:12]}..."
                )

        self._check_required_artifact_provenance(
            stage_output=stage_output,
            required_artifacts=required_artifacts,
            result=result,
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

    def _check_required_artifact_provenance(
        self,
        *,
        stage_output: StageOutput,
        required_artifacts: list[str] | None,
        result: ContractValidationResult,
    ) -> None:
        """Warn when required artifacts are missing from included_sources."""
        if not required_artifacts:
            return

        required_paths = {
            normalized
            for path in required_artifacts
            if (normalized := self._normalize_artifact_logical_path(path)) is not None
        }
        if not required_paths:
            return

        included_paths = {
            normalized
            for source in stage_output.included_sources
            if (normalized := self._normalize_artifact_logical_path(source.artifact_id)) is not None
        }
        missing = sorted(path for path in required_paths if path not in included_paths)
        if missing:
            result.warnings.append("required_artifact_provenance_missing: " + ", ".join(missing))

    def _validate_payload_schema(
        self,
        payload: dict,
        schema_path: str,
        result: ContractValidationResult,
    ) -> None:
        """Validate a stage output payload against a JSON Schema file.

        Args:
            payload: Stage payload dict to validate
            schema_path: Path to the JSON Schema file
            result: Result to accumulate violations into
        """
        try:
            import json

            import jsonschema
        except ImportError:
            result.warnings.append(
                "structured_output payload schema validation skipped: jsonschema not installed"
            )
            return

        resolved_schema = self._resolve_workspace_path(schema_path)
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
                    dependency_map[dst].add(src)  # type: ignore[index]  # dst is str after dst_valid check

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
            exists, logical_path = self._artifact_exists(path)
            if logical_path is None:
                result.violations.append(
                    ContractViolation(
                        rule="must_write",
                        message=f"Invalid artifact path (session-scoped only): {path}",
                    )
                )
                continue
            if not exists:
                detail = (
                    "Required artifact not found in session artifact store"
                    if self._artifact_loader
                    else "Required artifact not found"
                )
                result.violations.append(
                    ContractViolation(
                        rule="must_write",
                        message=f"{detail}: {path}",
                    )
                )

    def _check_must_include_sections(
        self,
        must_include_sections: dict[str, list[str]],
        result: ContractValidationResult,
    ) -> None:
        """Check that files contain required section headings."""
        for file_path, required_sections in must_include_sections.items():
            content, logical_path = self._load_artifact_text(file_path)
            if logical_path is None:
                result.violations.append(
                    ContractViolation(
                        rule="must_include_sections",
                        message=f"Invalid artifact path (session-scoped only): {file_path}",
                    )
                )
                continue

            if content is None:
                detail = (
                    "Artifact not found in session artifact store"
                    if self._artifact_loader
                    else "Artifact not found for section check"
                )
                result.violations.append(
                    ContractViolation(
                        rule="must_include_sections",
                        message=f"{detail}: {file_path}",
                    )
                )
                continue

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
                                f"Missing required section in {logical_path}: "
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
            content, logical_path = self._load_artifact_text(path)
            if logical_path is None:
                result.violations.append(
                    ContractViolation(
                        rule="must_include_command_blocks",
                        message=f"Invalid artifact path (session-scoped only): {path}",
                    )
                )
                continue
            if content is None:
                continue
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
        if changed_files is None:
            changed_files = self._git_changed_files(result)
            if changed_files is None:
                return  # git unavailable, already recorded

        for pattern in must_update_files:
            if not any(PurePath(f).match(pattern) for f in changed_files):
                result.violations.append(
                    ContractViolation(
                        rule="must_update_files",
                        message=f"Expected file to be modified: {pattern}",
                    )
                )

    def _check_max_diff_lines(
        self,
        max_diff_lines: int,
        result: ContractValidationResult,
    ) -> None:
        """Check that diff size doesn't exceed limit."""
        total_lines = self._git_diff_line_count(result)
        if total_lines is None:
            return  # git unavailable

        if total_lines > max_diff_lines:
            result.violations.append(
                ContractViolation(
                    rule="max_diff_lines",
                    message=(f"Diff too large: {total_lines} lines (max: {max_diff_lines})"),
                )
            )

    def _check_max_files_changed(
        self,
        max_files_changed: int,
        result: ContractValidationResult,
    ) -> None:
        """Check that number of changed files doesn't exceed limit."""
        changed_files = self._git_changed_files(result)
        if changed_files is None:
            return  # git unavailable

        if len(changed_files) > max_files_changed:
            result.violations.append(
                ContractViolation(
                    rule="max_files_changed",
                    message=(
                        f"Too many files changed: {len(changed_files)} (max: {max_files_changed})"
                    ),
                )
            )

    def _check_scope_boundary(
        self,
        scope_boundary: list[str],
        forbidden_paths: list[str],
        result: ContractValidationResult,
        changed_files: list[str] | None = None,
    ) -> None:
        """Check that changed files fall within scope boundary.

        Args:
            scope_boundary: Glob patterns of allowed file paths.
                If non-empty, files not matching any pattern are violations.
            forbidden_paths: Glob patterns of forbidden file paths.
                Files matching any pattern are always violations (takes
                precedence over scope_boundary).
            result: Result to accumulate violations into.
            changed_files: Pre-resolved list of changed files.
        """
        if changed_files is None:
            changed_files_raw = self._git_changed_files(result)
            if changed_files_raw is None:
                return  # git unavailable, already recorded
            changed_files = list(changed_files_raw)

        out_of_scope: list[str] = []
        forbidden_hits: list[str] = []

        for fpath in changed_files:
            # Check forbidden_paths first (takes precedence)
            if forbidden_paths and any(fnmatch.fnmatch(fpath, pat) for pat in forbidden_paths):
                forbidden_hits.append(fpath)
                continue

            # Check scope_boundary (allow-list)
            if scope_boundary and not any(fnmatch.fnmatch(fpath, pat) for pat in scope_boundary):
                out_of_scope.append(fpath)

        for fpath in forbidden_hits:
            result.violations.append(
                ContractViolation(
                    rule="forbidden_path",
                    message=f"File matches forbidden_paths pattern: {fpath}",
                )
            )

        for fpath in out_of_scope:
            result.violations.append(
                ContractViolation(
                    rule="scope_boundary",
                    message=f"File changed outside scope_boundary: {fpath}",
                )
            )

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
            artifact_content, logical_artifact_path = self._load_artifact_text(artifact_path)
            if logical_artifact_path is None:
                result.violations.append(
                    ContractViolation(
                        rule="artifact_schemas",
                        message=f"Invalid artifact path (session-scoped only): {artifact_path}",
                    )
                )
                continue

            if artifact_content is None:
                detail = (
                    "Artifact not found in session artifact store for schema validation"
                    if self._artifact_loader
                    else "Artifact not found for schema validation"
                )
                result.violations.append(
                    ContractViolation(
                        rule="artifact_schemas",
                        message=f"{detail}: {artifact_path}",
                    )
                )
                continue

            resolved_schema = self._resolve_workspace_path(schema_path)
            if not resolved_schema.exists():
                result.violations.append(
                    ContractViolation(
                        rule="artifact_schemas",
                        message=f"Schema file not found: {schema_path}",
                    )
                )
                continue

            try:
                artifact_data = json.loads(artifact_content)
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

    # Stub Detection (GAP-09: Distrust Model)

    def detect_stubs(
        self,
        files: list[str],
        result: ContractValidationResult,
    ) -> list[dict[str, str]]:
        """Scan files for stub/placeholder patterns indicating incomplete implementation.

        Args:
            files: List of file paths to scan
            result: ContractValidationResult to accumulate violations

        Returns:
            List of detected stubs with file, line number, and matched pattern
        """
        stubs: list[dict[str, str]] = []

        for path in files:
            resolved = self._resolve_workspace_path(path)
            if not resolved.exists():
                continue

            try:
                content = resolved.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue

            for line_num, line in enumerate(content.splitlines(), 1):
                for pattern in STUB_PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        stubs.append(
                            {
                                "file": path,
                                "line": str(line_num),
                                "content": line.strip()[:120],
                                "pattern": pattern,
                            }
                        )
                        break  # One match per line is enough

        if stubs:
            result.violations.append(
                ContractViolation(
                    rule="stub_detected",
                    message=(
                        f"Found {len(stubs)} stub/placeholder pattern(s) in implementation: "
                        + "; ".join(f"{s['file']}:{s['line']}" for s in stubs[:5])
                        + ("..." if len(stubs) > 5 else "")
                    ),
                )
            )

        return stubs

    # Goal-Backward Verification (GAP-02)

    def verify_success_criteria(
        self,
        success_criteria: list[str],
        changed_files: list[str],
        result: ContractValidationResult,
    ) -> dict[str, bool]:
        """Verify implementation against explicit success criteria.

        Uses file content scanning to check whether success criteria
        have corresponding implementation evidence. This is a heuristic
        check -- not a substitute for test execution.

        Args:
            success_criteria: List of criteria strings from the feature/plan
            changed_files: List of files modified during implementation
            result: ContractValidationResult to accumulate violations

        Returns:
            Dict mapping each criterion to whether evidence was found
        """
        criteria_status: dict[str, bool] = {}

        for criterion in success_criteria:
            key_terms = self._extract_key_terms(criterion)
            evidence_found = False

            for path in changed_files:
                resolved = self._resolve_workspace_path(path)
                if not resolved.exists():
                    continue

                try:
                    content = resolved.read_text(encoding="utf-8").lower()
                except (UnicodeDecodeError, OSError):
                    continue

                matches = sum(1 for term in key_terms if term.lower() in content)
                if matches >= max(1, len(key_terms) // 2):
                    evidence_found = True
                    break

            criteria_status[criterion] = evidence_found

            if not evidence_found:
                result.violations.append(
                    ContractViolation(
                        rule="success_criteria_unmet",
                        message=f"No implementation evidence for: {criterion[:100]}",
                    )
                )

        return criteria_status

    @staticmethod
    def _extract_key_terms(text: str) -> list[str]:
        """Extract meaningful terms from a criterion for evidence search.

        Filters out common stop words and returns unique terms of 3+ chars.
        """
        stop_words = {
            "the",
            "and",
            "for",
            "are",
            "but",
            "not",
            "you",
            "all",
            "can",
            "had",
            "her",
            "was",
            "one",
            "our",
            "out",
            "has",
            "have",
            "been",
            "should",
            "must",
            "will",
            "shall",
            "that",
            "this",
            "with",
            "from",
            "they",
            "said",
            "each",
            "which",
            "their",
            "when",
            "into",
        }
        words = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]+", text)
        return [w for w in words if len(w) >= 3 and w.lower() not in stop_words]

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
            content, logical_path = self._load_artifact_text(path)
            if logical_path is None:
                result.warnings.append(f"context_budget_skipped_invalid_artifact_path: {path}")
                continue
            if content is None:
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

    def _normalize_artifact_logical_path(self, path: str) -> str | None:
        """Normalize and validate artifact path as session-scoped logical path."""
        raw = (path or "").strip().replace("\\", "/")
        if not raw:
            return None

        # Allow absolute paths only when they point inside this session artifacts dir.
        candidate = Path(raw)
        if candidate.is_absolute():
            try:
                raw = candidate.resolve().relative_to(self.artifacts_dir.resolve()).as_posix()
            except ValueError:
                return None

        # Strip sessions/<id>/artifacts/ prefix (agents may use full session path)
        _sessions_prefix = re.match(r"^sessions/[^/]+/artifacts/(.+)$", raw)
        if _sessions_prefix:
            raw = _sessions_prefix.group(1)

        if raw.startswith("artifacts/"):
            raw = raw[len("artifacts/") :]
        if raw.startswith("/"):
            raw = raw.lstrip("/")
        if not raw:
            return None

        pure = PurePosixPath(raw)
        if pure.is_absolute():
            return None

        normalized_parts: list[str] = []
        for part in pure.parts:
            if part in ("", "."):
                continue
            if part == "..":
                return None
            normalized_parts.append(part)

        if not normalized_parts:
            return None
        return "/".join(normalized_parts)

    def _materialize_artifact(self, logical_path: str, content: str) -> Path:
        """Materialize DB artifact content under artifacts_dir for file-based consumers."""
        materialized = self.artifacts_dir / logical_path
        materialized.parent.mkdir(parents=True, exist_ok=True)
        if not materialized.exists() or materialized.read_text(encoding="utf-8") != content:
            materialized.write_text(content, encoding="utf-8")
        return materialized

    def _try_auto_register_from_worktree(
        self,
        logical_path: str,
        result: ContractValidationResult,
    ) -> str | None:
        """Try to find and auto-register a missing artifact from the worktree.

        When the DB artifact loader returns None but the file exists on disk
        (in project_root), read it and register it via artifact_saver.

        Args:
            logical_path: Normalized artifact logical path
            result: ContractValidationResult to add warnings to

        Returns:
            File content if found and registered, None otherwise
        """
        if not self._artifact_saver:
            return None

        # Look in project_root (worktree), not artifacts_dir
        worktree_path = self.project_root / logical_path
        if not worktree_path.exists() or not worktree_path.is_file():
            return None

        try:
            content = worktree_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            return None

        # Auto-register into session store
        try:
            self._artifact_saver(logical_path, content)
            result.warnings.append(
                f"auto_registered_worktree_artifact: {logical_path} "
                f"(found in worktree, saved to session store)"
            )
            logger.warning("Auto-registered worktree artifact: %s", logical_path)
            return content
        except Exception:
            logger.debug(
                "Failed to auto-register worktree artifact %s",
                logical_path,
                exc_info=True,
            )
            return None

    def _artifact_exists(self, path: str) -> tuple[bool, str | None]:
        """Check if an artifact exists in session scope."""
        logical_path = self._normalize_artifact_logical_path(path)
        if logical_path is None:
            return False, None

        if self._artifact_loader:
            return self._artifact_loader(logical_path) is not None, logical_path

        return (self.artifacts_dir / logical_path).exists(), logical_path

    def _load_artifact_text(self, path: str) -> tuple[str | None, str | None]:
        """Load artifact text from DB session store (or artifact dir when no loader)."""
        logical_path = self._normalize_artifact_logical_path(path)
        if logical_path is None:
            return None, None

        if self._artifact_loader:
            content = self._artifact_loader(logical_path)
            if content is None:
                return None, logical_path
            # Keep materialization for consumers that require file paths.
            self._materialize_artifact(logical_path, content)
            return content, logical_path

        artifact_path = self.artifacts_dir / logical_path
        if not artifact_path.exists():
            return None, logical_path
        try:
            return artifact_path.read_text(encoding="utf-8"), logical_path
        except (UnicodeDecodeError, OSError):
            return None, logical_path

    def _resolve_workspace_path(self, path: str) -> Path:
        """Resolve workspace file path (project-root scoped)."""
        abs_path = Path(path)
        if abs_path.is_absolute():
            return abs_path
        return self.project_root / path

    @staticmethod
    def _extract_headings(content: str) -> list[str]:
        """Extract markdown headings from content.

        Matches lines starting with one or more '#' followed by whitespace and text.
        """
        headings = []
        for line in content.splitlines():
            match = re.match(r"^#+\s+(.+)$", line)
            if match:
                headings.append(match.group(1))
        return headings

    @staticmethod
    def _normalize_heading(text: str) -> str:
        """Normalize a heading for comparison.

        Strips punctuation, collapses whitespace, lowercases.
        """
        text = re.sub(r"[^\w\s]", "", text)
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text.lower()

    @staticmethod
    def _has_command_blocks(content: str) -> bool:
        """Check if content contains command blocks.

        Detects:
        - Fenced code blocks with bash/shell/sh language identifier
        - Lines starting with '$ ' (dollar-space)
        """
        # Check fenced code blocks
        if re.search(r"```(?:bash|shell|sh)\b", content):
            return True

        # Check dollar-prefixed lines
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
    ) -> list[str] | None:
        """Get list of changed files from git diff.

        Returns None if git is unavailable (records in result).
        """
        if not self.baseline_commit:
            result.git_unavailable_checks.append("must_update_files (no baseline_commit)")
            return None

        try:
            proc = subprocess.run(
                ["git", "diff", f"{self.baseline_commit}..HEAD", "--name-only"],
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
                timeout=10,
            )
            if proc.returncode != 0:
                result.git_unavailable_checks.append(f"git diff failed: {proc.stderr.strip()}")
                return None

            return list({line.strip() for line in proc.stdout.splitlines() if line.strip()})
        except (subprocess.TimeoutExpired, FileNotFoundError):
            result.git_unavailable_checks.append("git command not available")
            return None

    def _git_diff_line_count(
        self,
        result: ContractValidationResult,
    ) -> int | None:
        """Get total diff line count (insertions + deletions).

        Returns None if git is unavailable (records in result).
        """
        if not self.baseline_commit:
            result.git_unavailable_checks.append("max_diff_lines (no baseline_commit)")
            return None

        try:
            proc = subprocess.run(
                ["git", "diff", f"{self.baseline_commit}..HEAD", "--numstat"],
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
                timeout=10,
            )
            if proc.returncode != 0:
                result.git_unavailable_checks.append(
                    f"git diff --numstat failed: {proc.stderr.strip()}"
                )
                return None

            total = 0
            for line in proc.stdout.splitlines():
                parts = line.split("\t")
                if len(parts) >= 2:
                    insertions = parts[0].strip()
                    deletions = parts[1].strip()
                    # Skip binary files (shown as '-')
                    if insertions != "-" and deletions != "-":
                        total += int(insertions) + int(deletions)
            return total
        except (subprocess.TimeoutExpired, FileNotFoundError):
            result.git_unavailable_checks.append("git command not available")
            return None

"""Contract repair workflow — artifact-only re-query to fix contract violations.

When a stage's output contract fails, this workflow re-queries the same
agent with a focused repair prompt containing the violations and existing
artifact content. Writes are constrained to the artifacts directory.
"""

from __future__ import annotations

import contextlib
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

from pixl.models.event import Event, EventType
from pixl.models.session import WorkflowSession
from pixl.models.workflow import WorkflowSnapshot


def _run_coroutine(coro):
    """Run a coroutine from synchronous code, handling nested event loops."""
    from pixl.utils.async_compat import run_coroutine_sync

    return run_coroutine_sync(coro)


@dataclass
class ContractRepairResult:
    """Outcome of a contract repair attempt sequence."""

    success: bool
    attempt: int  # Which repair attempt (0-based)
    violations_before: list[str]  # Violations that triggered repair
    violations_after: list[str]  # Remaining violations (empty if success)
    artifacts_modified: list[str]  # Files changed during repair
    evidence: dict[str, Any] = field(default_factory=dict)


class ContractRepairWorkflow:
    """Run artifact-only repair attempts against contract violations.

    The repair loop:
    1. Build a focused repair prompt with violation details + artifact content
    2. Re-query the same agent via orchestrator
    3. Validate write constraints (only artifacts_dir)
    4. Re-validate the contract
    5. Emit RECOVERY_FAILED per failed attempt, RECOVERY_SUCCEEDED on fix
    """

    def __init__(
        self,
        orchestrator: Any,  # OrchestratorCore
        project_root: Path,
        artifacts_dir: Path,
        session: WorkflowSession,
        snapshot: WorkflowSnapshot,
        artifact_loader: Callable[[str], str | None] | None = None,
    ) -> None:
        self.orchestrator = orchestrator
        self.project_root = project_root
        self.artifacts_dir = artifacts_dir
        self.session = session
        self.snapshot = snapshot
        self.artifact_loader = artifact_loader

    def attempt_repair(
        self,
        node_id: str,
        violations: list[str],
        max_attempts: int,
        emit_event: Callable[[Event], None],
        resolved_stage_config: dict | None = None,
    ) -> ContractRepairResult:
        """Run internal repair loop (up to max_attempts).

        Args:
            node_id: The node whose contract failed.
            violations: List of violation messages.
            max_attempts: Maximum repair attempts.
            emit_event: Callback to persist events.
            resolved_stage_config: Pre-resolved stage config with template
                variables substituted.  When provided, used instead of the
                raw snapshot config (which may contain ``{{var}}`` patterns).

        Returns:
            ContractRepairResult with success/failure details.
        """

        from pixl.execution.contract_validator import ContractValidator
        from pixl.models.workflow_config import StageContract

        # Use resolved config when available; fall back to raw snapshot
        stage_config = resolved_stage_config or self._get_stage_config(node_id)
        contract_data = stage_config.get("contract", {})

        current_violations = list(violations)

        for attempt in range(max_attempts):
            start_time = time.monotonic()

            # 1. Read current artifact content
            existing_artifacts = self._read_artifacts(
                node_id,
                resolved_stage_config=stage_config,
            )

            # 2. Snapshot pre-repair file state for write constraint validation
            pre_repair_project = self._snapshot_directory(self.project_root)

            # 3. Build repair prompt
            repair_prompt = self._build_repair_prompt(
                node_id,
                current_violations,
                existing_artifacts,
                resolved_stage_config=stage_config,
            )

            # 4. Re-query orchestrator
            task_config = self._get_task_config(node_id)
            model = (
                task_config.get("model", "claude-sonnet-4-6")
                if task_config
                else "claude-sonnet-4-6"
            )
            agent_name = task_config.get("agent") if task_config else None

            coro = self.orchestrator.query_with_streaming(
                prompt=repair_prompt,
                model=model,
                max_turns=20,
                feature_id=self.session.feature_id,
                stream_callback=None,
                workflow_tags=None,
                stage_id=node_id,
                agent_name=agent_name,
            )

            try:
                _result_text, _metadata = _run_coroutine(coro)
            except Exception as exc:
                emit_event(
                    Event.create(
                        EventType.RECOVERY_FAILED,
                        self.session.id,
                        node_id=node_id,
                        data={
                            "attempt": attempt,
                            "reason": f"Orchestrator error: {exc}",
                        },
                    )
                )
                continue

            duration = time.monotonic() - start_time

            # 5. Validate write constraints
            write_violations = self._validate_write_constraints(pre_repair_project)
            if write_violations:
                emit_event(
                    Event.create(
                        EventType.RECOVERY_FAILED,
                        self.session.id,
                        node_id=node_id,
                        data={
                            "attempt": attempt,
                            "reason": "Write constraint violation",
                            "write_violations": write_violations,
                        },
                    )
                )
                current_violations = write_violations
                continue

            # 6. Re-validate contract
            if contract_data:
                contract = StageContract.model_validate(contract_data)
                validator = ContractValidator(
                    project_root=self.project_root,
                    artifacts_dir=self.artifacts_dir,
                    baseline_commit=self.session.baseline_commit,
                    artifact_loader=self.artifact_loader,
                )
                result = validator.validate(contract)

                if result.passed:
                    # Determine which artifacts were modified
                    modified = self._detect_modified_artifacts(pre_repair_project)
                    return ContractRepairResult(
                        success=True,
                        attempt=attempt,
                        violations_before=violations,
                        violations_after=[],
                        artifacts_modified=modified,
                        evidence={
                            "duration_seconds": duration,
                            "prompt_length": len(repair_prompt),
                        },
                    )

                # Still failing — update current violations for next attempt
                current_violations = result.violation_messages
                emit_event(
                    Event.create(
                        EventType.RECOVERY_FAILED,
                        self.session.id,
                        node_id=node_id,
                        data={
                            "attempt": attempt,
                            "remaining_violations": current_violations,
                            "duration_seconds": duration,
                        },
                    )
                )
            else:
                # No contract defined (shouldn't happen, but handle gracefully)
                return ContractRepairResult(
                    success=True,
                    attempt=attempt,
                    violations_before=violations,
                    violations_after=[],
                    artifacts_modified=[],
                    evidence={"duration_seconds": duration},
                )

        # All attempts exhausted
        return ContractRepairResult(
            success=False,
            attempt=max_attempts - 1,
            violations_before=violations,
            violations_after=current_violations,
            artifacts_modified=[],
            evidence={"total_attempts": max_attempts},
        )

    def _build_repair_prompt(
        self,
        node_id: str,
        violations: list[str],
        existing_artifacts: dict[str, str],
        resolved_stage_config: dict | None = None,
    ) -> str:
        """Build repair prompt with violations and current artifact content.

        Args:
            node_id: Stage node ID.
            violations: Current violation messages.
            existing_artifacts: path -> content mapping of current artifacts.
            resolved_stage_config: Pre-resolved stage config (avoids {{var}} in prompt).

        Returns:
            Formatted repair prompt string.
        """
        stage_config = resolved_stage_config or self._get_stage_config(node_id)
        original_prompt = stage_config.get("prompt", "")

        parts = [
            "# Contract Repair Task",
            "",
            "The previous execution of this stage produced output that violates "
            "the stage contract. Your task is to fix the artifacts so they pass "
            "all contract checks.",
            "",
            "## Violations to Fix",
            "",
        ]

        for i, v in enumerate(violations, 1):
            parts.append(f"{i}. {v}")

        parts.extend(
            [
                "",
                "## Current Artifact Content",
                "",
            ]
        )

        for path, content in existing_artifacts.items():
            parts.append(f"### `{path}`")
            parts.append("```")
            # Truncate very large artifacts to keep prompt manageable
            if len(content) > 10000:
                parts.append(content[:10000])
                parts.append(f"... (truncated, {len(content)} chars total)")
            else:
                parts.append(content)
            parts.append("```")
            parts.append("")

        parts.extend(
            [
                "## Constraints",
                "",
                f"- Only write files within the artifacts directory: {self.artifacts_dir}",
                "- Do NOT modify files outside the artifacts directory",
                "- Fix all listed violations while preserving correct existing content",
                "",
            ]
        )

        if original_prompt:
            parts.extend(
                [
                    "## Original Stage Context",
                    "",
                    original_prompt[:3000] if len(original_prompt) > 3000 else original_prompt,
                    "",
                ]
            )

        return "\n".join(parts)

    def _validate_write_constraints(
        self,
        pre_repair_project: dict[str, float],
    ) -> list[str]:
        """Check that only files within artifacts_dir were created/modified.

        Scans the entire project root to detect writes anywhere, then flags
        any new or modified file that falls outside the artifacts directory.

        Args:
            pre_repair_project: path -> mtime snapshot of project_root before repair.

        Returns:
            List of violation messages for out-of-scope writes.
        """
        violations: list[str] = []
        artifacts_resolved = self.artifacts_dir.resolve()
        current_files = self._snapshot_directory(self.project_root)

        for path, mtime in current_files.items():
            is_new = path not in pre_repair_project
            is_modified = not is_new and mtime != pre_repair_project[path]

            if not (is_new or is_modified):
                continue

            full_path = Path(path)
            try:
                full_path.resolve().relative_to(artifacts_resolved)
            except ValueError:
                action = "created" if is_new else "modified"
                violations.append(f"File {action} outside artifacts directory: {path}")

        return violations

    def _read_artifacts(
        self,
        node_id: str,
        resolved_stage_config: dict | None = None,
    ) -> dict[str, str]:
        """Read current content of stage output artifacts.

        Uses stage config's contract.must_write to identify target files.

        Args:
            node_id: Stage node ID.
            resolved_stage_config: Pre-resolved stage config (avoids {{var}} in paths).

        Returns:
            path -> content mapping.
        """
        stage_config = resolved_stage_config or self._get_stage_config(node_id)
        contract = stage_config.get("contract", {})
        must_write = contract.get("must_write", [])

        artifacts: dict[str, str] = {}
        for path in must_write:
            logical_path = self._normalize_artifact_logical_path(path)
            if logical_path is None:
                continue

            if self.artifact_loader is not None:
                content = self.artifact_loader(logical_path)
                if content is not None:
                    artifacts[path] = content
                continue

            # Fallback for non-session contexts/tests without artifact loader.
            artifact_path = self.artifacts_dir / logical_path
            if artifact_path.exists():
                try:
                    artifacts[path] = artifact_path.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    artifacts[path] = "<binary or unreadable>"
            else:
                project_path = self.project_root / path
                if project_path.exists():
                    try:
                        artifacts[path] = project_path.read_text(encoding="utf-8")
                    except (UnicodeDecodeError, OSError):
                        artifacts[path] = "<binary or unreadable>"

        return artifacts

    def _normalize_artifact_logical_path(self, path: str) -> str | None:
        """Normalize contract artifact path to session-scoped logical path."""
        raw = (path or "").strip().replace("\\", "/")
        if not raw:
            return None

        candidate = Path(raw)
        if candidate.is_absolute():
            try:
                raw = candidate.resolve().relative_to(self.artifacts_dir.resolve()).as_posix()
            except ValueError:
                return None

        if raw.startswith("artifacts/"):
            raw = raw[len("artifacts/") :]
        if raw.startswith("/"):
            raw = raw.lstrip("/")
        if not raw:
            return None

        pure = PurePosixPath(raw)
        if pure.is_absolute():
            return None

        parts: list[str] = []
        for part in pure.parts:
            if part in ("", "."):
                continue
            if part == "..":
                return None
            parts.append(part)

        if not parts:
            return None
        return "/".join(parts)

    # Directories to skip during snapshot (never contain artifacts)
    _SNAPSHOT_SKIP_DIRS = {
        ".git",
        "__pycache__",
        "node_modules",
        ".venv",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
    }

    @staticmethod
    def _snapshot_directory(directory: Path) -> dict[str, float]:
        """Snapshot a directory tree (path -> mtime).

        Skips noise directories (.git, node_modules, etc.) that never
        contain artifacts and whose mtime changes cause false write
        constraint violations.

        Args:
            directory: Root directory to scan.

        Returns:
            Mapping of absolute file paths to modification times.
        """
        snapshot: dict[str, float] = {}
        if not directory.exists():
            return snapshot

        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if d not in ContractRepairWorkflow._SNAPSHOT_SKIP_DIRS]
            for name in files:
                full = os.path.join(root, name)
                with contextlib.suppress(OSError):
                    snapshot[full] = os.path.getmtime(full)

        return snapshot

    def _detect_modified_artifacts(
        self,
        pre_repair_project: dict[str, float],
    ) -> list[str]:
        """Detect which artifacts were modified during repair.

        Args:
            pre_repair_project: path -> mtime snapshot of project before repair.

        Returns:
            List of modified file paths (relative to artifacts_dir).
        """
        modified: list[str] = []
        artifacts_resolved = self.artifacts_dir.resolve()
        current_files = self._snapshot_directory(self.artifacts_dir)

        for path, mtime in current_files.items():
            if path not in pre_repair_project or mtime != pre_repair_project[path]:
                try:
                    rel = str(Path(path).relative_to(artifacts_resolved))
                    modified.append(rel)
                except ValueError:
                    modified.append(path)

        return modified

    def _get_stage_config(self, stage_id: str) -> dict:
        """Get stage config from snapshot."""
        stages = self.snapshot.workflow_config.get("stages", [])
        for stage in stages:
            if stage.get("id") == stage_id:
                return stage
        return {}

    def _get_task_config(self, node_id: str) -> dict | None:
        """Get task config from the execution graph node."""
        node = self.snapshot.graph.nodes.get(node_id)
        if node and node.task_config:
            return {
                "model": node.task_config.model,
                "agent": node.task_config.agent,
                "max_turns": node.task_config.max_turns,
            }
        return None

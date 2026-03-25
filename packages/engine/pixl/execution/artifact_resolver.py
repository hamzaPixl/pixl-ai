"""Artifact resolution extracted from GraphExecutor.

Handles artifact path resolution, handoff manifest construction,
and required input validation. GraphExecutor delegates to this class
for all artifact-related pre-execution checks.
"""

from __future__ import annotations

import contextlib
import hashlib
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pixl.execution.prompt_builder import resolve_template_string

logger = logging.getLogger(__name__)


class ArtifactResolver:
    """Resolves artifact paths and builds handoff manifests.

    Extracted from GraphExecutor to isolate artifact resolution concerns.
    """

    def __init__(
        self,
        *,
        session_id: str,
        artifacts_dir: Path,
        store: Any,  # WorkflowSessionStore — avoid circular import
        build_contract_variables: Callable[[str], dict[str, str]],
    ) -> None:
        """Initialize the artifact resolver.

        Args:
            session_id: ID of the current session.
            artifacts_dir: Directory for artifact storage.
            store: WorkflowSessionStore for DB artifact lookups.
            build_contract_variables: Callable that builds template variables
                for a given node_id (bound from GraphExecutor).
        """
        self.session_id = session_id
        self.artifacts_dir = artifacts_dir
        self.store = store
        self._build_contract_variables = build_contract_variables

    def resolve_required_artifact_path(self, artifact: str, variables: dict[str, str]) -> str:
        """Resolve and normalize a required artifact path."""
        resolved_name = resolve_template_string(artifact, variables)
        if resolved_name.startswith("artifacts/"):
            resolved_name = resolved_name[len("artifacts/") :]
        if resolved_name.startswith(str(self.artifacts_dir)):
            with_candidate = Path(resolved_name)
            with contextlib.suppress(ValueError):
                resolved_name = str(with_candidate.relative_to(self.artifacts_dir))
        return resolved_name.replace("\\", "/").lstrip("/")

    def load_artifact_row_safe(self, path: str) -> dict[str, Any] | None:
        """Best-effort DB artifact-row loader for manifest diagnostics."""
        try:
            db = self.store._get_db()  # noqa: SLF001 - executor/storage integration
            return db.artifacts.get_by_session_path(self.session_id, path)
        except Exception:
            return None

    def _load_session_artifact_safe(self, path: str) -> str | None:
        """Best-effort session artifact loader for DB-first validation hooks."""
        try:
            return self.store.load_artifact(self.session_id, path)
        except Exception:
            return None

    def build_artifact_handoff_manifest(
        self,
        node_id: str,
        required_artifacts: list[str],
    ) -> list[dict[str, Any]]:
        """Build deterministic handoff metadata for required artifacts."""
        variables = self._build_contract_variables(node_id)
        manifest: list[dict[str, Any]] = []

        for artifact in required_artifacts:
            resolved_path = self.resolve_required_artifact_path(artifact, variables)
            row = self.load_artifact_row_safe(resolved_path)

            entry: dict[str, Any] = {
                "path": resolved_path,
                "exists": False,
                "sha256": None,
                "version": None,
                "producer_stage": None,
            }
            if row:
                entry["exists"] = True
                entry["sha256"] = row.get("content_hash")
                entry["version"] = row.get("version")
                entry["producer_stage"] = row.get("task_id")
            else:
                fallback_content = self._load_session_artifact_safe(resolved_path)
                if fallback_content is not None:
                    entry["exists"] = True
                    entry["sha256"] = hashlib.sha256(fallback_content.encode("utf-8")).hexdigest()
                    entry["version"] = "unknown"
                    entry["producer_stage"] = "unknown"

            manifest.append(entry)

        manifest.sort(key=lambda item: str(item.get("path", "")))
        return manifest

    def check_required_inputs(
        self,
        node_id: str,
        required_artifacts: list[str],
    ) -> list[str]:
        """Check that required input artifacts exist before task execution.

        Resolves template variables (e.g., {{decomposition_file}}) and checks
        only session-scoped artifacts.

        Returns list of missing artifact names (empty = all present).
        """
        manifest = self.build_artifact_handoff_manifest(node_id, required_artifacts)
        return [entry["path"] for entry in manifest if not entry["exists"]]

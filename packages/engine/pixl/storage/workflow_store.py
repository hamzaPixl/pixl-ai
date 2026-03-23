"""Workflow template storage.

Manages workflow templates with version tracking.
Templates are stored in .pixl/workflows/:
  ├── *.yaml              # YAML workflows
  │   ├── tdd.yaml
  │   ├── debug.yaml
  │   └── simple.yaml
  └── snapshots/          # Shared snapshots
      ├── <hash>.json
      └── ...
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pixl.models.workflow import (
    WorkflowSnapshot,
    WorkflowTemplate,
)
from pixl.paths import get_workflows_dir


class WorkflowStore:
    """Manages workflow template persistence."""

    def __init__(self, project_path: Path) -> None:
        """Initialize the store.

        Args:
            project_path: Path to the project root
        """
        self.project_path = project_path
        self.workflows_dir = get_workflows_dir(project_path)
        self.snapshots_dir = self.workflows_dir / "snapshots"

    def _ensure_dirs(self) -> None:
        """Ensure all directories exist."""
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    # YAML Workflow Loading

    def load_workflow(
        self,
        workflow_id: str,
        skip_model_validation: bool = False,
    ) -> WorkflowTemplate:
        """Load a workflow from YAML file.

        Args:
            workflow_id: Workflow ID (e.g., "tdd", "debug")
            skip_model_validation: If True, skip pre-build model validation

        Returns:
            WorkflowTemplate

        Raises:
            WorkflowLoadError: If workflow not found or fails to load
        """
        from pixl.config.workflow_loader import WorkflowLoader

        loader = WorkflowLoader(self.project_path)
        return loader.convert_to_template(
            loader.load_workflow(workflow_id),
            skip_model_validation=skip_model_validation,
        )

    def list_workflows(self) -> list[dict[str, Any]]:
        """List all available YAML workflows.

        Returns:
            List of workflow metadata dictionaries
        """
        from pixl.config.workflow_loader import list_yaml_workflows

        return list_yaml_workflows(self.project_path)

    # Snapshot Management

    def load_snapshot_by_hash(self, snapshot_hash: str) -> WorkflowSnapshot | None:
        """Load a snapshot by its hash.

        Args:
            snapshot_hash: SHA256 hash of snapshot

        Returns:
            WorkflowSnapshot or None if not found
        """
        snapshot_file = self.snapshots_dir / f"{snapshot_hash}.json"
        if not snapshot_file.exists():
            return None

        with open(snapshot_file, encoding="utf-8") as f:
            data = json.load(f)

        return WorkflowSnapshot.model_validate(data)

    def save_snapshot(self, snapshot: WorkflowSnapshot) -> None:
        """Save a snapshot to the snapshots directory.

        Args:
            snapshot: WorkflowSnapshot to save
        """
        self._ensure_dirs()

        snapshot_file = self.snapshots_dir / f"{snapshot.snapshot_hash}.json"
        with open(snapshot_file, "w", encoding="utf-8") as f:
            f.write(snapshot.model_dump_json(indent=2, exclude_none=True))

"""Workflow endpoints: list and get workflow definitions."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from pixl_api.auth.dependencies import CurrentUser
from pixl_api.deps import ProjectRoot
from pixl_api.errors import EntityNotFoundError
from pixl_api.schemas.workflows import WorkflowDetail, WorkflowSummary

router = APIRouter(prefix="/projects/{project_id}/workflows", tags=["workflows"])


@router.get("", response_model=list[WorkflowSummary])
async def list_workflows(project_root: ProjectRoot, user: CurrentUser) -> list[dict[str, Any]]:
    """List available workflows for a project."""
    workflows = await asyncio.to_thread(_load_workflow_list, project_root)
    return [
        {"id": w["id"], "name": w["name"], "description": w.get("description")} for w in workflows
    ]


@router.get("/{workflow_id}", response_model=WorkflowDetail)
async def get_workflow(
    workflow_id: str, project_root: ProjectRoot, user: CurrentUser
) -> dict[str, Any]:
    """Get workflow structure by ID."""
    detail = await asyncio.to_thread(_load_workflow_detail, project_root, workflow_id)
    if detail is None:
        raise EntityNotFoundError("workflow", workflow_id)
    return detail


def _load_workflow_list(project_path: Path) -> list[dict[str, Any]]:
    """Sync helper — instantiate WorkflowLoader and list workflows."""
    from pixl.config.workflow_loader import WorkflowLoader

    loader = WorkflowLoader(project_path)
    return loader.list_workflows()


def _load_workflow_detail(project_path: Path, workflow_id: str) -> dict[str, Any] | None:
    """Sync helper — load a single workflow and return its graph structure."""
    from pixl.config.workflow_loader import WorkflowLoader, WorkflowLoadError

    loader = WorkflowLoader(project_path)
    try:
        config = loader.load_workflow(workflow_id)
    except WorkflowLoadError:
        return None

    graph = loader.convert_to_graph(config, skip_model_validation=True)

    nodes = [
        {"id": n.id, "type": n.type.value, "priority": n.priority} for n in graph.nodes.values()
    ]
    edges_list = [
        {"from": from_id, "to": e.to, "on": e.on.value}
        for from_id, edge_group in graph.edges.items()
        for e in edge_group
    ]

    return {
        "id": config.id,
        "name": config.name,
        "nodes": nodes,
        "edges": edges_list,
        "metadata": {
            "description": config.description,
            "version": config.version,
            "tags": config.tags,
        },
    }

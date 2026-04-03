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
    return workflows


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
    raw = loader.list_workflows()
    results: list[dict[str, Any]] = []
    for w in raw:
        wf_id = w["id"]
        summary: dict[str, Any] = {
            "id": wf_id,
            "name": w.get("name", wf_id),
            "description": w.get("description"),
        }
        # Enrich with config data if loadable
        try:
            config = loader.load_workflow(wf_id)
            summary["version"] = config.version
            summary["tags"] = config.tags
            summary["tier"] = config.tier
            if config.routing:
                summary["routing"] = {
                    "auto_route": config.routing.auto_route,
                    "sub_invocable": config.routing.sub_invocable,
                    "category": config.routing.category,
                    "trigger_keywords": config.routing.trigger_keywords,
                }
        except Exception:
            pass
        results.append(summary)
    return results


def _load_workflow_detail(project_path: Path, workflow_id: str) -> dict[str, Any] | None:
    """Sync helper — load a single workflow and return its full structure."""
    from pixl.config.workflow_loader import WorkflowLoader, WorkflowLoadError

    loader = WorkflowLoader(project_path)
    try:
        config = loader.load_workflow(workflow_id)
    except WorkflowLoadError:
        return None

    graph = loader.convert_to_graph(config, skip_model_validation=True)

    # Build stage lookup for enriching nodes
    stage_map: dict[str, Any] = {}
    for stage in config.stages:
        stage_map[stage.id] = stage

    # Nodes as Record<string, NodeDetail>
    nodes: dict[str, dict[str, Any]] = {}
    for node in graph.nodes.values():
        stage = stage_map.get(node.id)
        node_detail: dict[str, Any] = {
            "id": node.id,
            "type": node.type.value,
        }

        if stage:
            if stage.type == "task":
                node_detail["task_config"] = {
                    "agent": stage.agent,
                    "max_turns": stage.max_turns,
                }
            elif stage.type == "gate":
                node_detail["gate_config"] = {
                    "id": stage.id,
                    "name": stage.name,
                    "description": stage.description or "",
                    "timeout_minutes": stage.timeout_minutes,
                    "timeout_policy": stage.timeout_policy,
                }
            elif stage.type == "hook":
                node_detail["hook_config"] = {
                    "hook": stage.hook or "",
                    **({"hook_params": stage.hook_params} if stage.hook_params else {}),
                }

            # Metadata (prompt, outputs, etc.)
            meta: dict[str, str] = {}
            if stage.name:
                meta["name"] = stage.name
            if stage.prompt:
                meta["prompt"] = stage.prompt[:500]
            if stage.outputs:
                meta["outputs"] = ", ".join(stage.outputs)
            if stage.required_artifacts:
                meta["required_artifacts"] = ", ".join(stage.required_artifacts)
            if stage.description:
                meta["description"] = stage.description
            if meta:
                node_detail["metadata"] = meta

        nodes[node.id] = node_detail

    # Edges as Record<string, EdgeDetail[]>
    edges: dict[str, list[dict[str, Any]]] = {}
    for from_id, edge_group in graph.edges.items():
        edges[from_id] = [
            {"to": e.to, "on": e.on.value, "condition": e.condition} for e in edge_group
        ]

    # Loops
    loops = [
        {
            "id": lc.id,
            "from_node": lc.from_node,
            "to_node": lc.to_node,
            "max_iterations": lc.max_iterations,
            "edge_trigger": lc.edge_trigger.value,
        }
        for lc in graph.loop_constraints
    ]

    # Stages raw (for Console to inspect prompts, contracts, etc.)
    stages_raw = []
    for stage in config.stages:
        s: dict[str, Any] = {
            "id": stage.id,
            "name": stage.name,
            "type": stage.type,
            "agent": stage.agent,
            "max_turns": stage.max_turns,
        }
        if stage.prompt:
            s["prompt"] = stage.prompt
        if stage.outputs:
            s["outputs"] = stage.outputs
        if stage.required_artifacts:
            s["required_artifacts"] = stage.required_artifacts
        if stage.description:
            s["description"] = stage.description
        if stage.hook:
            s["hook"] = stage.hook
        if stage.hook_params:
            s["hook_params"] = stage.hook_params
        if stage.timeout_minutes:
            s["timeout_minutes"] = stage.timeout_minutes
        if stage.contract:
            s["contract"] = stage.contract.model_dump(exclude_defaults=True)
        stages_raw.append(s)

    routing = None
    if config.routing:
        routing = {
            "auto_route": config.routing.auto_route,
            "sub_invocable": config.routing.sub_invocable,
            "category": config.routing.category,
            "trigger_keywords": config.routing.trigger_keywords,
        }

    return {
        "id": config.id,
        "name": config.name,
        "description": config.description,
        "tags": config.tags,
        "version": config.version,
        "tier": config.tier,
        "routing": routing,
        "nodes": nodes,
        "edges": edges,
        "loops": loops,
        "stages": stages_raw,
        "variables": config.variables or {},
    }

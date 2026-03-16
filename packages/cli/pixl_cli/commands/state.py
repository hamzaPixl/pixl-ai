"""pixl state — show, graph, deps."""

from __future__ import annotations

from typing import Any

import click

from pixl_cli._output import emit_detail, emit_error, emit_json
from pixl_cli.main import get_ctx


@click.group()
@click.pass_context
def state(ctx: click.Context) -> None:
    """Inspect entity state and transitions."""


@state.command("show")
@click.argument("entity_id")
@click.pass_context
def state_show(ctx: click.Context, entity_id: str) -> None:
    """Show current state and available transitions for an entity."""
    cli = get_ctx(ctx)
    db = cli.db

    from pixl.state import TransitionEngine

    engine = TransitionEngine.default(db.backlog)

    # Resolve entity type from prefix
    prefix = entity_id.split("-")[0]
    entity_type = {"feat": "feature", "epic": "epic", "roadmap": "roadmap"}.get(prefix)
    if entity_type is None:
        emit_error(f"Unknown entity type for ID: {entity_id}", is_json=cli.is_json)
        raise SystemExit(1)

    # Fetch entity
    fetch = {
        "feature": db.backlog.get_feature,
        "epic": db.backlog.get_epic,
        "roadmap": db.backlog.get_roadmap,
    }
    entity = fetch[entity_type](entity_id)
    if entity is None:
        emit_error(f"Entity not found: {entity_id}", is_json=cli.is_json)
        raise SystemExit(1)

    available = engine.get_available_transitions(entity_id)

    result: dict[str, Any] = {
        "entity_id": entity_id,
        "entity_type": entity_type,
        "status": entity.get("status"),
        "title": entity.get("title"),
        "available_transitions": available,
    }

    if cli.is_json:
        emit_json(result)
    else:
        click.echo(f"Entity: {entity_id} ({entity_type})")
        click.echo(f"  Status: {entity.get('status')}")
        click.echo(f"  Title:  {entity.get('title')}")
        click.echo(f"  Available transitions: {', '.join(available) or 'none'}")


@state.command("graph")
@click.argument("epic_id")
@click.pass_context
def state_graph(ctx: click.Context, epic_id: str) -> None:
    """Show the dependency graph for an epic's features."""
    cli = get_ctx(ctx)
    graph = cli.db.backlog.get_dependency_graph(epic_id=epic_id)

    if cli.is_json:
        emit_json(graph)
    else:
        if not graph:
            click.echo("No dependencies found.")
            return
        click.echo(f"Dependency graph for {epic_id}:")
        for feature_id, deps in sorted(graph.items()):
            dep_str = ", ".join(deps) if deps else "(no deps)"
            click.echo(f"  {feature_id} -> {dep_str}")


@state.command("deps")
@click.argument("feature_id")
@click.pass_context
def state_deps(ctx: click.Context, feature_id: str) -> None:
    """Check if a feature's dependencies are met."""
    cli = get_ctx(ctx)
    met, unmet = cli.db.backlog.check_dependencies_met(feature_id)

    result = {
        "feature_id": feature_id,
        "dependencies_met": met,
        "unmet_dependencies": unmet,
    }

    if cli.is_json:
        emit_json(result)
    else:
        status = "met" if met else "NOT met"
        click.echo(f"Dependencies for {feature_id}: {status}")
        if unmet:
            click.echo(f"  Unmet: {', '.join(unmet)}")

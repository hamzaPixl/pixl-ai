"""pixl session — list, get, create."""

from __future__ import annotations

import click

from pixl_cli._output import emit_detail, emit_error, emit_json, emit_table
from pixl_cli.main import get_ctx


@click.group()
@click.pass_context
def session(ctx: click.Context) -> None:
    """Manage workflow sessions."""


@session.command("list")
@click.option("--feature", default=None, help="Filter by feature ID.")
@click.option("--status", default=None, help="Filter by status.")
@click.option("--limit", default=20, type=int, help="Max results.")
@click.pass_context
def session_list(
    ctx: click.Context,
    feature: str | None,
    status: str | None,
    limit: int,
) -> None:
    """List workflow sessions."""
    cli = get_ctx(ctx)
    sessions = cli.db.sessions.list_sessions(
        feature_id=feature,
        status=status,
        limit=limit,
    )

    emit_table(
        sessions,
        columns=[
            ("id", "ID"),
            ("feature_id", "Feature"),
            ("status", "Status"),
            ("created_at", "Created"),
            ("last_updated_at", "Updated"),
        ],
        title="Sessions",
        is_json=cli.is_json,
    )


@session.command("get")
@click.argument("session_id")
@click.pass_context
def session_get(ctx: click.Context, session_id: str) -> None:
    """Get session details."""
    cli = get_ctx(ctx)
    result = cli.db.sessions.get_session(session_id)

    if result is None:
        emit_error(f"Session not found: {session_id}", is_json=cli.is_json)
        raise SystemExit(1)

    emit_detail(result, is_json=cli.is_json)


@session.command("create")
@click.option("--feature-id", required=True, help="Feature ID to execute.")
@click.option("--workflow-id", default=None, help="Workflow ID (uses default if not specified).")
@click.pass_context
def session_create(
    ctx: click.Context,
    feature_id: str,
    workflow_id: str | None,
) -> None:
    """Create a new workflow session."""
    cli = get_ctx(ctx)

    # Load workflow and create snapshot
    from pixl.config.workflow_loader import WorkflowLoader

    loader = WorkflowLoader(cli.project_path)

    if workflow_id:
        config = loader.load_workflow(workflow_id)
    else:
        # Use default workflow
        workflows = loader.list_workflows()
        if not workflows:
            emit_error("No workflows available.", is_json=cli.is_json)
            raise SystemExit(1)
        config = loader.load_workflow(workflows[0]["id"])

    template = loader.convert_to_template(config)
    snapshot = template.snapshot

    result = cli.db.sessions.create_session(
        feature_id=feature_id,
        snapshot_hash=snapshot.snapshot_hash,
    )

    # Save snapshot if not already saved
    if not cli.db.sessions.snapshot_exists(snapshot.snapshot_hash):
        cli.db.sessions.save_snapshot(
            snapshot.snapshot_hash,
            snapshot.model_dump_json(),
        )

    if cli.is_json:
        emit_json(result)
    else:
        click.echo(f"Created session: {result.get('id')}")
        click.echo(f"  Feature: {feature_id}")
        click.echo(f"  Workflow: {config.id}")

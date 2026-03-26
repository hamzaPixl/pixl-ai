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


@session.command("cancel")
@click.argument("session_id")
@click.pass_context
def session_cancel(ctx: click.Context, session_id: str) -> None:
    """Cancel a workflow session."""
    cli = get_ctx(ctx)
    result = cli.db.sessions.get_session(session_id)

    if result is None:
        emit_error(f"Session not found: {session_id}", is_json=cli.is_json)
        raise SystemExit(1)

    updated = cli.db.sessions.update_session(session_id, status="cancelled")

    if not updated:
        emit_error(f"Failed to cancel session: {session_id}", is_json=cli.is_json)
        raise SystemExit(1)

    if cli.is_json:
        emit_json({"id": session_id, "status": "cancelled"})
    else:
        emit_detail({"id": session_id, "status": "cancelled"}, is_json=False)


@session.command("cleanup")
@click.option("--stale-minutes", default=5, type=int, help="Cancel sessions idle longer than this (default: 5).")
@click.pass_context
def session_cleanup(ctx: click.Context, stale_minutes: int) -> None:
    """Cancel sessions stuck in 'running' state.

    Auto-cancels sessions that haven't been updated in --stale-minutes.
    """
    from datetime import datetime, timedelta, timezone

    cli = get_ctx(ctx)
    sessions = cli.db.sessions.list_sessions(status="running", limit=100)
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=stale_minutes)
    cancelled = []

    for s in sessions:
        updated = s.get("last_updated_at", "")
        if not updated:
            continue
        # Parse ISO timestamp (may or may not have timezone)
        try:
            ts = datetime.fromisoformat(updated.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        except (ValueError, AttributeError):
            continue
        if ts < cutoff:
            cli.db.sessions.update_session(s["id"], status="cancelled")
            cancelled.append(s["id"])

    if cli.is_json:
        emit_json({"cancelled": cancelled, "count": len(cancelled)})
    else:
        if cancelled:
            click.echo(f"Cancelled {len(cancelled)} stale session(s):")
            for sid in cancelled:
                click.echo(f"  {sid}")
        else:
            click.echo("No stale sessions found.")


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
    snapshot = template.snapshot  # type: ignore[attr-defined]

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

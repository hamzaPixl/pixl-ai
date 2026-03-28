"""pixl session — list, get, create."""

from __future__ import annotations

from datetime import UTC

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
@click.option(
    "--stale-minutes",
    default=5,
    type=int,
    help="Cancel sessions idle longer than this (default: 5).",
)
@click.pass_context
def session_cleanup(ctx: click.Context, stale_minutes: int) -> None:
    """Cancel sessions stuck in 'running' state.

    Auto-cancels sessions that haven't been updated in --stale-minutes.
    """
    from datetime import datetime, timedelta

    cli = get_ctx(ctx)
    sessions = cli.db.sessions.list_sessions(status="running", limit=100)
    cutoff = datetime.now(UTC) - timedelta(minutes=stale_minutes)
    cancelled = []

    for s in sessions:
        updated = s.get("last_updated_at", "")
        if not updated:
            continue
        # Parse ISO timestamp (may or may not have timezone)
        try:
            ts = datetime.fromisoformat(updated.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
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


@session.command("resume")
@click.argument("session_id")
@click.option("--yes", is_flag=True, default=False, help="Auto-approve all gates.")
@click.pass_context
def session_resume(ctx: click.Context, session_id: str, yes: bool) -> None:
    """Resume a stalled or paused session from its saved cursor.

    Restarts execution from the last checkpoint. The executor picks up
    where it left off — completed stages are skipped.
    """
    cli = get_ctx(ctx)
    result = cli.db.sessions.get_session(session_id)

    if result is None:
        emit_error(f"Session not found: {session_id}", is_json=cli.is_json)
        raise SystemExit(1)

    status = result.get("status", "")
    if status in ("completed",):
        emit_error(f"Cannot resume session in status: {status}", is_json=cli.is_json)
        raise SystemExit(1)

    # Reset status so the runner can pick it up
    cli.db.sessions.update_session(session_id, status="running")

    if not cli.is_json:
        click.echo(f"Resuming session {session_id} (was: {status})...")

    _resume_session(cli, session_id, skip_approval=yes)


@session.command("retry")
@click.argument("session_id")
@click.option("--yes", is_flag=True, default=False, help="Auto-approve all gates.")
@click.pass_context
def session_retry(ctx: click.Context, session_id: str, yes: bool) -> None:
    """Retry a failed or cancelled session.

    Resets failed/cancelled nodes to pending and re-executes the DAG
    from the first incomplete stage.
    """
    cli = get_ctx(ctx)
    result = cli.db.sessions.get_session(session_id)

    if result is None:
        emit_error(f"Session not found: {session_id}", is_json=cli.is_json)
        raise SystemExit(1)

    status = result.get("status", "")
    if status == "completed":
        emit_error("Session already completed", is_json=cli.is_json)
        raise SystemExit(1)

    # Reset status so the runner can pick it up
    cli.db.sessions.update_session(session_id, status="running")

    if not cli.is_json:
        click.echo(f"Retrying session {session_id} (was: {status})...")

    _resume_session(cli, session_id, skip_approval=yes, workflow_id="retry")


def _resume_session(
    cli, session_id: str, *, skip_approval: bool = False, workflow_id: str = "resumed"
) -> None:
    """Shared logic for resume/retry — loads session and re-executes the DAG."""
    from pixl.execution import GraphExecutor
    from pixl.execution.workflow_helpers import get_waiting_gate_node, has_waiting_gates
    from pixl.orchestration.core import OrchestratorCore
    from pixl.paths import get_sessions_dir
    from pixl.storage import SessionManager, WorkflowSessionStore

    try:
        session_store = WorkflowSessionStore(cli.project_path)
        session = session_store.load_session(session_id)

        if session is None:
            emit_error(f"Cannot load session state: {session_id}", is_json=cli.is_json)
            raise SystemExit(1)

        snapshot = session_store.load_snapshot(session.snapshot_hash)
        if snapshot is None:
            emit_error(
                f"Cannot load workflow snapshot for session: {session_id}", is_json=cli.is_json
            )
            raise SystemExit(1)

        # For retry: reset failed/cancelled nodes to pending
        if workflow_id == "retry":
            for node_id, instance in session.node_instances.items():
                node_status = instance.get("status", "")
                if node_status in ("task_failed", "task_cancelled"):
                    instance["status"] = "task_pending"
                    instance.pop("error", None)
                    instance.pop("ended_at", None)

        session_dir = get_sessions_dir(cli.project_path) / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        orchestrator = OrchestratorCore(cli.project_path)
        session_manager = SessionManager(cli.project_path)

        from pixl_cli.commands.workflow import _ndjson_event_callback

        event_callback = _ndjson_event_callback if cli.is_json else None

        executor = GraphExecutor(
            session,
            snapshot,
            session_dir,
            project_root=cli.project_path,
            orchestrator=orchestrator,
            event_callback=event_callback,
            session_manager=session_manager,
            db=cli.db,
        )

        step_count = 0
        max_steps = 100

        while step_count < max_steps:
            session = executor.session
            if has_waiting_gates(session):
                gate_node_id = get_waiting_gate_node(session)
                if not gate_node_id:
                    break
                if skip_approval:
                    if not cli.is_json:
                        click.echo(f"  Auto-approving gate: {gate_node_id}")
                    session = session_manager.approve_gate(
                        session.id,
                        gate_node_id,
                        approver="auto",
                        snapshot=snapshot,
                    )
                else:
                    if not cli.is_json:
                        click.echo(f"  Paused at gate: {gate_node_id} (use --yes to auto-approve)")
                    break

            result = executor.step()
            if not result["executed"]:
                break
            step_count += 1
            if not cli.is_json:
                node_id = result.get("node_id", "?")
                click.echo(f"  Step {step_count}: {node_id}")

        status_val = session.status
        final_status = status_val.value if hasattr(status_val, "value") else str(status_val)

        if cli.is_json:
            emit_json({"session_id": session_id, "status": final_status, "steps": step_count})
        else:
            click.echo(f"  Session {final_status} ({step_count} steps).")

    except ImportError as exc:
        emit_error(f"Execution requires additional dependencies: {exc}", is_json=cli.is_json)
        raise SystemExit(1) from None
    except Exception as exc:
        emit_error(f"Session execution failed: {exc}", is_json=cli.is_json)
        raise SystemExit(1) from None


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

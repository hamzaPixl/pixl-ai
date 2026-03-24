"""pixl sandbox — manage sandbox projects."""

from __future__ import annotations

import json
import sys
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import click

from pixl_cli._output import emit_detail, emit_error, emit_json, emit_table
from pixl_cli.main import get_ctx

# -- Streaming helpers --------------------------------------------------------


def _print_stream_event(event: dict[str, Any]) -> None:
    """Print a single SSE event to the terminal.

    Recognizes common event shapes emitted by the sandbox API:
    - ``{"type": "log", "message": "..."}``  -> echo the message
    - ``{"type": "stdout", "data": "..."}``  -> echo to stdout
    - ``{"type": "stderr", "data": "..."}``  -> echo to stderr
    - ``{"type": "output", "data": "..."}``  -> echo to stdout
    - ``{"type": "error", ...}``             -> echo to stderr
    - ``{"type": "done", ...}``              -> summary line
    - anything else                          -> compact JSON dump
    """
    event_type = event.get("type", "")

    if event_type == "log":
        click.echo(event.get("message", ""))
    elif event_type in ("stdout", "output"):
        click.echo(event.get("data", ""))
    elif event_type == "stderr":
        click.echo(event.get("data", ""), err=True)
    elif event_type == "error":
        click.echo(event.get("message", event.get("error", "")), err=True)
    elif event_type == "done":
        success = event.get("success")
        if success is True:
            click.echo("Done.")
        elif success is False:
            click.echo("Failed.", err=True)
    else:
        # Unknown shape — dump as compact JSON so nothing is lost
        click.echo(json.dumps(event, default=str))


def _consume_stream(events: Iterator[dict]) -> list[dict]:
    """Consume an SSE event iterator, printing each event and collecting them."""
    collected: list[dict] = []
    for event in events:
        _print_stream_event(event)
        collected.append(event)
    return collected


@click.group()
@click.pass_context
def sandbox(ctx: click.Context) -> None:
    """Manage sandbox projects."""


def _get_client():
    """Get SandboxClient, raising ClickException on config errors."""
    from pixl_cli.sandbox_client import get_sandbox_client

    try:
        return get_sandbox_client()
    except ValueError as exc:
        raise click.ClickException(str(exc)) from None


def _log_operation(
    cli,
    project_id: str,
    operation: str,
    *,
    status: str,
    duration_ms: int | None = None,
    error: str | None = None,
) -> None:
    """Log operation to local pixl.db (best-effort)."""
    try:
        cli.db.sandboxes.log_operation(
            project_id,
            operation,
            status=status,
            duration_ms=duration_ms,
            error=error,
        )
    except Exception:
        pass  # Best-effort — don't break the command


@sandbox.command("create")
@click.argument("project_id")
@click.option("--repo-url", default=None, help="Git repo to clone into sandbox.")
@click.option("--branch", default="main", help="Git branch (default: main).")
@click.option("--env", "env_pairs", multiple=True, help="Extra env vars (KEY=VALUE).")
@click.option(
    "--fork-from",
    default=None,
    help="Fork session from another sandbox (format: SANDBOX_ID:SESSION_ID).",
)
@click.pass_context
def sandbox_create(
    ctx: click.Context,
    project_id: str,
    repo_url: str | None,
    branch: str,
    env_pairs: tuple[str, ...],
    fork_from: str | None,
) -> None:
    """Create a sandbox project.

    Use --fork-from to bootstrap from an existing sandbox session:
      pixl sandbox create new-proj --fork-from old-proj:sess-abc123
    """
    cli = get_ctx(ctx)
    client = _get_client()

    # Parse env pairs
    env_vars: dict[str, str] = {}
    for pair in env_pairs:
        if "=" not in pair:
            emit_error(f"Invalid env var format: {pair} (expected KEY=VALUE)", is_json=cli.is_json)
            raise SystemExit(1)
        key, value = pair.split("=", 1)
        env_vars[key] = value

    # Validate --fork-from format
    source_sandbox_id: str | None = None
    source_session_id: str | None = None
    if fork_from:
        if ":" not in fork_from:
            emit_error(
                f"Invalid --fork-from format: {fork_from} (expected SANDBOX_ID:SESSION_ID)",
                is_json=cli.is_json,
            )
            raise SystemExit(1)
        source_sandbox_id, source_session_id = fork_from.split(":", 1)

    start = time.monotonic()
    try:
        result = client.create(
            project_id, repo_url=repo_url, branch=branch, env_vars=env_vars or None
        )
    except Exception as exc:
        duration_ms = int((time.monotonic() - start) * 1000)
        emit_error(f"Failed to create sandbox: {exc}", is_json=cli.is_json)
        _log_operation(
            cli, project_id, "create", status="failed", duration_ms=duration_ms, error=str(exc)
        )
        raise SystemExit(1) from None

    # Fork session from source sandbox if requested (GAP-09)
    if source_sandbox_id and source_session_id:
        if not cli.is_json:
            click.echo(f"  Forking session {source_session_id} from {source_sandbox_id}...")
        try:
            bundle = client.export_session(source_sandbox_id, source_session_id)
            client.import_session(project_id, bundle)
            if not cli.is_json:
                click.echo("  Session imported successfully.")
        except Exception as exc:
            emit_error(
                f"Session fork failed (sandbox created but session not imported): {exc}",
                is_json=cli.is_json,
            )

    duration_ms = int((time.monotonic() - start) * 1000)

    # Track in local DB
    sandbox_url = client._client.base_url
    try:
        cli.db.sandboxes.create_project(  # type: ignore[attr-defined]
            project_id,
            str(sandbox_url),
            repo_url=repo_url,
            branch=branch,
            env_keys=list(env_vars.keys()) if env_vars else None,
        )
        cli.db.sandboxes.update_project(  # type: ignore[attr-defined]
            project_id,
            status=result.get("status", "ready"),
            pixl_version=result.get("versions", {}).get("pixl"),
            claude_version=result.get("versions", {}).get("claude"),
        )
    except Exception:
        pass  # Best-effort

    _log_operation(cli, project_id, "create", status="completed", duration_ms=duration_ms)

    if cli.is_json:
        if source_sandbox_id:
            result["forked_from"] = {
                "sandbox_id": source_sandbox_id,
                "session_id": source_session_id,
            }
        emit_json(result)
    else:
        emit_detail(result, is_json=False)


@sandbox.command("list")
@click.option("--status", default=None, help="Filter by status.")
@click.pass_context
def sandbox_list(ctx: click.Context, status: str | None) -> None:
    """List tracked sandbox projects."""
    cli = get_ctx(ctx)
    try:
        projects = cli.db.sandboxes.list_projects(status=status)  # type: ignore[attr-defined]
    except Exception as exc:
        emit_error(f"Failed to list projects: {exc}", is_json=cli.is_json)
        raise SystemExit(1) from None

    emit_table(
        projects,
        [
            ("id", "Project"),
            ("status", "Status"),
            ("branch", "Branch"),
            ("repo_url", "Repo"),
            ("created_at", "Created"),
        ],
        title="Sandbox Projects",
        is_json=cli.is_json,
    )


@sandbox.command("status")
@click.argument("project_id")
@click.pass_context
def sandbox_status(ctx: click.Context, project_id: str) -> None:
    """Get sandbox status."""
    cli = get_ctx(ctx)
    client = _get_client()

    try:
        result = client.status(project_id)
    except Exception as exc:
        emit_error(f"Failed to get status: {exc}", is_json=cli.is_json)
        raise SystemExit(1) from None

    # Update local record
    try:
        cli.db.sandboxes.update_project(  # type: ignore[attr-defined]
            project_id,
            status=result.get("status", "running"),
            pixl_version=result.get("versions", {}).get("pixl"),
            claude_version=result.get("versions", {}).get("claude"),
        )
    except Exception:
        pass

    _log_operation(cli, project_id, "status", status="completed")
    emit_detail(result, is_json=cli.is_json)


@sandbox.command("workflow")
@click.argument("project_id")
@click.option("--prompt", required=True, help="PRD prompt for the workflow.")
@click.option("--workflow-id", default=None, help="Workflow template ID.")
@click.option("--yes", "auto_approve", is_flag=True, help="Auto-approve gates.")
@click.option("--no-stream", is_flag=True, help="Disable live streaming.")
@click.pass_context
def sandbox_workflow(
    ctx: click.Context,
    project_id: str,
    prompt: str,
    workflow_id: str | None,
    auto_approve: bool,
    no_stream: bool,
) -> None:
    """Run a workflow in the sandbox."""
    cli = get_ctx(ctx)
    client = _get_client()
    use_stream = not no_stream and not cli.is_json

    # Update status to running
    try:
        cli.db.sandboxes.update_project(project_id, status="running")  # type: ignore[attr-defined]
    except Exception:
        pass

    start = time.monotonic()

    # -- Streaming path (default for interactive terminals) --------------------
    if use_stream:
        collected = _consume_stream(
            client.workflow_stream(project_id, prompt, workflow=workflow_id, yes=auto_approve)
        )
        if collected:
            # Stream succeeded — derive status from collected events
            duration_ms = int((time.monotonic() - start) * 1000)
            last = collected[-1] if collected else {}
            op_status = "completed" if last.get("success", True) else "failed"
            _log_operation(cli, project_id, "workflow", status=op_status, duration_ms=duration_ms)
            try:
                cli.db.sandboxes.update_project(project_id, status="ready")  # type: ignore[attr-defined]
            except Exception:
                pass
            return
        # Stream yielded nothing — fall through to synchronous path

    # -- Synchronous path (--no-stream, --json, or streaming fallback) --------
    try:
        result = client.workflow(
            project_id, prompt, workflow_id=workflow_id, auto_approve=auto_approve
        )
    except Exception as exc:
        duration_ms = int((time.monotonic() - start) * 1000)
        emit_error(f"Workflow failed: {exc}", is_json=cli.is_json)
        _log_operation(
            cli, project_id, "workflow", status="failed", duration_ms=duration_ms, error=str(exc)
        )
        raise SystemExit(1) from None
    duration_ms = int((time.monotonic() - start) * 1000)

    op_status = "completed" if result.get("success") else "failed"
    _log_operation(cli, project_id, "workflow", status=op_status, duration_ms=duration_ms)

    # Update status back to ready
    try:
        cli.db.sandboxes.update_project(project_id, status="ready")  # type: ignore[attr-defined]
    except Exception:
        pass

    if cli.is_json:
        emit_json(result)
    else:
        if result.get("success"):
            click.echo("Workflow completed successfully.")
        else:
            click.echo("Workflow failed.")
        if result.get("stdout"):
            click.echo(result["stdout"])
        if result.get("stderr"):
            click.echo(result["stderr"], err=True)


@sandbox.command("cancel")
@click.argument("project_id")
@click.pass_context
def sandbox_cancel(ctx: click.Context, project_id: str) -> None:
    """Cancel the running workflow in a sandbox."""
    cli = get_ctx(ctx)
    client = _get_client()

    try:
        result = client.cancel_workflow(project_id)
    except Exception as exc:
        emit_error(f"Failed to cancel workflow: {exc}", is_json=cli.is_json)
        raise SystemExit(1) from None

    _log_operation(
        cli,
        project_id,
        "workflow_cancel",
        status="completed" if result.get("success") else "failed",
    )

    if cli.is_json:
        emit_json(result)
    else:
        click.echo(result.get("message", "Cancel request sent."))


@sandbox.command("events")
@click.argument("project_id")
@click.option("--limit", default=50, help="Max events to return.")
@click.pass_context
def sandbox_events(ctx: click.Context, project_id: str, limit: int) -> None:
    """Get workflow events from sandbox."""
    cli = get_ctx(ctx)
    client = _get_client()

    try:
        result = client.events(project_id, limit=limit)
    except Exception as exc:
        emit_error(f"Failed to get events: {exc}", is_json=cli.is_json)
        raise SystemExit(1) from None

    _log_operation(cli, project_id, "events", status="completed")

    events = result.get("events", result.get("raw", []))
    if cli.is_json:
        emit_json(events)
    elif isinstance(events, list):
        emit_table(
            events,
            [
                ("event_type", "Type"),
                ("node_id", "Node"),
                ("created_at", "Time"),
            ],
            title="Sandbox Events",
            is_json=False,
        )
    else:
        click.echo(events)


@sandbox.command("sessions")
@click.argument("project_id")
@click.pass_context
def sandbox_sessions(ctx: click.Context, project_id: str) -> None:
    """Get workflow sessions from sandbox."""
    cli = get_ctx(ctx)
    client = _get_client()

    try:
        result = client.sessions(project_id)
    except Exception as exc:
        emit_error(f"Failed to get sessions: {exc}", is_json=cli.is_json)
        raise SystemExit(1) from None

    _log_operation(cli, project_id, "sessions", status="completed")

    sessions = result.get("sessions", result.get("raw", []))
    if cli.is_json:
        emit_json(sessions)
    elif isinstance(sessions, list):
        emit_table(
            sessions,
            [
                ("id", "Session"),
                ("status", "Status"),
                ("created_at", "Created"),
            ],
            title="Sandbox Sessions",
            is_json=False,
        )
    else:
        click.echo(sessions)


@sandbox.command("export-session")
@click.argument("project_id")
@click.argument("session_id")
@click.option("--output", "-o", default=None, help="Output file (default: stdout).")
@click.pass_context
def sandbox_export_session(
    ctx: click.Context,
    project_id: str,
    session_id: str,
    output: str | None,
) -> None:
    """Export a session from sandbox as portable JSON."""
    cli = get_ctx(ctx)
    client = _get_client()

    start = time.monotonic()
    try:
        bundle = client.export_session(project_id, session_id)
    except Exception as exc:
        duration_ms = int((time.monotonic() - start) * 1000)
        emit_error(f"Failed to export session: {exc}", is_json=cli.is_json)
        _log_operation(
            cli,
            project_id,
            "session_export",
            status="failed",
            duration_ms=duration_ms,
            error=str(exc),
        )
        raise SystemExit(1) from None
    duration_ms = int((time.monotonic() - start) * 1000)

    _log_operation(cli, project_id, "session_export", status="completed", duration_ms=duration_ms)

    if output:
        from pathlib import Path

        Path(output).write_text(json.dumps(bundle, indent=2, default=str))
        if not cli.is_json:
            click.echo(f"Session exported to {output}")
    else:
        emit_json(bundle)


@sandbox.command("import-session")
@click.argument("project_id")
@click.argument("bundle_file", type=click.Path(exists=True))
@click.pass_context
def sandbox_import_session(
    ctx: click.Context,
    project_id: str,
    bundle_file: str,
) -> None:
    """Import a session bundle into sandbox."""
    cli = get_ctx(ctx)
    client = _get_client()

    from pathlib import Path

    try:
        bundle = json.loads(Path(bundle_file).read_text())
    except (json.JSONDecodeError, OSError) as exc:
        emit_error(f"Failed to read bundle file: {exc}", is_json=cli.is_json)
        raise SystemExit(1) from None

    if "session" not in bundle:
        emit_error("Invalid bundle: missing 'session' key", is_json=cli.is_json)
        raise SystemExit(1)

    start = time.monotonic()
    try:
        result = client.import_session(project_id, bundle)
    except Exception as exc:
        duration_ms = int((time.monotonic() - start) * 1000)
        emit_error(f"Failed to import session: {exc}", is_json=cli.is_json)
        _log_operation(
            cli,
            project_id,
            "session_import",
            status="failed",
            duration_ms=duration_ms,
            error=str(exc),
        )
        raise SystemExit(1) from None
    duration_ms = int((time.monotonic() - start) * 1000)

    op_status = "completed" if result.get("success") else "failed"
    _log_operation(cli, project_id, "session_import", status=op_status, duration_ms=duration_ms)

    if cli.is_json:
        emit_json(result)
    else:
        if result.get("success"):
            click.echo(
                f"Session '{result.get('imported_session_id', 'unknown')}' "
                f"imported into sandbox '{project_id}'."
            )
        else:
            click.echo(f"Import failed: {result.get('error', 'unknown error')}", err=True)


@sandbox.command("git")
@click.argument("project_id")
@click.argument("action", default="status", type=click.Choice(["status", "log", "push"]))
@click.pass_context
def sandbox_git(ctx: click.Context, project_id: str, action: str) -> None:
    """Git operations on sandbox."""
    cli = get_ctx(ctx)
    client = _get_client()

    try:
        if action == "push":
            result = client.git_push(project_id)
            _log_operation(
                cli,
                project_id,
                "git_push",
                status="completed" if result.get("success") else "failed",
            )
        else:
            result = client.git(project_id)
            _log_operation(cli, project_id, "git_status", status="completed")
    except Exception as exc:
        emit_error(f"Git operation failed: {exc}", is_json=cli.is_json)
        raise SystemExit(1) from None

    if cli.is_json:
        emit_json(result)
    elif action == "log":
        for line in result.get("log", []):
            click.echo(line)
    elif action == "push":
        if result.get("success"):
            click.echo("Pushed successfully.")
        else:
            click.echo(f"Push failed: {result.get('stderr', '')}")
    else:
        emit_detail(result, is_json=False)


@sandbox.command("exec")
@click.argument("project_id")
@click.argument("command")
@click.option("--no-stream", is_flag=True, help="Disable live streaming.")
@click.pass_context
def sandbox_exec(ctx: click.Context, project_id: str, command: str, no_stream: bool) -> None:
    """Execute a command in the sandbox."""
    cli = get_ctx(ctx)
    client = _get_client()
    use_stream = not no_stream and not cli.is_json

    # -- Streaming path (default for interactive terminals) --------------------
    if use_stream:
        collected = _consume_stream(client.exec_stream(project_id, command))
        if collected:
            last = collected[-1] if collected else {}
            op_status = "completed" if last.get("exit_code", 0) == 0 else "failed"
            _log_operation(cli, project_id, "exec", status=op_status)
            return
        # Stream yielded nothing — fall through to synchronous path

    # -- Synchronous path (--no-stream, --json, or streaming fallback) --------
    try:
        result = client.exec(project_id, command)
    except Exception as exc:
        emit_error(f"Exec failed: {exc}", is_json=cli.is_json)
        raise SystemExit(1) from None

    _log_operation(
        cli,
        project_id,
        "exec",
        status="completed" if result.get("success") else "failed",
    )

    if cli.is_json:
        emit_json(result)
    else:
        if result.get("stdout"):
            click.echo(result["stdout"])
        if result.get("stderr"):
            click.echo(result["stderr"], err=True)


@sandbox.command("destroy")
@click.argument("project_id")
@click.pass_context
def sandbox_destroy(ctx: click.Context, project_id: str) -> None:
    """Destroy a sandbox."""
    cli = get_ctx(ctx)
    client = _get_client()

    try:
        result = client.destroy(project_id)
    except Exception as exc:
        emit_error(f"Failed to destroy sandbox: {exc}", is_json=cli.is_json)
        raise SystemExit(1) from None

    # Update local DB
    try:
        cli.db.sandboxes.update_project(  # type: ignore[attr-defined]
            project_id,
            status="destroyed",
            destroyed_at=datetime.now(UTC).isoformat(),
        )
    except Exception:
        pass

    _log_operation(cli, project_id, "destroy", status="completed")

    if cli.is_json:
        emit_json(result)
    else:
        click.echo(f"Sandbox '{project_id}' destroyed.")


@sandbox.command("sync")
@click.argument("project_id")
@click.pass_context
def sandbox_sync(ctx: click.Context, project_id: str) -> None:
    """Sync execution data from sandbox to local project DB."""
    cli = get_ctx(ctx)
    client = _get_client()

    start = time.monotonic()
    try:
        data = client.export(project_id)
    except Exception as exc:
        duration_ms = int((time.monotonic() - start) * 1000)
        emit_error(f"Failed to export sandbox data: {exc}", is_json=cli.is_json)
        _log_operation(
            cli, project_id, "sync", status="failed", duration_ms=duration_ms, error=str(exc)
        )
        sys.exit(1)

    events = data.get("events", [])
    sessions = data.get("sessions", [])
    artifacts = data.get("artifacts", [])

    counts = {"events": 0, "sessions": 0, "artifacts": 0}
    skipped = {"events": 0, "sessions": 0, "artifacts": 0}

    try:
        # All inserts use raw SQL with INSERT OR IGNORE for idempotent syncs.
        # This sets sandbox_origin_id on every entity type for provenance tracking
        # and avoids duplicates when re-syncing the same sandbox.
        with cli.db.write() as conn:  # type: ignore[attr-defined]
            for s in sessions:
                cursor = conn.execute(
                    """INSERT OR IGNORE INTO workflow_sessions
                       (id, feature_id, snapshot_hash, status, created_at,
                        started_at, ended_at, sandbox_origin_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        s.get("id"),
                        s.get("feature_id"),
                        s.get("snapshot_hash", "sandbox-sync"),
                        s.get("status", "completed"),
                        s.get("created_at"),
                        s.get("started_at"),
                        s.get("ended_at"),
                        project_id,
                    ),
                )
                if cursor.rowcount > 0:
                    counts["sessions"] += 1
                else:
                    skipped["sessions"] += 1

            for e in events:
                payload = e.get("payload")
                payload_json = json.dumps(payload) if payload else None
                created_at = e.get("created_at")
                event_type = e.get("event_type", "unknown")
                session_id = e.get("session_id")
                node_id = e.get("node_id")

                # Dedup: skip if an identical event already exists
                # (events table has no unique constraint, so we check manually)
                existing = conn.execute(
                    """SELECT 1 FROM events
                       WHERE session_id IS ? AND event_type = ? AND node_id IS ?
                         AND created_at = ? AND sandbox_origin_id = ?
                       LIMIT 1""",
                    (session_id, event_type, node_id, created_at, project_id),
                ).fetchone()

                if existing:
                    skipped["events"] += 1
                    continue

                conn.execute(
                    """INSERT INTO events
                       (event_type, session_id, node_id,
                        entity_type, entity_id, payload_json,
                        sandbox_origin_id, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE(?, datetime('now')))""",
                    (
                        event_type,
                        session_id,
                        node_id,
                        e.get("entity_type"),
                        e.get("entity_id"),
                        payload_json,
                        project_id,
                        created_at,
                    ),
                )
                counts["events"] += 1

            for a in artifacts:
                artifact_id = a.get("id")
                if not artifact_id:
                    # Generate an ID if the sandbox export omitted one
                    import uuid

                    artifact_id = f"art-{uuid.uuid4().hex[:8]}"

                cursor = conn.execute(
                    """INSERT OR IGNORE INTO artifacts
                       (id, type, name, path, content,
                        task_id, session_id, tags_json, extra_json,
                        sandbox_origin_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        artifact_id,
                        a.get("type", "other"),
                        a.get("name", "unknown"),
                        a.get("path"),
                        a.get("content"),
                        a.get("task_id"),
                        a.get("session_id"),
                        json.dumps(a.get("tags", [])),
                        json.dumps(a.get("extra", {})),
                        project_id,
                    ),
                )
                if cursor.rowcount > 0:
                    counts["artifacts"] += 1
                else:
                    skipped["artifacts"] += 1

            conn.commit()
    except Exception as exc:
        duration_ms = int((time.monotonic() - start) * 1000)
        emit_error(f"Failed to sync data to local DB: {exc}", is_json=cli.is_json)
        _log_operation(
            cli, project_id, "sync", status="failed", duration_ms=duration_ms, error=str(exc)
        )
        sys.exit(1)

    duration_ms = int((time.monotonic() - start) * 1000)
    _log_operation(cli, project_id, "sync", status="completed", duration_ms=duration_ms)

    summary: dict[str, Any] = {
        "project_id": project_id,
        "synced": counts,
        "duration_ms": duration_ms,
    }
    if any(v > 0 for v in skipped.values()):
        summary["skipped_existing"] = skipped

    if cli.is_json:
        emit_json(summary)
    else:
        click.echo(
            f"Synced {counts['sessions']} sessions, "
            f"{counts['events']} events, "
            f"{counts['artifacts']} artifacts "
            f"from sandbox '{project_id}' ({duration_ms}ms)"
        )
        if any(v > 0 for v in skipped.values()):
            click.echo(
                f"Skipped {skipped['sessions']} sessions, "
                f"{skipped['events']} events, "
                f"{skipped['artifacts']} artifacts (already exist)"
            )

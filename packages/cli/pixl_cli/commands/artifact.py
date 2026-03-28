"""pixl artifact — get, put, list, search, versions."""

from __future__ import annotations

import hashlib

import click

from pixl_cli._output import emit_detail, emit_error, emit_json, emit_table
from pixl_cli.main import get_ctx


@click.group()
@click.pass_context
def artifact(ctx: click.Context) -> None:
    """Manage artifacts."""


@artifact.command("get")
@click.option("--name", required=True, help="Artifact name (logical path).")
@click.option("--session", default=None, help="Session ID (default: from env).")
@click.pass_context
def artifact_get(ctx: click.Context, name: str, session: str | None) -> None:
    """Get an artifact by name."""
    cli = get_ctx(ctx)
    session_id = session or cli.session_id

    if session_id:
        result = cli.db.artifacts.get_by_session_path(session_id, name)
    else:
        # Search by name across all sessions
        results = cli.db.artifacts.search(name, limit=1)
        result = results[0] if results else None

    if result is None:
        emit_error(f"Artifact not found: {name}", is_json=cli.is_json)
        raise SystemExit(1)

    if cli.is_json:
        emit_json(result)
    else:
        emit_detail(result)


@artifact.command("put")
@click.option("--name", required=True, help="Artifact name (logical path).")
@click.option("--content", required=True, help="Artifact content.")
@click.option("--type", "artifact_type", default="other", help="Artifact type.")
@click.option("--session", default=None, help="Session ID (default: from env).")
@click.option("--tags", default=None, help="Comma-separated tags.")
@click.pass_context
def artifact_put(
    ctx: click.Context,
    name: str,
    content: str,
    artifact_type: str,
    session: str | None,
    tags: str | None,
) -> None:
    """Store an artifact."""
    cli = get_ctx(ctx)
    session_id = session or cli.ensure_session()
    stage_id = cli.stage_id or "manual"
    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    result = cli.db.artifacts.put(
        session_id=session_id,
        logical_path=name,
        content=content,
        artifact_type=artifact_type,
        task_id=stage_id,
        name=name,
        tags=tag_list,
    )

    content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
    output = {
        "id": result.get("id", result.get("artifact_id")),
        "sha256": content_hash,
        "name": name,
        "session_id": session_id,
    }

    if cli.is_json:
        emit_json(output)
    else:
        click.echo(f"Stored artifact: {name} (id={output['id']})")


@artifact.command("list")
@click.option("--session", default=None, help="Filter by session ID.")
@click.pass_context
def artifact_list(ctx: click.Context, session: str | None) -> None:
    """List artifacts."""
    cli = get_ctx(ctx)
    session_id = session or cli.session_id

    if session_id:
        results = cli.db.artifacts.list_by_session(session_id)
    else:
        # List recent artifacts across all sessions
        results = cli.db.artifacts.list_page(session_id="", limit=50)

    emit_table(
        results,
        columns=[
            ("id", "ID"),
            ("name", "Name"),
            ("artifact_type", "Type"),
            ("session_id", "Session"),
        ],
        title="Artifacts",
        is_json=cli.is_json,
    )


@artifact.command("search")
@click.option("--query", required=True, help="Search query.")
@click.option("--limit", default=5, type=int, help="Max results.")
@click.option("--type", "artifact_type", default=None, help="Filter by type.")
@click.pass_context
def artifact_search(
    ctx: click.Context,
    query: str,
    limit: int,
    artifact_type: str | None,
) -> None:
    """Search artifacts using full-text search."""
    cli = get_ctx(ctx)
    results = cli.db.artifacts.search(
        query=query,
        limit=limit,
        artifact_type=artifact_type,
    )

    if cli.is_json:
        emit_json(results)
    else:
        if not results:
            click.echo("No artifacts found.")
            return
        for r in results:
            click.echo(
                f"  [{r.get('artifact_type', '?')}] {r.get('name', r.get('logical_path', '?'))}"
            )


@artifact.command("versions")
@click.argument("session_id")
@click.argument("artifact_path")
@click.pass_context
def artifact_versions(ctx: click.Context, session_id: str, artifact_path: str) -> None:
    """List versions of an artifact."""
    cli = get_ctx(ctx)
    versions = cli.db.artifacts.list_versions_by_path(artifact_path, session_id=session_id)

    emit_table(
        versions,
        columns=[
            ("id", "ID"),
            ("version", "Version"),
            ("change_description", "Change"),
            ("created_at", "Created"),
        ],
        title=f"Versions: {artifact_path}",
        is_json=cli.is_json,
    )

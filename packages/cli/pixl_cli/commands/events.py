"""pixl events / pixl event-stats — query events and statistics."""

from __future__ import annotations

import click

from pixl_cli._output import emit_json, emit_table
from pixl_cli.main import get_ctx


@click.command("events")
@click.argument("session_id", required=False, default=None)
@click.option("--type", "event_type", default=None, help="Filter by event type.")
@click.option("--limit", default=20, type=int, help="Max results.")
@click.option("--since", default=None, help="ISO timestamp to filter from.")
@click.pass_context
def events(
    ctx: click.Context,
    session_id: str | None,
    event_type: str | None,
    limit: int,
    since: str | None,
) -> None:
    """Query events, optionally filtered by session."""
    cli = get_ctx(ctx)
    session_id = session_id or cli.session_id

    results = cli.db.events.get_events(
        session_id=session_id,
        event_type=event_type,
        since=since,
        limit=limit,
    )

    emit_table(
        results,
        columns=[
            ("id", "ID"),
            ("event_type", "Type"),
            ("session_id", "Session"),
            ("entity_id", "Entity"),
            ("created_at", "Time"),
        ],
        title="Events",
        is_json=cli.is_json,
    )


@click.command("event_stats")
@click.option("--session", default=None, help="Filter by session ID.")
@click.option("--since", default=None, help="ISO timestamp to filter from.")
@click.pass_context
def event_stats(ctx: click.Context, session: str | None, since: str | None) -> None:
    """Show event statistics (counts by type)."""
    cli = get_ctx(ctx)
    session_id = session or cli.session_id

    counts = cli.db.events.get_event_counts(
        session_id=session_id,
        since=since,
    )

    if cli.is_json:
        emit_json(counts)
    else:
        click.echo("Event counts:")
        for event_type, count in sorted(counts.items(), key=lambda x: -x[1]):
            click.echo(f"  {event_type}: {count}")

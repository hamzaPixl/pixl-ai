"""pixl cost — cost analytics commands."""

from __future__ import annotations

import click

from pixl_cli._output import emit_detail, emit_json, emit_table
from pixl_cli.main import get_ctx


@click.group()
@click.pass_context
def cost(ctx: click.Context) -> None:
    """Cost analytics."""


@cost.command("summary")
@click.pass_context
def cost_summary(ctx: click.Context) -> None:
    """Show overall cost summary."""
    cli = get_ctx(ctx)
    data = cli.db.cost_events.summary()

    if cli.is_json:
        emit_json(data)
    else:
        emit_detail(data, is_json=False)


@cost.command("by-model")
@click.option("--session", default=None, help="Filter by session ID.")
@click.pass_context
def cost_by_model(ctx: click.Context, session: str | None) -> None:
    """Cost breakdown by model."""
    cli = get_ctx(ctx)
    rows = cli.db.cost_events.breakdown_by_model(session_id=session)

    emit_table(
        rows,
        columns=[
            ("model_name", "Model"),
            ("event_count", "Queries"),
            ("input_tokens", "Input Tokens"),
            ("output_tokens", "Output Tokens"),
            ("cost_usd", "Cost (USD)"),
        ],
        title="Cost by Model",
        is_json=cli.is_json,
    )


@cost.command("by-session")
@click.option("--limit", default=20, type=int, help="Max results.")
@click.pass_context
def cost_by_session(ctx: click.Context, limit: int) -> None:
    """Cost breakdown by session."""
    cli = get_ctx(ctx)
    rows = cli.db.cost_events.total_by_session(limit=limit)

    emit_table(
        rows,
        columns=[
            ("session_id", "Session"),
            ("event_count", "Queries"),
            ("input_tokens", "Input Tokens"),
            ("output_tokens", "Output Tokens"),
            ("cost_usd", "Cost (USD)"),
        ],
        title="Cost by Session",
        is_json=cli.is_json,
    )

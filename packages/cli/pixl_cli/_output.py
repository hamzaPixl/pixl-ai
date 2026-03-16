"""Output helpers for CLI commands.

Provides a unified interface for emitting results in either
human-readable (Rich) or JSON format, based on the --json flag.
"""

from __future__ import annotations

import json
import sys
from typing import Any


def emit_json(data: Any) -> None:
    """Write a single JSON object to stdout and flush."""
    sys.stdout.write(json.dumps(data, default=str) + "\n")
    sys.stdout.flush()


def emit_error(message: str, *, is_json: bool = False) -> None:
    """Write an error message to stderr (or JSON to stdout)."""
    if is_json:
        emit_json({"error": message})
    else:
        import click

        click.echo(f"Error: {message}", err=True)


def emit_table(
    rows: list[dict[str, Any]],
    columns: list[tuple[str, str]],
    *,
    title: str | None = None,
    is_json: bool = False,
) -> None:
    """Emit data as a table (human) or JSON array (machine).

    Args:
        rows: List of dicts, one per row.
        columns: List of (key, header_label) tuples.
        title: Optional table title (human mode only).
        is_json: If True, emit JSON instead of a table.
    """
    if is_json:
        emit_json(rows)
        return

    from rich.console import Console
    from rich.table import Table

    table = Table(title=title, show_lines=False)
    for _, header in columns:
        table.add_column(header)

    for row in rows:
        table.add_row(*(str(row.get(key, "")) for key, _ in columns))

    Console().print(table)


def emit_detail(data: dict[str, Any], *, is_json: bool = False) -> None:
    """Emit a single record as key-value pairs (human) or JSON (machine)."""
    if is_json:
        emit_json(data)
        return

    from rich.console import Console
    from rich.table import Table

    table = Table(show_header=False, show_lines=False, pad_edge=False)
    table.add_column("Key", style="bold cyan")
    table.add_column("Value")

    for key, value in data.items():
        table.add_row(key, str(value) if value is not None else "-")

    Console().print(table)

"""pixl config — get/set configuration values."""

from __future__ import annotations

import click

from pixl_cli._output import emit_error, emit_json
from pixl_cli.main import get_ctx


@click.group()
@click.pass_context
def config(ctx: click.Context) -> None:
    """Manage pixl configuration."""


@config.command("get")
@click.argument("key")
@click.pass_context
def config_get(ctx: click.Context, key: str) -> None:
    """Get a configuration value."""
    from pixl.storage.config_store import ConfigStore

    cli = get_ctx(ctx)
    store = ConfigStore(cli.project_path, pixl_dir=cli.pixl_dir)

    try:
        value = store.get(key)
    except Exception as exc:
        emit_error(str(exc), is_json=cli.is_json)
        raise SystemExit(1) from None

    if cli.is_json:
        emit_json({"key": key, "value": value})
    else:
        click.echo(f"{key}={value}")


@config.command("set")
@click.argument("key")
@click.argument("value")
@click.pass_context
def config_set(ctx: click.Context, key: str, value: str) -> None:
    """Set a configuration value."""
    from pixl.storage.config_store import ConfigStore

    cli = get_ctx(ctx)
    store = ConfigStore(cli.project_path, pixl_dir=cli.pixl_dir)

    try:
        store.set(key, value)
    except ValueError as exc:
        emit_error(str(exc), is_json=cli.is_json)
        raise SystemExit(1) from None

    if cli.is_json:
        emit_json({"key": key, "value": value, "updated": True})
    else:
        click.echo(f"Set {key}={value}")

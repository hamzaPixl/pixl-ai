"""pixl template — list, get, create, update, delete DB-backed workflow templates."""

from __future__ import annotations

from pathlib import Path

import click

from pixl_cli._output import emit_detail, emit_error, emit_json, emit_table
from pixl_cli.main import get_ctx


def _templates(ctx: click.Context):  # type: ignore[no-untyped-def]
    """Get workflow_templates store from CLI context (dynamic attr on StorageBackend)."""
    return get_ctx(ctx).db.workflow_templates  # type: ignore[attr-defined]


@click.group()
@click.pass_context
def template(ctx: click.Context) -> None:
    """Manage DB-backed workflow templates."""


@template.command("list")
@click.option(
    "--source",
    default=None,
    type=click.Choice(["db", "filesystem", "imported"]),
    help="Filter by source.",
)
@click.option("--limit", default=50, type=int, help="Max results.")
@click.pass_context
def template_list(ctx: click.Context, source: str | None, limit: int) -> None:
    """List workflow templates."""
    cli = get_ctx(ctx)
    results = _templates(ctx).list_templates(source=source, limit=limit)

    emit_table(
        results,
        columns=[
            ("id", "ID"),
            ("name", "Name"),
            ("version", "Version"),
            ("source", "Source"),
            ("description", "Description"),
            ("created_at", "Created"),
        ],
        title="Workflow Templates",
        is_json=cli.is_json,
    )


@template.command("get")
@click.argument("template_id")
@click.pass_context
def template_get(ctx: click.Context, template_id: str) -> None:
    """Get a workflow template by ID."""
    cli = get_ctx(ctx)
    result = _templates(ctx).get(template_id)

    if result is None:
        emit_error(f"Template not found: {template_id}", is_json=cli.is_json)
        raise SystemExit(1)

    if cli.is_json:
        emit_json(result)
    else:
        emit_detail(result)


@template.command("create")
@click.argument("name")
@click.option(
    "--file",
    "yaml_file",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to YAML workflow file.",
)
@click.option("--description", default=None, help="Template description.")
@click.option(
    "--source",
    default="db",
    type=click.Choice(["db", "filesystem", "imported"]),
    help="Template source.",
)
@click.pass_context
def template_create(
    ctx: click.Context,
    name: str,
    yaml_file: Path,
    description: str | None,
    source: str,
) -> None:
    """Create a new workflow template from a YAML file."""
    cli = get_ctx(ctx)
    yaml_content = yaml_file.read_text(encoding="utf-8")

    result = _templates(ctx).create(
        name,
        yaml_content,
        description=description,
        source=source,
    )

    if cli.is_json:
        emit_json(result)
    else:
        name = result["name"]
        tid = result["id"]
        ver = result["version"]
        click.echo(f"Created template: {name} (id={tid}, version={ver})")


@template.command("update")
@click.argument("template_id")
@click.option(
    "--file",
    "yaml_file",
    default=None,
    type=click.Path(exists=True, path_type=Path),
    help="Path to updated YAML workflow file.",
)
@click.option("--description", default=None, help="Updated description.")
@click.pass_context
def template_update(
    ctx: click.Context,
    template_id: str,
    yaml_file: Path | None,
    description: str | None,
) -> None:
    """Update a workflow template (bumps version)."""
    cli = get_ctx(ctx)

    yaml_content = None
    if yaml_file is not None:
        yaml_content = yaml_file.read_text(encoding="utf-8")

    if yaml_content is None and description is None:
        emit_error("Nothing to update. Provide --file or --description.", is_json=cli.is_json)
        raise SystemExit(1)

    success = _templates(ctx).update(
        template_id,
        yaml_content=yaml_content,
        description=description,
    )

    if not success:
        emit_error(f"Template not found: {template_id}", is_json=cli.is_json)
        raise SystemExit(1)

    updated = _templates(ctx).get(template_id)
    if cli.is_json:
        emit_json(updated)
    else:
        click.echo(f"Updated template: {updated['name']} (version={updated['version']})")


@template.command("delete")
@click.argument("template_id")
@click.option("--yes", is_flag=True, default=False, help="Skip confirmation.")
@click.pass_context
def template_delete(ctx: click.Context, template_id: str, yes: bool) -> None:
    """Delete a workflow template."""
    cli = get_ctx(ctx)

    if not yes:
        existing = _templates(ctx).get(template_id)
        if existing is None:
            emit_error(f"Template not found: {template_id}", is_json=cli.is_json)
            raise SystemExit(1)
        if not click.confirm(f"Delete template '{existing['name']}' ({template_id})?"):
            click.echo("Cancelled.")
            return

    success = _templates(ctx).delete(template_id)

    if not success:
        emit_error(f"Template not found: {template_id}", is_json=cli.is_json)
        raise SystemExit(1)

    if cli.is_json:
        emit_json({"deleted": template_id})
    else:
        click.echo(f"Deleted template: {template_id}")

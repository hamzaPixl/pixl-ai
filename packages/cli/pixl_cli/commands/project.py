"""pixl project — list, get, create, init, delete projects."""

from __future__ import annotations

import click

from pixl_cli._output import emit_detail, emit_error, emit_json, emit_table
from pixl_cli.main import get_ctx


@click.group()
@click.pass_context
def project(ctx: click.Context) -> None:
    """Manage pixl projects."""


@project.command("list")
@click.pass_context
def project_list(ctx: click.Context) -> None:
    """List all known projects."""
    from pixl.projects.registry import list_projects

    cli = get_ctx(ctx)
    projects = list_projects()
    emit_table(
        projects,
        columns=[
            ("project_id", "ID"),
            ("project_name", "Name"),
            ("project_root", "Root"),
            ("storage_dir", "Storage"),
        ],
        title="Projects",
        is_json=cli.is_json,
    )


@project.command("get")
@click.argument("project_id")
@click.pass_context
def project_get(ctx: click.Context, project_id: str) -> None:
    """Get project info by ID."""
    from pixl.projects.registry import get_project

    cli = get_ctx(ctx)
    info = get_project(project_id)
    if info is None:
        emit_error(f"Project not found: {project_id}", is_json=cli.is_json)
        raise SystemExit(1)
    emit_detail(info, is_json=cli.is_json)


@project.command("create")
@click.option("--name", required=True, help="Project name.")
@click.option("--root", "project_root", default=None, help="Project root path on disk.")
@click.option("--description", default="", help="Project description.")
@click.pass_context
def project_create(
    ctx: click.Context,
    name: str,
    project_root: str | None,
    description: str,
) -> None:
    """Create a new project in the global workspace."""
    from pixl.projects.registry import create_project

    cli = get_ctx(ctx)
    try:
        info = create_project(name=name, description=description, project_root=project_root)
    except ValueError as exc:
        emit_error(str(exc), is_json=cli.is_json)
        raise SystemExit(1) from None

    if cli.is_json:
        emit_json(info)
    else:
        click.echo(f"Created project: {info['project_id']}")


@project.command("init")
@click.pass_context
def project_init(ctx: click.Context) -> None:
    """Initialize pixl for the current project directory.

    Creates the .pixl directory structure and backfills config.
    """
    from pixl.projects.registry import ensure_project_config

    cli = get_ctx(ctx)
    cli.pixl_dir.mkdir(parents=True, exist_ok=True)
    (cli.pixl_dir / "sessions").mkdir(exist_ok=True)
    (cli.pixl_dir / "workflows").mkdir(exist_ok=True)

    ensure_project_config(cli.project_path)

    if cli.is_json:
        emit_json(
            {
                "project_id": cli.project_id,
                "pixl_dir": str(cli.pixl_dir),
                "status": "initialized",
            }
        )
    else:
        click.echo(f"Initialized pixl project: {cli.project_id}")
        click.echo(f"  Storage: {cli.pixl_dir}")


@project.command("delete")
@click.argument("project_id")
@click.option("--yes", is_flag=True, help="Skip confirmation prompt.")
@click.pass_context
def project_delete(ctx: click.Context, project_id: str, yes: bool) -> None:
    """Delete a project from the global workspace."""
    from pixl.projects.registry import delete_project

    cli = get_ctx(ctx)
    if not yes:
        click.confirm(f"Delete project '{project_id}' and all its data?", abort=True)

    deleted = delete_project(project_id)
    if not deleted:
        emit_error(f"Project not found: {project_id}", is_json=cli.is_json)
        raise SystemExit(1)

    if cli.is_json:
        emit_json({"project_id": project_id, "deleted": True})
    else:
        click.echo(f"Deleted project: {project_id}")

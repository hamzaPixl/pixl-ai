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


@project.command("new")
@click.argument("name")
@click.option(
    "--path",
    "parent_dir",
    default=None,
    help="Parent directory (default: ~/projects/).",
)
@click.option("--description", default="", help="Project description.")
@click.option("--setup/--no-setup", default=True, help="Run project-setup workflow after creation.")
@click.pass_context
def project_new(
    ctx: click.Context,
    name: str,
    parent_dir: str | None,
    description: str,
    setup: bool,
) -> None:
    """Create a new project from scratch — directory, git, pixl, and setup workflow.

    This is the single entry point for starting a new project:
    1. Creates the project directory
    2. Initializes git
    3. Registers with pixl (project init + DB)
    4. Initializes crew (CLAUDE.md, rules, permissions from crew-init templates)
    5. Optionally runs the project-setup workflow (backlog, knowledge index)

    Example:
        pixl project new demo-web
        pixl project new my-api --path ~/code --description "REST API for widgets"
    """
    import os
    import subprocess
    from pathlib import Path

    from pixl.projects.registry import ensure_project_config

    # 1. Resolve parent directory
    if parent_dir is None:
        parent_dir = os.path.expanduser("~/projects")
    parent = Path(parent_dir)
    parent.mkdir(parents=True, exist_ok=True)

    project_dir = parent / name
    if project_dir.exists() and any(project_dir.iterdir()):
        click.echo(f"Directory already exists and is not empty: {project_dir}")
        raise SystemExit(1)

    project_dir.mkdir(parents=True, exist_ok=True)
    click.echo(f"Created {project_dir}")

    # 2. Git init
    subprocess.run(["git", "init"], cwd=str(project_dir), check=True, capture_output=True)
    readme = project_dir / "README.md"
    readme.write_text(f"# {name}\n\n{description}\n")
    click.echo("Initialized git repository")

    # 3. Pixl project init
    pixl_dir = project_dir / ".pixl"
    pixl_dir.mkdir(parents=True, exist_ok=True)
    (pixl_dir / "sessions").mkdir(exist_ok=True)
    (pixl_dir / "workflows").mkdir(exist_ok=True)
    ensure_project_config(project_dir)
    click.echo("Registered pixl project")

    # 4. Initialize crew (copy templates from crew-init)
    from pixl_cli.crew import get_crew_root

    try:
        crew_root = get_crew_root()
        templates_dir = Path(crew_root) / "templates" / "crew-init"
        if templates_dir.is_dir():
            import shutil

            # CLAUDE.md from template
            tmpl = templates_dir / "CLAUDE.md.tmpl"
            if tmpl.is_file():
                content = tmpl.read_text()
                content = content.replace("{{PROJECT_NAME}}", name)
                (project_dir / "CLAUDE.md").write_text(content)

            # .claude/rules/ from templates
            rules_dir = project_dir / ".claude" / "rules"
            rules_dir.mkdir(parents=True, exist_ok=True)
            for rule_file in ["crew-workflow.md", "crew-delegation.md", "crew-enforcement.md"]:
                src = templates_dir / rule_file
                if src.is_file():
                    shutil.copy2(str(src), str(rules_dir / rule_file))

            # .claude/settings.local.json (only if not exists)
            settings_src = templates_dir / "settings.local.json"
            settings_dst = project_dir / ".claude" / "settings.local.json"
            if settings_src.is_file() and not settings_dst.exists():
                shutil.copy2(str(settings_src), str(settings_dst))

            click.echo("Initialized crew (CLAUDE.md, rules, permissions)")
        else:
            click.echo("Crew templates not found — skipping crew init")
    except FileNotFoundError:
        click.echo("Crew plugin not found — skipping crew init")

    # 5. Initial git commit (includes README, CLAUDE.md, rules, .gitignore)
    subprocess.run(["git", "add", "-A"], cwd=str(project_dir), check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", f"init: {name} — pixl project with crew"],
        cwd=str(project_dir),
        check=True,
        capture_output=True,
    )

    # 6. Run project-setup workflow
    if setup:
        click.echo("\nRunning project-setup workflow...")
        result = subprocess.run(
            [
                "pixl",
                "--project",
                str(project_dir),
                "workflow",
                "run",
                "--workflow",
                "project-setup",
                "--yes",
            ],
            cwd=str(project_dir),
        )
        if result.returncode != 0:
            click.echo("Warning: project-setup workflow failed. Run manually with:")
            click.echo(f"  cd {project_dir} && pixl workflow run --workflow project-setup --yes")
    else:
        click.echo("\nProject ready. To set up:")
        click.echo(f"  cd {project_dir}")
        click.echo("  pixl workflow run --workflow project-setup --yes")

    cli = get_ctx(ctx)
    if cli.is_json:
        emit_json(
            {
                "name": name,
                "path": str(project_dir),
                "setup_run": setup,
            }
        )


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

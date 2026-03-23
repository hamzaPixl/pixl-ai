"""Root Click group with global options (--json, --project).

Entry point: ``pixl`` binary, registered via pyproject.toml [project.scripts].
"""

from __future__ import annotations

import click

from pixl_cli._lazy import LazyGroup
from pixl_cli.context import CLIContext

COMMAND_MODULES = {
    "artifact": "pixl_cli.commands.artifact",
    "config": "pixl_cli.commands.config",
    "cost": "pixl_cli.commands.cost",
    "event-stats": "pixl_cli.commands.events",
    "events": "pixl_cli.commands.events",
    "knowledge": "pixl_cli.commands.knowledge",
    "project": "pixl_cli.commands.project",
    "sandbox": "pixl_cli.commands.sandbox",
    "session": "pixl_cli.commands.session",
    "setup": "pixl_cli.commands.setup",
    "state": "pixl_cli.commands.state",
    "template": "pixl_cli.commands.template",
    "workflow": "pixl_cli.commands.workflow",
}


@click.group(cls=LazyGroup, lazy_subcommands=COMMAND_MODULES)
@click.option("--json", "use_json", is_flag=True, default=False, help="Output JSON instead of human-readable text.")
@click.option("--project", "project_path", default=None, type=str, help="Project root path (default: cwd).")
@click.version_option(package_name="pixl-cli")
@click.pass_context
def cli(ctx: click.Context, use_json: bool, project_path: str | None) -> None:
    """Pixl CLI — local bridge to the pixl-engine."""
    ctx.ensure_object(dict)
    cli_ctx = CLIContext(project=project_path, is_json=use_json)
    ctx.obj["cli_ctx"] = cli_ctx

    if use_json:
        from pixl.output import OutputFormat, set_output_format

        set_output_format(OutputFormat.JSON)

    # Ensure cleanup on exit
    ctx.call_on_close(cli_ctx.close)


def get_ctx(ctx: click.Context) -> CLIContext:
    """Helper to extract CLIContext from Click context."""
    return ctx.obj["cli_ctx"]

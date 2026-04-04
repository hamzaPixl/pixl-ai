"""pixl codex — Codex scaffolding and verification."""

from __future__ import annotations

import shutil

import click

from pixl_cli._output import emit_json
from pixl_cli.commands.project import _install_codex_scaffold
from pixl_cli.crew import get_crew_root
from pixl_cli.main import get_ctx


@click.group()
def codex() -> None:
    """Codex setup and helpers."""


@codex.command("setup")
@click.option("--name", default=None, help="Project name (default: directory name).")
@click.pass_context
def codex_setup(ctx: click.Context, name: str | None) -> None:
    """Install Codex scaffolding in the current project.

    Creates:
      - AGENTS.md
      - .codex/ (config, hooks, rules, agents)
      - .agents/skills (symlinks to crew skills)
    """
    cli = get_ctx(ctx)
    project_path = cli.project_path
    project_name = name or project_path.name

    try:
        crew_root = get_crew_root()
    except FileNotFoundError:
        click.echo("Crew plugin not found — cannot install Codex scaffolding")
        return
    result: dict[str, bool] = {"codex_installed": False, "agents_md_created": False}

    _install_codex_scaffold(project_path, crew_root, project_name, result)

    if cli.is_json:
        emit_json(
            {
                "codex_installed": result["codex_installed"],
                "agents_md_created": result["agents_md_created"],
                "project": str(project_path),
            }
        )
        return

    click.echo(f"Codex scaffolding installed for {project_path}")
    if result["agents_md_created"]:
        click.echo("  AGENTS.md created")
    else:
        click.echo("  AGENTS.md already exists — skipped")


@codex.command("verify")
@click.option("--run-engine/--no-run-engine", default=True, help="Run a Pixl workflow using Codex.")
@click.option("--prompt", default=None, help="Override the Codex exec prompt.")
@click.pass_context
def codex_verify(ctx: click.Context, run_engine: bool, prompt: str | None) -> None:
    """Verify Codex CLI + Pixl engine integration.

    Runs:
      1) codex exec (read-only) to list skills and summarize repo
      2) optional pixl workflow using Codex provider
    """
    import json
    import subprocess

    cli = get_ctx(ctx)
    root = cli.project_path
    out_path = root / ".codex-verify.jsonl"

    if not shutil.which("codex"):
        raise click.ClickException(
            "codex CLI not found. Install with: npm install -g @openai/codex"
        )

    exec_prompt = (
        prompt
        or "Can you list the available skills (just the names) and confirm that task-plan exists? "
        "Also summarize the repo layout. If subagents are supported, try the orchestrator. "
        "Please do not modify any files."
    )

    with out_path.open("w", encoding="utf-8") as f:
        subprocess.run(
            ["codex", "exec", "-s", "read-only", "--json", "-C", str(root), exec_prompt],
            check=True,
            stdout=f,
        )

    found_task_plan = False
    with out_path.open("r", encoding="utf-8") as f:
        for line in f:
            if "task-plan" in line:
                found_task_plan = True
                break

    click.echo(f"Codex exec output: {out_path}")
    click.echo("Skill check: " + ("task-plan found" if found_task_plan else "task-plan NOT found"))

    if run_engine:
        subprocess.run(
            ["pixl", "config", "set", "default_model", "codex/gpt-5.2-codex"],
            check=True,
            cwd=str(root),
        )
        subprocess.run(
            [
                "pixl",
                "workflow",
                "run",
                "--workflow",
                "codex-verify",
                "--yes",
                "--prompt",
                "Verify Codex integration for this repo. Do not modify files.",
            ],
            check=True,
            cwd=str(root),
        )
        # Optional: print recent cost summary lines for codex
        try:
            result = subprocess.run(
                ["pixl", "cost", "summary", "--json"],
                check=True,
                cwd=str(root),
                capture_output=True,
                text=True,
            )
            data = json.loads(result.stdout)
            by_model = data.get("by_model", {})
            codex_models = {k: v for k, v in by_model.items() if "codex" in k or "gpt-5" in k}
            click.echo(f"Codex model usage: {codex_models}")
        except Exception:
            click.echo("Warning: could not read codex usage from cost summary.")

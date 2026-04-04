"""pixl codex — Codex scaffolding and verification."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import click
import yaml

from pixl_cli._output import emit_json
from pixl_cli.commands.project import _install_codex_scaffold
from pixl_cli.crew import get_crew_root
from pixl_cli.main import get_ctx


@click.group()
def codex() -> None:
    """Codex setup and helpers."""


@codex.command("setup")
@click.option("--name", default=None, help="Project name (default: directory name).")
@click.option(
    "--set-default-provider/--no-set-default-provider",
    default=False,
    help="Persist Codex as default provider in .pixl/providers.yaml.",
)
@click.pass_context
def codex_setup(ctx: click.Context, name: str | None, set_default_provider: bool) -> None:
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
    if set_default_provider:
        _persist_codex_provider_defaults(project_path)
        click.echo("  Default provider set to codex (see .pixl/providers.yaml)")


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
        providers_path = _set_codex_provider_defaults(root)
        try:
            result = subprocess.run(
                [
                    "pixl",
                    "--json",
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
                capture_output=True,
                text=True,
            )
            session_id = ""
            try:
                payload = json.loads(result.stdout)
                session_id = payload.get("session_id") or ""
            except json.JSONDecodeError:
                match = re.search(r'"session_id"\s*:\s*"([^"]+)"', result.stdout)
                if match:
                    session_id = match.group(1)
            if session_id:
                sess = subprocess.run(
                    ["pixl", "--json", "session", "get", session_id],
                    check=True,
                    cwd=str(root),
                    capture_output=True,
                    text=True,
                )
                session_data = json.loads(sess.stdout)
                model_names = {
                    inst.get("model_name")
                    for inst in session_data.get("node_instances", {}).values()
                    if inst.get("model_name")
                }
                codex_models = [m for m in model_names if "codex" in m or "gpt-5" in m]
                click.echo(f"Session models (session {session_id}): {sorted(model_names)}")
                if codex_models:
                    click.echo(f"Codex models detected: {codex_models}")
                else:
                    click.echo("Warning: No Codex models detected in session.")
            else:
                click.echo("Warning: could not parse session_id from workflow output.")
        finally:
            _restore_providers_yaml(providers_path)


def _set_codex_provider_defaults(project_root: Path) -> Path:
    """Temporarily set default provider/model to Codex in .pixl/providers.yaml."""
    pixl_dir = project_root / ".pixl"
    pixl_dir.mkdir(parents=True, exist_ok=True)
    providers_path = pixl_dir / "providers.yaml"
    backup_path = pixl_dir / "providers.yaml.bak"

    if providers_path.exists():
        backup_path.write_text(providers_path.read_text())

    data = {}
    if providers_path.exists():
        try:
            data = yaml.safe_load(providers_path.read_text()) or {}
        except Exception:
            data = {}
    data["default_provider"] = "codex"
    data["default_model"] = "codex/gpt-5.2-codex"
    providers_path.write_text(yaml.safe_dump(data, sort_keys=False))
    return providers_path


def _persist_codex_provider_defaults(project_root: Path) -> None:
    """Persist Codex as the default provider in .pixl/providers.yaml."""
    pixl_dir = project_root / ".pixl"
    pixl_dir.mkdir(parents=True, exist_ok=True)
    providers_path = pixl_dir / "providers.yaml"

    data = {}
    if providers_path.exists():
        try:
            data = yaml.safe_load(providers_path.read_text()) or {}
        except Exception:
            data = {}
    data["default_provider"] = "codex"
    data["default_model"] = "codex/gpt-5.2-codex"
    providers_path.write_text(yaml.safe_dump(data, sort_keys=False))


def _restore_providers_yaml(providers_path: Path) -> None:
    """Restore .pixl/providers.yaml if a backup exists; otherwise remove it."""
    backup_path = providers_path.parent / "providers.yaml.bak"
    if backup_path.exists():
        providers_path.write_text(backup_path.read_text())
        backup_path.unlink()
        return
    try:
        providers_path.unlink()
    except OSError:
        pass

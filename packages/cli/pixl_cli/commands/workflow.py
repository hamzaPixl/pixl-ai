"""pixl workflow — list, run, step."""

from __future__ import annotations

import asyncio

import click

from pixl_cli._output import emit_error, emit_json, emit_table
from pixl_cli.main import get_ctx


@click.group()
@click.pass_context
def workflow(ctx: click.Context) -> None:
    """Manage and execute workflows."""


@workflow.command("list")
@click.pass_context
def workflow_list(ctx: click.Context) -> None:
    """List available workflows."""
    from pixl.config.workflow_loader import WorkflowLoader

    cli = get_ctx(ctx)
    loader = WorkflowLoader(cli.project_path)
    workflows = loader.list_workflows()

    emit_table(
        workflows,
        columns=[
            ("id", "ID"),
            ("name", "Name"),
            ("version", "Version"),
            ("source", "Source"),
            ("description", "Description"),
        ],
        title="Workflows",
        is_json=cli.is_json,
    )


@workflow.command("run")
@click.option("--prompt", required=True, help="Prompt describing what to build.")
@click.option("--workflow", "workflow_id", default=None, help="Workflow ID (auto-selects if not specified).")
@click.pass_context
def workflow_run(ctx: click.Context, prompt: str, workflow_id: str | None) -> None:
    """Run a workflow from a prompt.

    Classifies the prompt, creates a feature, loads the workflow,
    creates a session, and executes the DAG.
    """
    import os

    cli = get_ctx(ctx)

    # Force SDK execution backend (no Daytona sandbox)
    os.environ["PIXL_EXECUTION_BACKEND"] = "sdk"

    if not cli.is_json:
        click.echo(f"Starting workflow for: {prompt}")

    asyncio.run(_run_workflow(cli, prompt, workflow_id))


async def _run_workflow(cli, prompt: str, workflow_id: str | None) -> None:
    """Async workflow execution."""
    from pixl.config.workflow_loader import WorkflowLoader

    db = cli.db

    # 1. Create a feature for this prompt
    feature = db.backlog.add_feature(
        title=prompt[:120],
        description=prompt,
        feature_type="feature",
    )
    feature_id = feature["id"]

    if not cli.is_json:
        click.echo(f"  Feature: {feature_id}")

    # 2. Load workflow
    loader = WorkflowLoader(cli.project_path)

    if workflow_id:
        config = loader.load_workflow(workflow_id)
    else:
        workflows = loader.list_workflows()
        if not workflows:
            emit_error("No workflows available.", is_json=cli.is_json)
            raise SystemExit(1)
        # Pick the first general-purpose workflow
        config = loader.load_workflow(workflows[0]["id"])

    template = loader.convert_to_template(config)
    snapshot = template.snapshot

    if not cli.is_json:
        click.echo(f"  Workflow: {config.id} v{config.version}")

    # 3. Create session
    session = db.sessions.create_session(
        feature_id=feature_id,
        snapshot_hash=snapshot.snapshot_hash,
    )
    session_id = session["session_id"]

    if not db.sessions.snapshot_exists(snapshot.snapshot_hash):
        db.sessions.save_snapshot(
            snapshot.snapshot_hash,
            snapshot.model_dump_json(),
        )

    if not cli.is_json:
        click.echo(f"  Session: {session_id}")

    # 4. Execute via GraphExecutor
    try:
        from pixl.execution import GraphExecutor
        from pixl.orchestration.core import OrchestratorCore
        from pixl.paths import get_sessions_dir

        session_dir = get_sessions_dir(cli.project_path) / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        orchestrator = OrchestratorCore(cli.project_path, sandbox_backend=None)

        executor = GraphExecutor(
            session_id=session_id,
            snapshot=snapshot,
            session_dir=session_dir,
            orchestrator=orchestrator,
            storage=db,
        )

        if not cli.is_json:
            click.echo("  Executing DAG...")

        while not executor.is_terminal():
            await executor.step()
            status = executor.get_status()
            if not cli.is_json:
                click.echo(f"    Step: {status}")

        if not cli.is_json:
            click.echo("  Workflow complete.")

        if cli.is_json:
            emit_json({
                "session_id": session_id,
                "feature_id": feature_id,
                "workflow_id": config.id,
                "status": "completed",
            })

    except ImportError as exc:
        # GraphExecutor may need additional deps
        emit_error(f"Execution requires additional dependencies: {exc}", is_json=cli.is_json)
        raise SystemExit(1) from None
    except Exception as exc:
        emit_error(f"Workflow execution failed: {exc}", is_json=cli.is_json)
        if cli.is_json:
            emit_json({
                "session_id": session_id,
                "feature_id": feature_id,
                "workflow_id": config.id,
                "status": "failed",
                "error": str(exc),
            })
        raise SystemExit(1) from None

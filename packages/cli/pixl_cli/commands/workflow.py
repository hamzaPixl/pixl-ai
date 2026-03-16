"""pixl workflow — list, run, step."""

from __future__ import annotations

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
    cli = get_ctx(ctx)

    if not cli.is_json:
        click.echo(f"Starting workflow for: {prompt}")

    _run_workflow_sync(cli, prompt, workflow_id)


def _run_workflow_sync(cli, prompt: str, workflow_id: str | None) -> None:
    """Synchronous workflow execution."""
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
        config = loader.load_workflow(workflows[0]["id"])

    template = loader.convert_to_template(config)
    snapshot = template.snapshot

    if not cli.is_json:
        click.echo(f"  Workflow: {config.id} v{config.version}")

    # 3. Create session via WorkflowSessionStore (produces WorkflowSession model)
    try:
        from pixl.execution import GraphExecutor
        from pixl.orchestration.core import OrchestratorCore
        from pixl.paths import get_sessions_dir
        from pixl.storage import WorkflowSessionStore

        session_store = WorkflowSessionStore(cli.project_path)
        session = session_store.create_session(feature_id, snapshot)
        session_id = session.id

        if not cli.is_json:
            click.echo(f"  Session: {session_id}")

        # Also track in PixlDB for observability
        db.sessions.create_session(
            feature_id=feature_id,
            snapshot_hash=snapshot.snapshot_hash,
        )

        # 4. Execute via GraphExecutor
        session_dir = get_sessions_dir(cli.project_path) / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        orchestrator = OrchestratorCore(cli.project_path)

        executor = GraphExecutor(
            session,
            snapshot,
            session_dir,
            project_root=cli.project_path,
            orchestrator=orchestrator,
            db=db,
        )

        if not cli.is_json:
            click.echo("  Executing DAG...")

        step_count = 0
        max_steps = 100

        while step_count < max_steps:
            result = executor.step()

            if not result["executed"]:
                if result.get("terminal"):
                    break
                break

            step_count += 1
            if not cli.is_json:
                node_id = result.get("node_id", "?")
                click.echo(f"    Step {step_count}: {node_id}")

        final_status = session.status.value if hasattr(session.status, "value") else str(session.status)

        if not cli.is_json:
            click.echo(f"  Workflow complete ({final_status}, {step_count} steps).")

        if cli.is_json:
            emit_json({
                "session_id": session_id,
                "feature_id": feature_id,
                "workflow_id": config.id,
                "status": final_status,
                "steps": step_count,
            })

    except ImportError as exc:
        emit_error(f"Execution requires additional dependencies: {exc}", is_json=cli.is_json)
        raise SystemExit(1) from None
    except Exception as exc:
        emit_error(f"Workflow execution failed: {exc}", is_json=cli.is_json)
        if cli.is_json:
            emit_json({
                "feature_id": feature_id,
                "workflow_id": config.id if "config" in dir() else workflow_id,
                "status": "failed",
                "error": str(exc),
            })
        raise SystemExit(1) from None

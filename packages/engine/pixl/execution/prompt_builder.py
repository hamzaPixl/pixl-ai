"""Prompt building and template resolution for workflow execution.

Extracted from graph_executor.py — handles prompt compilation, variable
resolution, feedback context, and feature context loading.
"""

from __future__ import annotations

import copy
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pixl.prompts.schema_contract import render_payload_contract_from_path

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pixl.models.session import WorkflowSession
    from pixl.models.workflow import Node, WorkflowSnapshot
    from pixl.storage import WorkflowSessionStore

def build_validation_followup_prompt(
    *,
    node_id: str,
    validation_errors: list[str],
    previous_output: str,
    expects_structured: bool,
    attempt: int = 1,
    output_schema_path: str | None = None,
) -> str:
    """Build a targeted follow-up prompt after deterministic validation fails.

    Progressive simplification:
    - attempt 1: full schema with all fields
    - attempt 2: minimal schema (only required fields)
    - attempt 3+: delegates to strict repair-only prompt
    """
    # attempt 3+ → strict repair mode (no schema explanation, just fix it)
    if attempt >= 3 and expects_structured:
        return build_structured_output_repair_prompt(
            node_id=node_id,
            validation_errors=validation_errors,
            previous_output=previous_output,
            output_schema_path=output_schema_path,
        )

    excerpt = previous_output[-4000:] if len(previous_output) > 4000 else previous_output
    bullets = "\n".join(f"- {err}" for err in validation_errors[:20])
    schema_guidance = _build_schema_contract_guidance(output_schema_path)

    # Detect artifact-missing errors and add specific remediation guidance
    has_artifact_missing = any(
        "artifact_missing" in err or "artifact store" in err for err in validation_errors
    )
    artifact_fix_guidance = ""
    if has_artifact_missing:
        artifact_fix_guidance = (
            "\n## IMPORTANT: Fixing Missing Artifacts\n\n"
            "Your artifacts were NOT found in the session store. Writing files to disk with\n"
            "`write_file` does NOT register them as artifacts.\n\n"
            "You MUST use `pixl artifact put` to save each artifact:\n"
            "```bash\n"
            'pixl artifact put --name <filename> --content "$(cat <filename>)"\n'
            "```\n"
            "The command prints the SHA256 hash. Use `--json` for machine-readable output.\n\n"
            "If you are using `run_shell_command`, call it like:\n"
            "```\nrun_shell_command(command=\"pixl artifact put --name plan.md --content '$(cat plan.md)'\")\n```\n\n"
            "Do this for EVERY file listed in your `artifacts_written` array.\n\n"
        )

    if not expects_structured:
        return (
            f"Follow-up for stage '{node_id}'.\n\n"
            "Your previous output failed deterministic validation.\n"
            "Please fix ONLY the listed violations and keep the task scope unchanged.\n\n"
            "Validation errors:\n"
            f"{bullets}\n\n"
            f"{artifact_fix_guidance}"
            "Apply the minimal required changes to satisfy all violations.\n\n"
            "Previous output:\n"
            "```text\n"
            f"{excerpt}\n"
            "```"
        )

    # attempt 2+: simplified schema (only required fields)
    if attempt >= 2:
        return (
            f"Follow-up for stage '{node_id}'.\n\n"
            "CRITICAL: Your structured output is still invalid after "
            f"{attempt - 1} previous attempt(s). Simplify your output.\n\n"
            "Validation errors:\n"
            f"{bullets}\n\n"
            f"{schema_guidance}"
            "Return this minimal structure (fill in your values), and include any "
            "required `payload` keys from the schema-derived contract above:\n"
            "```\n"
            "<pixl_output>\n"
            "{\n"
            '  "schema_version": "1.0",\n'
            '  "stage_id": "' + node_id + '",\n'
            '  "status": "ok",\n'
            '  "summary": ["what you did"],\n'
            '  "artifacts_written": []\n'
            "}\n"
            "</pixl_output>\n"
            "```\n\n"
            f"{artifact_fix_guidance}"
            "Do NOT include any text before or after the <pixl_output> block.\n\n"
            "Previous output:\n"
            "```text\n"
            f"{excerpt}\n"
            "```"
        )

    return (
        f"Follow-up for stage '{node_id}'.\n\n"
        "CRITICAL: Your previous output failed validation because it was missing "
        "the required `<pixl_output>` envelope or had formatting errors.\n\n"
        "Validation errors:\n"
        f"{bullets}\n\n"
        f"{schema_guidance}"
        "You MUST return exactly one `<pixl_output>...</pixl_output>` block with valid JSON inside.\n\n"
        "Required format:\n"
        "```\n"
        "<pixl_output>\n"
        "{\n"
        '  "schema_version": "1.0",\n'
        '  "stage_id": "' + node_id + '",\n'
        '  "status": "ok",\n'
        '  "summary": ["what you did"],\n'
        '  "artifacts_written": [{"path": "...", "sha256": "...", "purpose": "..."}],\n'
        '  "included_sources": [],\n'
        '  "payload": {}\n'
        "}\n"
        "</pixl_output>\n"
        "```\n\n"
        "Rules:\n"
        "- Content inside <pixl_output> MUST be valid JSON.\n"
        "- status must be 'ok' or 'error'.\n"
        "- summary must have 1-10 bullets.\n"
        "- artifacts_written lists files you created/modified with their sha256 hashes.\n"
        "- If unsure, use empty arrays/objects for optional fields.\n\n"
        f"{artifact_fix_guidance}"
        "Fix ONLY the listed violations. Keep the task scope unchanged.\n\n"
        "Previous output:\n"
        "```text\n"
        f"{excerpt}\n"
        "```"
    )

def build_structured_output_repair_prompt(
    *,
    node_id: str,
    validation_errors: list[str],
    previous_output: str,
    output_schema_path: str | None = None,
) -> str:
    """Build a strict one-shot repair prompt for malformed structured output."""
    excerpt = previous_output[-8000:] if len(previous_output) > 8000 else previous_output
    bullets = "\n".join(f"- {err}" for err in validation_errors[:20])
    schema_guidance = _build_schema_contract_guidance(output_schema_path)
    return (
        f"Repair the structured output for stage '{node_id}'.\n\n"
        "Return EXACTLY one `<pixl_output>...</pixl_output>` block.\n"
        "Do not include explanations, code fences, or any text before/after the envelope.\n\n"
        "Validation errors to fix:\n"
        f"{bullets}\n\n"
        f"{schema_guidance}"
        "Required shape:\n"
        "```\n"
        "<pixl_output>\n"
        "{\n"
        '  "schema_version": "1.0",\n'
        f'  "stage_id": "{node_id}",\n'
        '  "status": "ok",\n'
        '  "summary": ["..."],\n'
        '  "artifacts_written": [],\n'
        '  "included_sources": [],\n'
        '  "payload": {}\n'
        "}\n"
        "</pixl_output>\n"
        "```\n\n"
        "Previous output excerpt (for correction only):\n"
        "```text\n"
        f"{excerpt}\n"
        "```"
    )

def _build_schema_contract_guidance(output_schema_path: str | None) -> str:
    """Build a compact schema-derived payload contract section."""
    if not output_schema_path:
        return ""
    section = render_payload_contract_from_path(
        output_schema_path,
        heading="## Schema-Derived Payload Contract",
    )
    if not section:
        return ""
    return section + "\n\n"

def resolve_template_string(template: str, variables: dict[str, str]) -> str:
    """Resolve {{var}} and {var} patterns with iterative passes for nesting.

    Handles nested variables like:
        {{decomposition_file}} -> docs/epics/{{epic_id}}.decomposition.md
                               -> docs/epics/epic-001.decomposition.md
    """
    result = template

    # Iterative resolution for nested variables (max 3 passes)
    for _ in range(3):
        prev = result

        def _replace_double(m: re.Match) -> str:
            var_name = m.group(1)
            return str(variables.get(var_name, m.group(0)))

        result = re.sub(r"\{\{(\w+)\}\}", _replace_double, result)

        def _replace_single(m: re.Match) -> str:
            var_name = m.group(1)
            return str(variables.get(var_name, m.group(0)))

        result = re.sub(r"\{(\w+)\}", _replace_single, result)

        if result == prev:
            break  # No more substitutions possible

    return result

def build_contract_variables(
    node_id: str,
    *,
    session: WorkflowSession,
    snapshot: WorkflowSnapshot,
    project_root: Path,
    artifacts_dir: Path,
    pixl_dir: Path,
    get_stage_config: Any,
    workspace_root: Path | None = None,
) -> dict[str, str]:
    """Build complete variables dictionary for contract/output resolution.

    Merges variables from all sources in priority order (lowest to highest):
    1. Context variables (feature_id, session_id, workflow_id)
    2. Workflow global variables
    3. Workflow parameters
    4. Stage-specific prompt_vars (includes block variables after expansion)
    """
    variables: dict[str, str] = {}

    # Context variables
    variables["feature_id"] = session.feature_id or ""
    variables["session_id"] = session.id or ""
    variables["workflow_id"] = snapshot.template_id or ""
    # Use workspace_root (the real project directory) for the {{project_root}}
    # template variable so prompts reference the actual project, not the
    # standalone storage dir.
    variables["project_root"] = str(workspace_root or project_root)
    variables["artifacts_dir"] = str(artifacts_dir)
    variables["pixl_dir"] = str(pixl_dir)

    # Provide epic_id/roadmap_id aliases based on feature_id prefix
    fid = session.feature_id or ""
    if fid.startswith("epic-"):
        variables["epic_id"] = fid
    elif fid.startswith("roadmap-"):
        variables["roadmap_id"] = fid

    # Workflow global variables
    if snapshot.workflow_config:
        global_vars = snapshot.workflow_config.get("variables", {})
        if global_vars:
            variables.update({str(k): str(v) for k, v in global_vars.items()})

    # Workflow parameters (may be a list of param defs or a dict of values)
    if snapshot.workflow_config:
        parameters = snapshot.workflow_config.get("parameters", {})
        if isinstance(parameters, dict):
            variables.update({str(k): str(v) for k, v in parameters.items()})
        elif isinstance(parameters, list):
            for param in parameters:
                if isinstance(param, dict) and "id" in param and "default" in param:
                    variables.setdefault(str(param["id"]), str(param["default"]))

    # Stage-specific prompt_vars (includes block variables after expansion)
    stage_config = get_stage_config(node_id)
    prompt_vars = stage_config.get("prompt_vars", {})
    if prompt_vars:
        variables.update({str(k): str(v) for k, v in prompt_vars.items()})

    return variables

def resolve_contract_data(
    contract_data: dict,
    node_id: str,
    *,
    build_variables: Any,
) -> dict:
    """Resolve template variables in contract data."""
    resolved = copy.deepcopy(contract_data)
    variables = build_variables(node_id)

    if "must_write" in resolved:
        resolved["must_write"] = [
            resolve_template_string(p, variables) for p in resolved["must_write"]
        ]

    if "must_include_sections" in resolved:
        resolved["must_include_sections"] = {
            resolve_template_string(k, variables): v
            for k, v in resolved["must_include_sections"].items()
        }

    if "must_update_files" in resolved:
        resolved["must_update_files"] = [
            resolve_template_string(p, variables) for p in resolved["must_update_files"]
        ]

    if "artifact_schemas" in resolved:
        resolved["artifact_schemas"] = {
            resolve_template_string(k, variables): resolve_template_string(v, variables)
            for k, v in resolved["artifact_schemas"].items()
        }

    return resolved

def build_frozen_context(
    *,
    frozen_artifacts: dict[str, str],
    artifacts_dir: Path,
    project_root: Path,
    emit_error_event: Any | None = None,
) -> str:
    """Build frozen artifact context for prompt injection."""
    if not frozen_artifacts:
        return ""

    from pixl.errors import StorageError

    lines = [
        "",
        "## Frozen Specifications (DO NOT MODIFY)",
        "",
        "The following were approved and frozen. Reference them as immutable truth.",
        "",
    ]

    for path, sha in frozen_artifacts.items():
        lines.append(f"### {path} (frozen, hash: {sha[:12]}...)")

        # Include first 20 lines as excerpt
        resolved = artifacts_dir / path
        if not resolved.exists():
            resolved = project_root / path

        if resolved.exists():
            try:
                content = resolved.read_text(encoding="utf-8")
                excerpt_lines = content.splitlines()[:20]
                for el in excerpt_lines:
                    lines.append(f"> {el}")
                if len(content.splitlines()) > 20:
                    lines.append("> ...")
            except Exception as exc:
                if emit_error_event:
                    emit_error_event(
                        StorageError(
                            "Failed to read frozen artifact",
                            op="read_frozen_artifact",
                            details=str(exc),
                            metadata={"path": str(resolved)},
                            cause=exc,
                        ),
                        node_id=None,
                    )
                lines.append("> (could not read file)")
        else:
            lines.append("> (file not found)")

        lines.append("")

    return "\n".join(lines)

def build_change_request_context(
    node: Node,
    *,
    stage_configs: dict[str, dict[str, Any]],
    artifacts_dir: Path,
    build_variables: Any,
) -> str:
    """Build change request context for prompt injection."""
    stage_config = stage_configs.get(node.id, {})
    target = stage_config.get("change_request_target")
    if not target:
        return ""

    target_config = stage_configs.get(target, {})
    variables = build_variables(target)
    exempt_paths = [
        resolve_template_string(p, variables) for p in target_config.get("freeze_artifacts", [])
    ]

    lines = [
        "",
        "## Change Request",
        "",
        "You MAY modify the following frozen artifacts:",
        "",
    ]
    for path in exempt_paths:
        lines.append(f"- `{path}`")

    lines.extend(
        [
            "",
            "Write the change request using:",
            '`pixl artifact put --name change_request.md --content "..."`',
            "Your changes require gate approval to take effect.",
            "",
        ]
    )

    return "\n".join(lines)

def write_rejection_feedback(
    gate_id: str,
    *,
    store: WorkflowSessionStore,
    session: WorkflowSession,
    snapshot: WorkflowSnapshot,
    artifacts_dir: Path,
) -> None:
    """Write gate rejection feedback to artifact file.

    For review gates, includes the code review artifacts (structured output
    issues + review.md) so the implementer has full context on what to fix.
    """
    from pixl.models.event import EventType

    reason = None
    events = store.load_events(session.id)
    for event in reversed(events):
        if event.type == EventType.GATE_REJECTED and event.node_id == gate_id:
            reason = event.data.get("reason")
            break

    if not reason:
        reason = "No specific reason provided."

    gate_node = snapshot.graph.nodes.get(gate_id)
    gate_name = gate_node.gate_config.name if gate_node and gate_node.gate_config else gate_id

    feedback_name = f"rejection-feedback-{gate_id}.md"

    parts = [
        f"# Gate Rejection Feedback: {gate_name}\n",
        "The previous output was reviewed and rejected.\n",
        f"## Rejection Reason\n\n{reason}\n",
        "Please address this feedback and revise your output accordingly.\n",
    ]

    # For review gates, include the code review context so the implementer
    # knows exactly what needs fixing (the human rejects, the review explains).
    _append_predecessor_review_context(
        gate_id,
        parts,
        session=session,
        snapshot=snapshot,
        artifacts_dir=artifacts_dir,
        store=store,
    )
    store.save_artifact(session.id, feedback_name, "\n".join(parts))

def _append_predecessor_review_context(
    gate_id: str,
    parts: list[str],
    *,
    session: WorkflowSession,
    snapshot: WorkflowSnapshot,
    artifacts_dir: Path,
    store: WorkflowSessionStore | None = None,
) -> None:
    """Append code review context from predecessor review stages.

    Walks the gate's predecessors to find review stages (automated-checks,
    code-review) and includes their structured output issues + artifacts.
    """
    predecessors: list[str] = []
    for source_id, edge_list in snapshot.graph.edges.items():
        for edge in edge_list:
            if edge.to == gate_id:
                predecessors.append(source_id)

    # Include structured output issues from review predecessors
    for pred_id in predecessors:
        structured = session.structured_outputs.get(pred_id)
        if not structured:
            continue
        payload = structured.get("payload", {})
        issues = payload.get("issues", [])
        if not issues:
            continue

        recommendation = payload.get("recommendation", "unknown")
        parts.append(f"## Code Review ({pred_id}): {recommendation}\n")
        for i, issue in enumerate(issues, 1):
            severity = issue.get("severity", "unknown")
            desc = issue.get("description", "")
            file_path = issue.get("file", "")
            suggestion = issue.get("suggestion", "")
            parts.append(f"### {i}. [{severity.upper()}] {desc}")
            if file_path:
                parts.append(f"- File: `{file_path}`")
            if suggestion:
                parts.append(f"- Suggestion: {suggestion}")
            parts.append("")

    # Include the review artifact if it exists
    content: str | None = None
    if store is not None:
        content = store.load_artifact(session.id, "review.md")
    else:
        review_artifact = artifacts_dir / "review.md"
        if review_artifact.exists():
            content = review_artifact.read_text()

    if content:
        if len(content) > 8000:
            content = content[:8000] + "\n\n... (truncated, see full review at review.md)"
        parts.append("## Full Review\n")
        parts.append(content)

def write_auto_review_feedback(
    review_node_id: str,
    *,
    session: WorkflowSession,
    artifacts_dir: Path,
    store: WorkflowSessionStore | None = None,
) -> None:
    """Write auto-review feedback artifact from structured output."""
    feedback_name = f"auto-review-feedback-{review_node_id}.md"

    parts = [f"# Auto-Review Feedback: {review_node_id}\n"]
    parts.append("The reviewer requested changes. Address the issues below.\n")

    structured = session.structured_outputs.get(review_node_id)
    if structured:
        payload = structured.get("payload", {})
        recommendation = payload.get("recommendation", "unknown")
        parts.append(f"## Recommendation: {recommendation}\n")

        issues = payload.get("issues", [])
        if issues:
            parts.append("## Issues\n")
            for i, issue in enumerate(issues, 1):
                severity = issue.get("severity", "unknown")
                desc = issue.get("description", "")
                file_path = issue.get("file", "")
                suggestion = issue.get("suggestion", "")
                parts.append(f"### {i}. [{severity.upper()}] {desc}")
                if file_path:
                    parts.append(f"- File: `{file_path}`")
                if suggestion:
                    parts.append(f"- Suggestion: {suggestion}")
                parts.append("")

    review_content: str | None = None
    if store is not None:
        review_content = store.load_artifact(session.id, "review.md")
    else:
        review_artifact = artifacts_dir / "review.md"
        if review_artifact.exists():
            review_content = review_artifact.read_text()

    if review_content:
        content = review_content
        if len(content) > 8000:
            content = content[:8000] + "\n\n... (truncated, see full review at review.md)"
        parts.append("## Full Review\n")
        parts.append(content)

    if store is not None:
        store.save_artifact(session.id, feedback_name, "\n".join(parts))
    else:
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        feedback_path = artifacts_dir / feedback_name
        feedback_path.write_text("\n".join(parts))

def build_rejection_feedback_context(
    node: Node,
    *,
    snapshot: WorkflowSnapshot,
    artifacts_dir: Path,
    store: WorkflowSessionStore | None = None,
    session_id: str | None = None,
) -> str:
    """Build rejection feedback context for revision passes."""
    for constraint in snapshot.graph.loop_constraints:
        if constraint.to_node != node.id:
            continue

        from_id = constraint.from_node

        # Gate rejection feedback (failure trigger)
        if constraint.edge_trigger.value == "failure":
            feedback_name = f"rejection-feedback-{from_id}.md"
            feedback = None
            if store is not None and session_id:
                feedback = store.load_artifact(session_id, feedback_name)
            else:
                feedback_path = artifacts_dir / feedback_name
                if feedback_path.exists():
                    feedback = feedback_path.read_text()
            if feedback:
                return (
                    "\n## Revision Pass\n\n"
                    "This is a revision pass. Your previous output was rejected at a review gate.\n"
                    f"Read the full feedback at: {feedback_name}\n\n"
                    f"{feedback}\n"
                )

        # Auto-review feedback (condition trigger)
        if constraint.edge_trigger.value == "condition":
            feedback_name = f"auto-review-feedback-{from_id}.md"
            feedback = None
            if store is not None and session_id:
                feedback = store.load_artifact(session_id, feedback_name)
            else:
                feedback_path = artifacts_dir / feedback_name
                if feedback_path.exists():
                    feedback = feedback_path.read_text()
            if feedback:
                return (
                    "\n## Revision Pass (Auto-Review)\n\n"
                    "This is a revision pass. The automated review requested changes.\n"
                    f"Read the full feedback at: {feedback_name}\n\n"
                    f"{feedback}\n"
                )

    return ""

def load_feature_context(
    *,
    session: WorkflowSession,
    project_root: Path,
    snapshot: WorkflowSnapshot,
    node_id: str | None = None,
) -> tuple[str, str]:
    """Load feature title and description, failing fast on data corruption."""
    from pixl.errors import StateError
    from pixl.storage import BacklogStore

    feature = None
    load_exc = None
    try:
        backlog_store = BacklogStore(project_root)
        feature = backlog_store.get_feature(session.feature_id)
    except Exception as exc:
        load_exc = exc

    if feature:
        return feature.title, feature.description

    # Feature load failed or returned None — check if data corruption
    if load_exc is not None:
        try:
            backlog_store_raw = BacklogStore(project_root)
            raw = backlog_store_raw._store.get_feature(session.feature_id)
            if raw and raw.get("description"):
                raise StateError(
                    f"Feature {session.feature_id} has a description in the database "
                    f"but could not be loaded through the model layer. "
                    f"This indicates data corruption — refusing to proceed with empty context. "
                    f"Original error: {load_exc}",
                    invariant="feature_data_integrity",
                    details=str(load_exc),
                    metadata={"feature_id": session.feature_id, "node_id": node_id},
                )
        except StateError:
            raise
        except Exception:
            pass

    # Legitimately empty or missing — fall back to workflow params
    workflow_params = snapshot.workflow_config.get("parameters", {})
    feature_title = session.feature_id
    feature_description = ""

    if "project_name" in workflow_params:
        feature_title = workflow_params["project_name"]
    elif "project_description" in workflow_params:
        feature_description = workflow_params["project_description"]

    return feature_title, feature_description

def resolve_output_schema_path(
    schema_ref: str | None,
    *,
    pixl_dir: Path,
) -> str | None:
    """Resolve an output schema reference to a file path."""
    if not schema_ref:
        return None

    # 1. Project-level
    project_schema = pixl_dir / "schemas" / schema_ref
    if project_schema.exists():
        return str(project_schema)

    # 2. Bundled assets
    assets_dir = Path(__file__).parent.parent / "assets" / "schemas"
    bundled_schema = assets_dir / schema_ref
    if bundled_schema.exists():
        return str(bundled_schema)

    return None

def initialize_baton(
    node: Node,
    *,
    session: WorkflowSession,
    project_root: Path,
    snapshot: WorkflowSnapshot,
    feature_title: str | None = None,
    feature_description: str | None = None,
) -> None:
    """Initialize the baton for a new workflow session."""
    from pixl.models.baton import Baton

    if feature_title is None:
        feature_title, feature_description = load_feature_context(
            session=session,
            project_root=project_root,
            snapshot=snapshot,
            node_id=node.id,
        )

    if feature_description:
        baton = Baton.from_feature(feature_title, feature_description)
    else:
        baton = Baton(
            goal=feature_title,
            current_state=["Workflow starting"],
        )

    session.baton = baton.model_dump()

def build_unified_prompt(
    node: Node,
    *,
    session: WorkflowSession,
    snapshot: WorkflowSnapshot,
    project_root: Path,
    artifacts_dir: Path,
    pixl_dir: Path,
    stage_configs: dict[str, dict[str, Any]],
    summarizer: Any | None = None,
    differ: Any | None = None,
    workspace_root: Path | None = None,
    store: WorkflowSessionStore | None = None,
    artifact_handoff_manifest: list[dict[str, Any]] | None = None,
) -> str:
    """Build prompt using the unified context compiler.

    Args:
        summarizer: Optional shared ArtifactSummarizer (avoids per-stage re-creation).
        differ: Optional shared ArtifactDiffer (avoids per-stage re-creation).
        workspace_root: Actual project directory (may differ from storage-based
            project_root in standalone mode). Used for the {{project_root}}
            template variable so prompts reference the real project.
    """
    from pixl.models.baton import Baton
    from pixl.prompts.resolver import PromptContext, PromptTemplateResolver

    stage_config = stage_configs.get(node.id, {})

    feature_title, feature_description = load_feature_context(
        session=session,
        project_root=project_root,
        snapshot=snapshot,
        node_id=node.id,
    )

    if session.baton is None:
        initialize_baton(
            node,
            session=session,
            project_root=project_root,
            snapshot=snapshot,
            feature_title=feature_title,
            feature_description=feature_description,
        )

    # Use workspace_root for template variables so {{project_root}} points to
    # the actual project directory, not the standalone storage dir.
    prompt_root = workspace_root or project_root

    baton = Baton.from_dict(session.baton)
    context = PromptContext(
        workflow_id=snapshot.template_id,
        workflow_name=snapshot.name,
        feature_id=session.feature_id,
        feature_title=feature_title,
        feature_description=feature_description,
        session_id=session.id,
        stage_id=node.id,
        project_root=prompt_root,
        artifacts_dir=artifacts_dir,
        pixl_dir=pixl_dir,
    )

    global_vars = {}
    parameters = {}
    if snapshot.workflow_config:
        global_vars = snapshot.workflow_config.get("variables", {})
        parameters = snapshot.workflow_config.get("_resolved_parameters", {})

    resolver = PromptTemplateResolver(project_root)
    base_prompt = resolver.resolve_stage_prompt(
        stage_config=stage_config,
        context=context,
        global_vars=global_vars,
        parameters=parameters,
    )

    # Plugin mode: plugin handles RAG, CLAUDE.md, agent routing natively.
    # We only provide: task instructions + baton + predecessors + contracts.
    import json as _json

    parts = [base_prompt]

    # Baton context
    baton_text = baton.to_prompt_section()
    if baton_text:
        parts.append(f"## Workflow State\n\n{baton_text}")

    # Predecessor outputs
    for pred_id in snapshot.graph.get_predecessors(node.id):
        pred_node = snapshot.graph.nodes.get(pred_id)
        if pred_node and pred_node.type != "task":
            continue
        pred_data = session.structured_outputs.get(pred_id)
        if pred_data:
            parts.append(
                f"## Output from `{pred_id}`\n\n```json\n"
                f"{_json.dumps(pred_data, indent=2, default=str)[:4000]}\n```"
            )

    # Output contract
    contract = stage_config.get("contract")
    if contract:
        parts.append(f"## Output Contract\n\n```json\n{_json.dumps(contract, indent=2)}\n```")

    # Artifact manifest
    if artifact_handoff_manifest:
        parts.append(
            f"## Available Artifacts\n\n```json\n"
            f"{_json.dumps(artifact_handoff_manifest, indent=2, default=str)}\n```"
        )

    # Rejection feedback (needed for loop retries)
    rejection_context = build_rejection_feedback_context(
        node,
        snapshot=snapshot,
        artifacts_dir=artifacts_dir,
        store=store,
        session_id=session.id,
    )
    if rejection_context:
        parts.append(rejection_context)

    # Envelope instructions — ensures plugin/CLI path produces <pixl_output> tags
    from pixl.context.unified_compiler import UnifiedContextCompiler

    parts.append(UnifiedContextCompiler._build_envelope_instructions(stage_id=node.id))

    return "\n\n".join(parts)

def _build_cli_tools_context(stage_config: dict[str, Any]) -> str:
    """Build CLI tools reference based on stage capabilities."""
    tools_doc = []

    tools_doc.append("""
### Artifact Management

> **⚠️ CRITICAL: You MUST use `pixl artifact put` to register every artifact.**
> Writing files with `write_file` or filesystem operations does NOT register them
> in the session artifact store. Validation WILL FAIL if artifacts are written
> to disk but not registered via `pixl artifact put`.

**Commands:**
- `pixl artifact put --name <filename> --content <string>`
  Persist a workflow artifact and return its SHA256 hash.
  Use `--json` for machine-readable output: `{"name": "...", "sha256": "..."}`.
- `pixl artifact get --name <filename>`
  Read an artifact by logical session path.
- `pixl artifact get --name <filename> --json`
  Read an artifact with machine-safe JSON: `{"name","session_id","sha256","content"}`.
- `pixl artifact list`
  List session artifacts and versions.
- `pixl artifact search --query <text>`
  Full-text search over session artifacts.

**Example — saving a file as an artifact:**
```bash
# WRONG: This only writes to disk, artifact store does NOT see it:
write_file(path="plan.md", content="# My Plan...")

# CORRECT: Use pixl artifact put (via run_shell_command if needed):
pixl artifact put --name plan.md --content "$(cat plan.md)"
# Output includes SHA256 hash, e.g.: Artifact 'plan.md' saved ... (sha256: abc123...)

# MACHINE-READABLE: Use --json to get the hash programmatically:
pixl artifact put --name plan.md --content "$(cat plan.md)" --json
# {"name": "plan.md", "session_id": "sess-xxx", "sha256": "abc123..."}
```

Use `pixl artifact put` for EVERY file listed in your `artifacts_written` output.
The SHA256 hash is returned by the command — no need to compute it manually.
""")

    if not tools_doc:
        return ""

    return "\n".join(
        [
            "",
            "## Available CLI Tools",
            "You have access to the following Pixl CLI tools:",
            *tools_doc,
            "",
        ]
    )

def _auto_build_knowledge_index(index: Any, project_root: Path) -> None:
    """Auto-build RAG knowledge index if project has source files.

    Only builds if the project has indexable files (docs, CLAUDE.md, etc.).
    Tree-sitter parsing is fast (~2-5s for typical projects) so this is
    safe to call during prompt building.
    """
    try:
        source_files = index._collect_source_files(include_code=True)
        if not source_files:
            return
        chunks_created, files_processed = index.build(include_code=True)
        if chunks_created > 0:
            logger.info(
                "Auto-built knowledge index: %d chunks from %d files",
                chunks_created,
                files_processed,
            )
    except Exception:
        logger.debug("Auto-build knowledge index failed", exc_info=True)

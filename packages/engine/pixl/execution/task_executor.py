"""Orchestrator execution pipeline for workflow tasks.

Extracted from graph_executor.py — handles the SDK query loop with
validation retries, structured output parsing, contract checking,
baton patching, and console streaming.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pixl.errors import ProviderError
from pixl.execution.baton_handler import apply_baton_patch, persist_progress_artifact
from pixl.execution.node_state import update_node_instance_metadata, workflow_max_attempts
from pixl.execution.prompt_builder import (
    build_structured_output_repair_prompt,
    build_validation_followup_prompt,
    resolve_output_schema_path,
)
from pixl.execution.review_validator import (
    get_default_review_output,
    is_review_stage,
    validate_review_structured_output,
)
from pixl.models.event import Event, EventType
from pixl.models.node_instance import NodeState
from pixl.utils.async_compat import run_coroutine_sync as _run_coroutine_sync

if TYPE_CHECKING:
    from pixl.models.workflow import Node

    from .graph_executor import GraphExecutor

logger = logging.getLogger(__name__)

STRUCTURED_OUTPUT_REPAIR_ATTEMPTS = 1
RAW_OUTPUT_EXCERPT_CHARS = 20_000

def _estimate_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    """Estimate USD cost from token counts using config-loaded model pricing.

    Loads pricing from packages/engine/pixl/config/pricing.yaml (cached).
    Falls back to $0 with a WARNING log when the model is not found.
    """
    from pixl.config.providers import load_model_pricing

    pricing = load_model_pricing()
    for key, (inp_rate, out_rate) in pricing.items():
        if key in model:
            return (input_tokens * inp_rate + output_tokens * out_rate) / 1_000_000

    logger.warning(
        "No pricing data for model %r — cost will be reported as $0. "
        "Add the model to packages/engine/pixl/config/pricing.yaml.",
        model,
    )
    return 0.0


def execute_with_orchestrator(
    executor: GraphExecutor,
    node: Node,
    instance: dict,
    *,
    effective_model: str | None = None,
    artifact_handoff_manifest: list[dict[str, Any]] | None = None,
) -> dict:
    """Execute task using orchestrator SDK with streaming output.

    Args:
        executor: GraphExecutor instance
        node: Node definition
        instance: Node instance
        effective_model: Pre-resolved model name (avoids redundant resolution)

    Returns:
        Execution result
    """
    from pixl.output import console, is_json_mode

    events: list[Event] = []
    task_config = node.task_config

    prompt = executor._build_task_prompt(
        node,
        artifact_handoff_manifest=artifact_handoff_manifest,
    )

    # Use pre-resolved model (from _resolve_agent_and_model via _execute_task)
    stage_model = effective_model or (task_config.model or "claude-sonnet-4-6")

    workflow_tags = None
    if executor.snapshot.workflow_config:
        workflow_tags = executor.snapshot.workflow_config.get("tags", []) or None

    stage_cfg = executor._stage_configs.get(node.id, {})
    output_schema = stage_cfg.get("output_schema")
    output_schema_path = (
        resolve_output_schema_path(output_schema, pixl_dir=executor.pixl_dir)
        if output_schema
        else None
    )
    required_artifact_paths = [
        str(entry.get("path", "")).strip()
        for entry in (artifact_handoff_manifest or [])
        if str(entry.get("path", "")).strip()
    ]
    structured_warnings: list[str] = []
    # Unified mode always uses structured output
    expects_structured = True

    # Only for SDK providers (Anthropic) — external providers use envelope.
    sdk_output_format = _build_stage_output_format()
    max_attempts = workflow_max_attempts(executor.snapshot)

    # Keep retries in the same conversation when SDK session IDs are available.
    llm_session_id = (instance or {}).get("llm_session_id")
    # Detect session resume: node ran before (has llm_session_id) and was
    # reset to pending with attempt incremented by unblock_tasks_for_resume.
    # Note: this is logically covered by is_revision_pass below (both check
    # attempt > 0), but kept as an explicit named flag for clarity of intent.
    is_session_resume = bool(llm_session_id) and (instance or {}).get("attempt", 0) > 0
    current_prompt = prompt

    fork_from_session_id: str | None = None
    if stage_cfg.get("fork_session"):
        for pred_id in executor.snapshot.graph.get_predecessors(node.id):
            pred_instance = executor.session.get_node_instance(pred_id)
            if pred_instance and pred_instance.get("llm_session_id"):
                fork_from_session_id = pred_instance["llm_session_id"]
                break

    executor.orchestrator.set_sdk_event_callback(
        callback=executor._persist_event,
        session_id=executor.session.id,
        node_id=node.id,
    )

    try:
        for validation_attempt in range(max_attempts):
            # Resume conversation on validation retries, revision passes,
            # or session resume (node re-entered after pause/crash with
            # its llm_session_id preserved).
            is_revision_pass = (instance or {}).get("attempt", 0) > 0
            resume_conversation = (
                validation_attempt > 0 or is_revision_pass or is_session_resume
            ) and bool(llm_session_id)
            # Compact session context before retries to reclaim token budget
            if resume_conversation and llm_session_id:
                try:
                    compact_options = executor.orchestrator._build_query_options(
                        max_turns=1,
                        resume_session_id=llm_session_id,
                        continue_conversation=True,
                    )
                    _run_coroutine_sync(
                        executor.orchestrator.send_session_command(
                            "/compact", options=compact_options
                        )
                    )
                except Exception:
                    logger.debug("Session compact before retry failed", exc_info=True)

            # Prepend a compact envelope reminder that survives context compaction
            _envelope_reminder = (
                "IMPORTANT: You MUST wrap your final result in "
                "<pixl_output>...</pixl_output> tags containing valid JSON "
                "conforming to the StageOutput schema. "
                "Your response is invalid without this envelope.\n\n"
            )
            query_kwargs: dict[str, Any] = {
                "prompt": _envelope_reminder + current_prompt,
                "model": stage_model,
                "max_turns": task_config.max_turns,
                "feature_id": executor.session.feature_id,
                "stream_callback": stream_message_to_console if not is_json_mode() else None,
                "workflow_tags": workflow_tags,
                "stage_id": node.id,
                "agent_name": task_config.agent,
                "extra_writable_dirs": _provider_writable_dirs(executor),
                "session_id": executor.session.id,
                "storage_project": str(executor.project_root),
                "cwd": executor._workspace_root,
                "artifacts_dir": str(executor.artifacts_dir),
            }

            # Inject error context from previous failed attempt so the LLM
            # can adjust its approach (prevents "groundhog day" retries).
            last_error = (instance or {}).get("last_error")
            if last_error and (instance or {}).get("attempt", 0) > 0:
                error_excerpt = str(last_error)[:2000]
                error_context = (
                    f"\n\n## IMPORTANT: Previous Attempt Failed\n"
                    f"Your previous attempt failed with this error:\n"
                    f"```\n{error_excerpt}\n```\n"
                    f"Adjust your approach to avoid this error. "
                    f"If a file edit failed, re-read the file first to get "
                    f"current contents before attempting the edit again."
                )
                query_kwargs["prompt"] = current_prompt + error_context

            # Phase 4B: Look up adapter session for resume
            if hasattr(executor, "db") and executor.db:
                task_session = executor.db.task_sessions.get_task_session(
                    executor.session.id, f"{node.id}:{(instance or {}).get('attempt', 0)}"
                )
                if task_session and task_session.get("adapter_session_id"):
                    adapter_session_id = task_session["adapter_session_id"]
                    if not llm_session_id and not resume_conversation:
                        query_kwargs["resume_session_id"] = adapter_session_id
                        query_kwargs["continue_conversation"] = True
                        resume_conversation = True

            # Pass native output_format for SDK-based structured output
            if sdk_output_format:
                query_kwargs["output_format"] = sdk_output_format
            if resume_conversation and "resume_session_id" not in query_kwargs:
                # Only set if not already set by adapter session lookup above
                query_kwargs["resume_session_id"] = llm_session_id
                query_kwargs["continue_conversation"] = True
            elif not resume_conversation and (instance or {}).get("provider_session_id"):
                # External provider session resume (e.g. Gemini CLI --resume)
                query_kwargs["resume_session_id"] = instance["provider_session_id"]
            elif fork_from_session_id and validation_attempt == 0:
                # Fork from predecessor session on first attempt (cross-stage context)
                query_kwargs["resume_session_id"] = fork_from_session_id
                query_kwargs["fork_session"] = True

            result_text, metadata = _run_coroutine_sync(
                executor.orchestrator.query_with_streaming(**query_kwargs)
            )

            if metadata.get("sdk_session_id"):
                llm_session_id = metadata["sdk_session_id"]
                update_node_instance_metadata(
                    executor.session, node.id, llm_session_id=llm_session_id
                )
            if metadata.get("provider_session_id"):
                update_node_instance_metadata(
                    executor.session,
                    node.id,
                    provider_session_id=metadata["provider_session_id"],
                )
            # Phase 4B: Persist adapter session state
            if hasattr(executor, "db") and executor.db and metadata.get("sdk_session_id"):
                executor.db.task_sessions.upsert_task_session(
                    session_id=executor.session.id,
                    node_id=node.id,
                    task_key=f"{node.id}:{(instance or {}).get('attempt', 0)}",
                    adapter_name=metadata.get("provider", "claude_sdk"),
                    adapter_session_id=metadata["sdk_session_id"],
                    last_run_id=getattr(executor, "_current_run_id", None),
                )

            # SDK sessions can expire between attempts. If resume fails, retry
            # once stateless within the same validation attempt.
            if (
                resume_conversation
                and not metadata.get("success")
                and is_resume_session_error(str(metadata.get("error", "")))
            ):
                llm_session_id = None
                retry_instance = executor.session.get_node_instance(node.id)
                if retry_instance:
                    retry_instance.pop("llm_session_id", None)

                fallback_kwargs = dict(query_kwargs)
                fallback_kwargs.pop("resume_session_id", None)
                fallback_kwargs.pop("continue_conversation", None)

                result_text, metadata = _run_coroutine_sync(
                    executor.orchestrator.query_with_streaming(**fallback_kwargs)
                )
                if metadata.get("sdk_session_id"):
                    llm_session_id = metadata["sdk_session_id"]
                    update_node_instance_metadata(
                        executor.session, node.id, llm_session_id=llm_session_id
                    )

            if not metadata.get("success"):
                error = metadata.get("error", "Unknown error")

                # Partial success recognition: if the agent already emitted
                # a valid structured output before the provider died, treat
                # the stage as successful rather than failing the whole
                # session (e.g. API outage after work was already done).
                if result_text:
                    from pixl.execution.envelope import extract_envelope as _extract_env

                    partial_output, _env_err = _extract_env(result_text)
                    if partial_output is not None and partial_output.status == "ok":
                        logger.info(
                            "partial_recovery.provider_error_but_output_valid",
                            extra={
                                "node_id": node.id,
                                "stage_id": partial_output.stage_id,
                                "error": error,
                            },
                        )
                        executor._persist_event(
                            Event.create(
                                EventType.RECOVERY_SUCCEEDED,
                                executor.session.id,
                                node_id=node.id,
                                data={
                                    "recovery_type": "partial_recovery",
                                    "provider_error": str(error),
                                },
                            )
                        )
                        # Fall through to normal validation — metadata is
                        # patched so downstream code treats this as success.
                        metadata["success"] = True
                    else:
                        if not is_json_mode():
                            console.error(f"Task error: {error}")

                        executor._emit_error_event(
                            ProviderError(
                                error,
                                provider="orchestrator",
                                model=task_config.model if task_config else None,
                            ),
                            node_id=node.id,
                        )

                        return executor._make_failure_result(
                            error,
                            failure_kind="transient",
                            error_type="provider_error",
                            events=events,
                        )
                else:
                    if not is_json_mode():
                        console.error(f"Task error: {error}")

                    executor._emit_error_event(
                        ProviderError(
                            error,
                            provider="orchestrator",
                            model=task_config.model if task_config else None,
                        ),
                        node_id=node.id,
                    )

                    return executor._make_failure_result(
                        error,
                        failure_kind="transient",
                        error_type="provider_error",
                        events=events,
                    )

            validation_errors: list[str] = []
            validation_kind: str | None = None
            stage_output = None

            # Structured output validation (deterministic)
            if expects_structured:
                from pixl.execution.envelope import extract_envelope

                # Prefer SDK native structured_output (already validated by schema)
                stage_output = None
                envelope_error = None
                sdk_structured = metadata.get("structured_output")
                if sdk_structured is not None:
                    try:
                        from pixl.models.stage_output import StageOutput as _StageOutput

                        if isinstance(sdk_structured, dict):
                            stage_output = _StageOutput.model_validate(sdk_structured)
                        elif isinstance(sdk_structured, str):
                            import json as _json

                            stage_output = _StageOutput.model_validate(_json.loads(sdk_structured))
                    except Exception as so_err:
                        logger.debug(
                            "SDK structured_output parse failed, falling back to envelope: %s",
                            so_err,
                        )

                # Fall back to envelope extraction
                if stage_output is None:
                    stage_output, envelope_error = extract_envelope(result_text)

                # Third fallback: artifact-based stage output (Gemini CLI path)
                if stage_output is None:
                    _so_artifact_name = f"_stage_output/{node.id}.json"
                    try:
                        _so_raw = executor.store.load_artifact(
                            executor.session.id,
                            _so_artifact_name,
                        )
                        if _so_raw:
                            import json as _json_so

                            from pixl.models.stage_output import StageOutput as _StageOutput2

                            stage_output = _StageOutput2.model_validate(_json_so.loads(_so_raw))
                            logger.info(
                                "stage_output.from_artifact",
                                extra={"node_id": node.id, "artifact": _so_artifact_name},
                            )
                    except Exception as so_art_err:
                        logger.debug(
                            "Artifact-based stage output load failed: %s",
                            so_art_err,
                        )
                if stage_output is None:
                    validation_kind = (
                        "structured_output_invalid"
                        if envelope_error is not None
                        else "structured_output_missing"
                    )
                    message = (
                        envelope_error
                        if envelope_error is not None
                        else "Expected <pixl_output> envelope but none found in agent output"
                    )
                    validation_errors.append(message)
                    so_invalid_event = Event.structured_output_invalid(
                        executor.session.id,
                        node.id,
                        message,
                    )
                    events.append(so_invalid_event)
                    if not is_json_mode():
                        console.error(f"Structured output error: {message}")
                else:
                    # If the model asks clarification with recoverable error/input hints,
                    # treat it as missing-input recovery rather than formatting retry.
                    requested_inputs: set[str] = set()
                    if stage_output.next and stage_output.next.inputs_needed:
                        requested_inputs.update(
                            i for i in stage_output.next.inputs_needed if isinstance(i, str) and i
                        )
                    if stage_output.error and stage_output.error.details:
                        for key in ("missing_inputs", "inputs_needed"):
                            raw_values = stage_output.error.details.get(key)
                            if isinstance(raw_values, list):
                                requested_inputs.update(
                                    str(v) for v in raw_values if str(v).strip()
                                )
                    if (
                        requested_inputs
                        and stage_output.status == "error"
                        and stage_output.error
                        and stage_output.error.recoverable
                    ):
                        missing_inputs = sorted(requested_inputs)
                        missing_msg = (
                            stage_output.error.message
                            if stage_output.error.message
                            else f"Stage requested additional inputs: {', '.join(missing_inputs)}"
                        )
                        return executor._make_failure_result(
                            missing_msg,
                            failure_kind="missing_inputs",
                            events=events,
                            extra={"missing_inputs": missing_inputs},
                            extra_payload={"missing_inputs": missing_inputs},
                        )

                    struct_validator = executor._get_contract_validator()
                    struct_result = struct_validator.validate_structured_output(
                        stage_output,
                        output_schema_path,
                        required_artifacts=required_artifact_paths,
                    )
                    if struct_result.warning_messages:
                        structured_warnings.extend(struct_result.warning_messages)
                    if not struct_result.passed:
                        validation_kind = "schema_mismatch"
                        validation_errors.extend(struct_result.violation_messages)
                        error_msg = "; ".join(struct_result.violation_messages)
                        events.append(
                            Event.structured_output_invalid(
                                executor.session.id,
                                node.id,
                                error_msg,
                            )
                        )
                        if not is_json_mode():
                            console.error(f"Structured output validation failed: {error_msg}")

            # Post-execution contract validation
            contract_result = executor._validate_contract(node.id)
            if contract_result and not contract_result.passed:
                validation_kind = validation_kind or "contract_violation"
                validation_errors.extend(contract_result.violation_messages)
                events.append(
                    Event.contract_violation(
                        executor.session.id,
                        node.id,
                        violations=contract_result.violation_messages,
                    )
                )
                if not is_json_mode():
                    console.error(
                        "Contract violation: " + "; ".join(contract_result.violation_messages)
                    )

            if validation_errors:
                if validation_attempt + 1 < max_attempts:
                    current_prompt = build_validation_followup_prompt(
                        node_id=node.id,
                        validation_errors=validation_errors,
                        previous_output=result_text,
                        expects_structured=expects_structured,
                        attempt=validation_attempt + 1,
                        output_schema_path=output_schema_path,
                    )
                    events.append(
                        Event.contract_warning(
                            executor.session.id,
                            node.id,
                            f"Validation retry {validation_attempt + 1}/{max_attempts} requested.",
                        )
                    )
                    continue

                repair_attempted = False
                if (
                    expects_structured
                    and STRUCTURED_OUTPUT_REPAIR_ATTEMPTS > 0
                    and validation_kind
                    in {
                        "structured_output_invalid",
                        "structured_output_missing",
                        "schema_mismatch",
                    }
                ):
                    repair_attempted = True
                    events.append(
                        Event.contract_warning(
                            executor.session.id,
                            node.id,
                            "Structured output repair attempt 1/1 requested.",
                        )
                    )

                    repair_prompt = build_structured_output_repair_prompt(
                        node_id=node.id,
                        validation_errors=validation_errors,
                        previous_output=result_text,
                        output_schema_path=output_schema_path,
                    )
                    repair_kwargs = dict(query_kwargs)
                    repair_kwargs["prompt"] = repair_prompt

                    repair_text, repair_metadata = _run_coroutine_sync(
                        executor.orchestrator.query_with_streaming(**repair_kwargs)
                    )
                    if repair_metadata.get("sdk_session_id"):
                        llm_session_id = repair_metadata["sdk_session_id"]
                        update_node_instance_metadata(
                            executor.session,
                            node.id,
                            llm_session_id=llm_session_id,
                        )

                    if not repair_metadata.get("success"):
                        validation_errors.append(
                            "Structured output repair query failed: "
                            f"{repair_metadata.get('error', 'Unknown error')}"
                        )
                        events.append(
                            Event.contract_warning(
                                executor.session.id,
                                node.id,
                                "Structured output repair attempt failed.",
                            )
                        )
                    else:
                        from pixl.execution.envelope import extract_envelope

                        repair_errors: list[str] = []
                        repair_kind: str | None = None
                        repaired_output, repair_envelope_error = extract_envelope(repair_text)
                        if repaired_output is None:
                            repair_kind = (
                                "structured_output_invalid"
                                if repair_envelope_error is not None
                                else "structured_output_missing"
                            )
                            repair_errors.append(
                                repair_envelope_error
                                if repair_envelope_error is not None
                                else "Expected <pixl_output> envelope but none found in repair"
                            )
                        else:
                            struct_validator = executor._get_contract_validator()
                            struct_result = struct_validator.validate_structured_output(
                                repaired_output,
                                output_schema_path,
                                required_artifacts=required_artifact_paths,
                            )
                            if struct_result.warning_messages:
                                structured_warnings.extend(struct_result.warning_messages)
                            if not struct_result.passed:
                                repair_kind = "schema_mismatch"
                                repair_errors.extend(struct_result.violation_messages)

                        repaired_contract = executor._validate_contract(node.id)
                        if repaired_contract and not repaired_contract.passed:
                            repair_kind = repair_kind or "contract_violation"
                            repair_errors.extend(repaired_contract.violation_messages)

                        if repair_errors:
                            validation_errors = repair_errors
                            validation_kind = repair_kind or validation_kind
                            result_text = repair_text
                            metadata = repair_metadata
                            events.append(
                                Event.contract_warning(
                                    executor.session.id,
                                    node.id,
                                    "Structured output repair attempt failed.",
                                )
                            )
                        else:
                            validation_errors = []
                            validation_kind = None
                            result_text = repair_text
                            metadata = repair_metadata
                            stage_output = repaired_output
                            contract_result = repaired_contract
                            events.append(
                                Event.contract_warning(
                                    executor.session.id,
                                    node.id,
                                    "Structured output repair attempt succeeded.",
                                )
                            )

                if validation_errors:
                    error_msg = "; ".join(validation_errors)
                    error_type = (
                        "contract_error"
                        if validation_kind == "contract_violation" and not expects_structured
                        else "structured_output_error"
                    )
                    error_metadata = {
                        "validation_kind": validation_kind,
                        "attempts": validation_attempt + 1,
                        "max_attempts": max_attempts,
                        "violations": validation_errors,
                        "repair_attempted": repair_attempted,
                        "repair_attempts": STRUCTURED_OUTPUT_REPAIR_ATTEMPTS
                        if repair_attempted
                        else 0,
                    }
                    raw_excerpt = _tail_excerpt(result_text)
                    if raw_excerpt:
                        error_metadata["raw_output_excerpt_chars"] = len(raw_excerpt)
                    return executor._make_failure_result(
                        error_msg,
                        failure_kind="validation_exhausted",
                        error_type=error_type,
                        events=events,
                        extra={
                            "error_metadata": error_metadata,
                            "raw_output_excerpt": raw_excerpt,
                        },
                        extra_payload={
                            "error_metadata": {
                                k: v for k, v in error_metadata.items() if k != "violations"
                            }
                        },
                    )

            # Success path after deterministic validation passes
            if expects_structured and stage_output is not None:
                output_dict = stage_output.model_dump(mode="json", exclude_none=True)

                is_valid, validation_error = validate_review_structured_output(
                    node.id, output_dict, executor.snapshot
                )

                if not is_valid and is_review_stage(node.id, executor.snapshot):
                    logger.warning(
                        f"Review stage {node.id} has invalid structured output: "
                        f"{validation_error}. Defaulting to 'request_changes' for safety."
                    )
                    output_dict = get_default_review_output()

                executor.session.structured_outputs[node.id] = output_dict
                events.append(
                    Event.structured_output_parsed(
                        executor.session.id,
                        node.id,
                        content_hash=stage_output.content_hash(),
                        summary_count=len(stage_output.summary),
                        artifact_count=len(stage_output.artifacts_written),
                    )
                )

            # Check for review rejection — a "reject" recommendation is fatal
            if expects_structured and stage_output is not None:
                recommendation = (stage_output.payload or {}).get("recommendation")
                if recommendation == "reject":
                    error_msg = "Review rejected: implementation does not meet quality standards"
                    if not is_json_mode():
                        console.error(error_msg)
                    return executor._make_failure_result(
                        error_msg,
                        error_type="review_rejected",
                        events=events,
                        extra_payload={"recommendation": "reject"},
                    )

            warning_messages: list[str] = []
            if structured_warnings:
                warning_messages.extend(structured_warnings)
            if contract_result and contract_result.warnings:
                warning_messages.extend(contract_result.warning_messages)
            if warning_messages and not is_json_mode():
                for warning in list(dict.fromkeys(warning_messages)):
                    console.warning(f"Validation warning: {warning}")

            if contract_result and contract_result.passed:
                events.append(Event.contract_passed(executor.session.id, node.id))

            if result_text:
                apply_baton_patch(executor.session, result_text, node.id, stage_output=stage_output)
                persist_progress_artifact(
                    executor.session,
                    node.id,
                    executor.artifacts_dir,
                    store=executor.store,
                )

            budget_ok = True  # assume OK unless budget check says otherwise
            final_payload: dict[str, Any] = {
                "duration_seconds": metadata.get("duration_seconds"),
                "attempts": validation_attempt + 1,
            }
            if metadata.get("provider"):
                final_payload["provider"] = metadata["provider"]
            if metadata.get("trace_chunks"):
                final_payload["trace_chunk_count"] = len(metadata["trace_chunks"])
            if metadata.get("trace_truncated"):
                final_payload["trace_truncated"] = True
            if metadata.get("usage"):
                final_payload["usage"] = metadata["usage"]
                usage = metadata["usage"]
                if not usage.get("cost_usd"):
                    usage["cost_usd"] = _estimate_cost(
                        usage.get("input_tokens", 0),
                        usage.get("output_tokens", 0),
                        metadata.get("model", ""),
                    )
                executor.session.update_node_token_usage(
                    node_id=node.id,
                    input_tokens=usage.get("input_tokens", 0),
                    output_tokens=usage.get("output_tokens", 0),
                    cost_usd=usage.get("cost_usd", 0.0),
                )
                # Phase 4A: Record cost event + check budget
                if hasattr(executor, "db") and executor.db:
                    from pixl.execution.budget import record_cost

                    budget_ok = record_cost(
                        executor.db,
                        executor.session.id,
                        run_id=getattr(executor, "_current_run_id", None),
                        node_id=node.id,
                        adapter_name=metadata.get("provider"),
                        model_name=metadata.get("model"),
                        input_tokens=usage.get("input_tokens", 0),
                        output_tokens=usage.get("output_tokens", 0),
                        cost_usd=usage.get("cost_usd", 0.0),
                    )

            result: dict[str, Any] = {
                "success": True,
                "state": NodeState.TASK_COMPLETED,
                "result_state": "success",
                "events": events,
                "result_text": result_text,
                "duration_seconds": metadata.get("duration_seconds"),
                "final_event_type": EventType.TASK_COMPLETED,
                "final_event_payload": final_payload,
            }
            # Phase 4A: Signal budget exceeded to caller
            if hasattr(executor, "db") and executor.db and not budget_ok:
                result["budget_exceeded"] = True
            if metadata.get("trace_text"):
                result["trace_text"] = metadata["trace_text"]
            if metadata.get("trace_chunks"):
                result["trace_chunks"] = metadata["trace_chunks"]
            if metadata.get("trace_truncated"):
                result["trace_truncated"] = True
            return result

        # Defensive fallback; loop should have returned success/failure above.
        return executor._make_failure_result(
            "Validation loop exited unexpectedly",
            events=events,
        )

    except Exception as e:
        import traceback

        error = str(e)
        full_traceback = traceback.format_exc()

        if not is_json_mode():
            console.error(f"Task exception: {error}")
            console.debug(full_traceback)

        executor._emit_error_event(
            ProviderError(
                error,
                provider="orchestrator",
                model=task_config.model if task_config else None,
                metadata={"traceback": full_traceback},
                cause=e,
            ),
            node_id=node.id,
        )

        return executor._make_failure_result(
            error,
            failure_kind="transient",
            error_type="provider_error",
            events=events,
            extra_payload={"error_metadata": {"traceback": full_traceback}},
        )
    finally:
        executor.orchestrator.clear_sdk_event_callback()


def is_resume_session_error(message: str) -> bool:
    """Detect provider errors that indicate an invalid/expired resume session."""
    text = message.lower()
    if "session" not in text:
        return False
    markers = (
        "not found",
        "unknown",
        "invalid",
        "expired",
        "cannot resume",
        "resume failed",
        "no such",
        "does not exist",
    )
    return any(marker in text for marker in markers)


def stream_message_to_console(message) -> None:
    """Stream SDK message content to console in real-time.

    Args:
        message: SDK message to stream
    """
    from pixl.output import console

    if not hasattr(message, "content"):
        return

    for block in message.content:
        if hasattr(block, "name"):
            # Tool use block
            tool_input = getattr(block, "input", {})
            console.stream_tool_call(block.name, tool_input)
        elif hasattr(block, "thinking"):
            # Thinking block
            console.stream_thinking(block.thinking)
        elif hasattr(block, "text") and block.text:
            # Text block
            console.stream_text(block.text)


def _build_stage_output_format() -> dict[str, Any] | None:
    """Build SDK output_format spec from StageOutput JSON Schema.

    Returns a dict suitable for ClaudeAgentOptions.output_format, or None
    if schema generation fails (graceful fallback to envelope parsing).
    """
    try:
        from pixl.models.stage_output import StageOutput

        schema = StageOutput.model_json_schema()
        return {
            "type": "json_schema",
            "schema": schema,
        }
    except Exception:
        return None


def _provider_writable_dirs(executor: GraphExecutor) -> list[str]:
    """Directories external providers may write during a stage."""
    candidates: list[Path] = [executor.artifacts_dir]
    try:
        db = executor.store._get_db()  # noqa: SLF001 - executor integration layer
        candidates.append(Path(db.pixl_dir))
    except Exception:
        pass

    seen: set[str] = set()
    resolved_dirs: list[str] = []
    for candidate in candidates:
        try:
            value = str(candidate.resolve())
        except Exception:
            value = str(candidate)
        if value in seen:
            continue
        seen.add(value)
        resolved_dirs.append(value)
    return resolved_dirs


def _tail_excerpt(text: str, limit: int = RAW_OUTPUT_EXCERPT_CHARS) -> str:
    if not text:
        return ""
    return text[-limit:] if len(text) > limit else text


def execute_simulated(node: Node, instance: dict) -> dict:
    """Execute task in simulation mode (no SDK call).

    Generates a stub output based on the node's task_config so downstream
    gates and edges see realistic payload metadata.

    Args:
        node: Node definition
        instance: Node instance

    Returns:
        Execution result
    """
    stub_output = f"[SIMULATED] Output for node: {node.id}"
    if node.task_config:
        artifact_name = getattr(node.task_config, "output_artifact", None)
        if artifact_name:
            stub_output = f"[SIMULATED] {artifact_name} for: {node.id}"

    return {
        "success": True,
        "state": NodeState.TASK_COMPLETED,
        "result_state": "success",
        "events": [],
        "final_event_type": EventType.TASK_COMPLETED,
        "final_event_payload": {
            "simulated": True,
            "output": stub_output,
        },
    }

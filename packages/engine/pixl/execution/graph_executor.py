"""Graph executor for workflow sessions.

Implements the core step algorithm for executing workflow graphs:
1. Get ready nodes from executor_cursor.ready_queue
2. If empty, compute new ready nodes
3. Execute first ready node
4. Append event
5. Update node_instance state
6. Follow outgoing edges based on result
7. Update executor_cursor
8. Check terminal condition
9. Save session to DB
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pixl.execution.contract_validator import ContractValidationResult
    from pixl.models.session import ExecutorCursor

from pixl.errors import (
    PixlError,
    StateError,
    StorageError,
)
from pixl.execution.artifact_manager import version_stage_outputs
from pixl.execution.artifact_resolver import ArtifactResolver
from pixl.execution.edge_traversal import follow_edges
from pixl.execution.event_emitter import EventEmitter
from pixl.execution.gate_processing import process_condition_loop_resets, process_gate_rejections
from pixl.execution.node_state import (
    allow_simulated_execution,
    get_or_create_node_instance,
    reset_instance_to_pending,
    resolve_agent_and_model,
    update_node_instance_metadata,
    update_node_instance_state,
    workflow_max_attempts,
)
from pixl.execution.prompt_builder import (
    build_change_request_context,
    build_contract_variables,
    build_frozen_context,
    build_rejection_feedback_context,
    build_unified_prompt,
    load_feature_context,
    resolve_contract_data,
    resolve_template_string,
    write_rejection_feedback,
)
from pixl.execution.recovery_handler import handle_pixl_error, try_recovery_for_result
from pixl.execution.session_report import save_session_summary
from pixl.execution.task_executor import execute_simulated, execute_with_orchestrator
from pixl.models.event import Event, EventType
from pixl.models.node_instance import NodeState
from pixl.models.session import SessionStatus, WorkflowSession
from pixl.models.workflow import (
    Node,
    NodeType,
    WorkflowSnapshot,
)
from pixl.paths import get_pixl_dir
from pixl.recovery.engine import RecoveryEngine
from pixl.storage import BacklogStore

logger = logging.getLogger(__name__)


class GraphExecutor:
    """Executes workflow graphs with checkpoint/resume support.

    The executor maintains:
    - Ready queue of nodes to execute
    - Current execution position
    - Loop state tracking
    - Event log
    - Optional orchestrator for SDK calls
    - Event callback for real-time streaming
    - Optional session_manager for auto-refresh on external changes
    """

    def __init__(
        self,
        session: WorkflowSession,
        snapshot: WorkflowSnapshot,
        session_dir: Path,
        project_root: Path | None = None,
        artifacts_dir: Path | None = None,
        orchestrator: Any | None = None,  # "OrchestratorCore" - avoid circular import
        event_callback: Callable[[Event], None] | None = None,
        session_manager: Any | None = None,  # "SessionManager" - avoid circular import
        state_bridge: Any | None = None,  # "WorkflowStateBridge" - avoid circular import
        db: Any | None = None,  # "PixlDB" - avoid circular import
    ) -> None:
        """Initialize the executor.

        Args:
            session: WorkflowSession to execute
            snapshot: WorkflowSnapshot defining the graph
            session_dir: Directory for session storage
            artifacts_dir: Directory for artifact storage
            orchestrator: Optional orchestrator for actual SDK calls
            event_callback: Optional callback for real-time event streaming
            session_manager: Optional SessionManager for auto-refresh on changes
            state_bridge: Optional WorkflowStateBridge for entity state transitions
        """
        self.session = session
        self.snapshot = snapshot
        self.session_dir = session_dir
        self.artifacts_dir = artifacts_dir or (session_dir / "artifacts")
        self.orchestrator = orchestrator
        self.event_callback = event_callback
        self.session_manager = session_manager
        self.state_bridge = state_bridge
        self.db = db

        if self.state_bridge:
            if hasattr(self.state_bridge, "set_event_callback"):
                self.state_bridge.set_event_callback(self._emit_event)
            if hasattr(self.state_bridge, "set_session_id"):
                self.state_bridge.set_session_id(self.session.id)

        # Import here to avoid circular dependency
        from pixl.storage.workflow_session_store import WorkflowSessionStore

        # Determine project root (repo) for storage + git operations
        if project_root is None:
            if self.session.workspace_root:
                project_root = Path(self.session.workspace_root)
            else:
                # Fallback: infer project root from session directory layout
                project_root = session_dir.parent.parent.parent
        self.store = WorkflowSessionStore(project_root)
        self.project_root = project_root
        self.pixl_dir = get_pixl_dir(project_root)

        # workspace_root: the actual project directory where the agent runs.
        # project_root is the storage dir (~/.pixl/projects/...) while
        # workspace_root is the real project repo. Use workspace_root for
        # file resolution (contract validation, git diffs).
        if self.session.workspace_root:
            self._workspace_root = Path(self.session.workspace_root)
        else:
            self._workspace_root = self.project_root

        self._stage_configs: dict[str, dict] = {}
        self._missing_stage_configs_logged: set[str] = set()
        if snapshot.workflow_config:
            stages_data = snapshot.workflow_config.get("stages", [])
            duplicates_logged: set[str] = set()
            for stage in stages_data:
                stage_id = stage.get("id")
                if not stage_id:
                    continue
                if stage_id in self._stage_configs and stage_id not in duplicates_logged:
                    logger.warning(
                        "Duplicate stage config for '%s' detected; using last occurrence",
                        stage_id,
                    )
                    duplicates_logged.add(stage_id)
                self._stage_configs[stage_id] = stage

        self._stage_contracts: dict[str, dict] = {}
        for stage_id, stage_cfg in self._stage_configs.items():
            if "contract" in stage_cfg and stage_cfg["contract"]:
                self._stage_contracts[stage_id] = stage_cfg["contract"]

        # Shared context compiler helpers (avoids re-creation per stage)
        from pixl.context.differ import ArtifactDiffer
        from pixl.context.summarizer import ArtifactSummarizer

        self._artifact_summarizer = ArtifactSummarizer(self.artifacts_dir)
        self._artifact_differ = ArtifactDiffer(self.artifacts_dir)

        # Incident store for recovery history tracking (lazy loaded)
        self._incident_store = None  # Loaded on first recovery event

        # Extracted collaborators (S1: EventEmitter, S2: ArtifactResolver)
        self.event_emitter = EventEmitter(
            session_id=self.session.id,
            store=self.store,
            event_callback=self.event_callback,
            incident_store_getter=self._get_incident_store,
        )
        self.artifact_resolver = ArtifactResolver(
            session_id=self.session.id,
            artifacts_dir=self.artifacts_dir,
            store=self.store,
            build_contract_variables=self._build_contract_variables,
        )

        # Recovery engine for deterministic error handling
        self._recovery_engine = RecoveryEngine(
            session_id=self.session.id,
            emit_event=self._persist_event,
            incident_store=self._get_incident_store(),
        )

        # Recovery counters for observability
        self._recovery_counters: dict[str, int] = {
            "requested": 0,
            "retries": 0,
            "contract_repairs": 0,
            "patch_and_test": 0,
            "escalations": 0,
            "successes": 0,
        }
        # Cache deterministic path expansions used by missing-input backtracking.
        self._path_nodes_cache: dict[tuple[str, str], set[str]] = {}

        # Cached expression evaluator (avoids re-creation per condition check)
        self._expr_evaluator: Any | None = None

        # Cached ContractValidator (avoids re-creation per validation call)
        self._contract_validator: Any | None = None

        # Pre-build loop constraint indexes for O(1) lookup instead of linear scans
        self._loop_constraints_by_from: dict[str, list] = {}
        self._loop_constraints_by_to: dict[str, list] = {}
        self._loop_constraint_by_edge: dict[tuple[str, str], Any] = {}
        for constraint in snapshot.graph.loop_constraints:
            self._loop_constraints_by_from.setdefault(constraint.from_node, []).append(constraint)
            self._loop_constraints_by_to.setdefault(constraint.to_node, []).append(constraint)
            self._loop_constraint_by_edge[(constraint.from_node, constraint.to_node)] = constraint

        if session_manager:
            session_manager.register_observer(self._on_session_changed)

    def _get_incident_store(self):
        """Lazy-load the incident store."""
        if self._incident_store is None:
            from pixl.recovery.incident_store import IncidentStore

            self._incident_store = IncidentStore(self.project_root)
        return self._incident_store

    def _on_session_changed(self, updated_session: WorkflowSession) -> None:
        """Handle session change notification from SessionManager.

        This is called automatically when the session is mutated through
        the SessionManager (e.g., gate approval from CLI).

        Args:
            updated_session: The updated session
        """
        # Only refresh if it's our session
        if updated_session.id == self.session.id:
            self.session = updated_session

    @property
    def recovery_counters(self) -> dict[str, int]:
        """Return a copy of the current recovery counters."""
        return dict(self._recovery_counters)

    def _refresh_session(self) -> None:
        """Internal: Refresh the executor's session from the store.

        This is now called automatically via SessionManager observer pattern.
        Direct use is rarely needed anymore.
        """
        refreshed = self.store.load_session(self.session.id)
        if refreshed:
            self.session = refreshed

    # Parallel Step Algorithm (Third Era)

    async def step_parallel(self) -> dict[str, Any]:
        """Execute ALL ready-queue nodes concurrently.

        Unlike ``step()`` which picks one node, this runs every independent
        node in parallel via ``asyncio.TaskGroup``.  Returns a merged result
        dict with aggregated events and per-node outcomes.
        """
        import asyncio

        merged: dict[str, Any] = {
            "executed": False,
            "node_ids": [],
            "events": [],
            "status": None,
            "terminal": False,
            "results": {},  # node_id -> individual step result
        }

        try:
            cursor = self.session.executor_cursor
            if cursor is None:
                cursor = self._initialize_cursor()
                self.session.executor_cursor = cursor

            ready_queue = cursor.ready_queue
            if not ready_queue:
                process_gate_rejections(self)
                ready_queue = self._compute_ready_queue()
                cursor.ready_queue = ready_queue

            if not ready_queue:
                status = self._compute_status()
                merged["status"] = status
                merged["terminal"] = self._is_terminal(status)
                checkpoint_event = self._checkpoint(reason="idle")
                merged["events"].append(checkpoint_event)

                if not merged["terminal"]:
                    diagnostic_event = self._commit_transition(
                        event_type=EventType.RECOVERY_NO_RUNNABLE_NODE,
                        node_id=None,
                        payload=self._build_no_runnable_diagnostics(),
                        from_state=None,
                        to_state=None,
                    )
                    merged["events"].append(diagnostic_event)

                self._finalize_terminal_session(merged)
                return merged

            # Snapshot the full ready queue — execute ALL nodes concurrently
            nodes_to_run = list(ready_queue)
            merged["node_ids"] = nodes_to_run

            node_results: dict[str, dict[str, Any]] = {}

            def _execute_single_node(nid: str) -> dict[str, Any]:
                """Execute a single node synchronously (reuses existing step internals)."""
                return self._execute_single_node_step(nid)

            loop = asyncio.get_running_loop()
            async with asyncio.TaskGroup() as tg:
                for nid in nodes_to_run:

                    async def _run(node_id: str = nid) -> None:
                        # Run synchronous node execution in a thread to avoid blocking
                        result = await loop.run_in_executor(None, _execute_single_node, node_id)
                        node_results[node_id] = result

                    tg.create_task(_run())

            merged["executed"] = any(r.get("executed") for r in node_results.values())
            for nid, nr in node_results.items():
                merged["events"].extend(nr.get("events", []))
                merged["results"][nid] = nr

            # Recompute terminal status after all nodes complete
            status = self._compute_status()
            merged["status"] = status
            merged["terminal"] = self._is_terminal(status)
            self._finalize_terminal_session(merged)
            return merged

        except PixlError as exc:
            return handle_pixl_error(self, exc, None, merged)
        except ExceptionGroup as eg:
            first = eg.exceptions[0] if eg.exceptions else Exception("unknown")
            return handle_pixl_error(
                self,
                StateError(
                    "Parallel step failure",
                    invariant="parallel_step",
                    details=str(first),
                    cause=first,
                ),
                None,
                merged,
            )

    def _execute_single_node_step(self, node_id: str) -> dict[str, Any]:
        """Execute a single node (extracted from step() internals).

        This is the per-node execution logic used by both ``step()``
        (sequential) and ``step_parallel()`` (concurrent).
        """
        result: dict[str, Any] = {
            "executed": False,
            "node_id": node_id,
            "events": [],
            "success": False,
        }

        graph = self.snapshot.graph
        node = graph.nodes.get(node_id)
        if not node:
            raise StateError(
                f"Node '{node_id}' not found in snapshot",
                invariant="node_lookup",
                details=node_id,
            )

        node_instance = get_or_create_node_instance(self.session, node_id)

        # Pre-execution frozen artifact integrity check
        if node.type in (NodeType.TASK, NodeType.SUB_WORKFLOW) and self.session.frozen_artifacts:
            frozen_check = self._pre_execution_frozen_check(node)
            if frozen_check is not None:
                result["executed"] = True
                update_node_instance_state(
                    self.session,
                    node.id,
                    NodeState.TASK_FAILED,
                    {
                        "failure_kind": "frozen_violation",
                        "error": frozen_check["error"],
                        "error_type": "contract_error",
                    },
                )
                cursor = self.session.executor_cursor
                if cursor:
                    cursor.current_node_id = None
                    cursor.remove_from_ready_queue(node_id)
                fail_event = self._commit_transition(
                    event_type=EventType.TASK_FAILED,
                    node_id=node_id,
                    payload={
                        "error": frozen_check["error"],
                        "failure_kind": "frozen_violation",
                        "error_type": "contract_error",
                    },
                    from_state=None,
                    to_state=NodeState.TASK_FAILED,
                )
                result["events"] = frozen_check["events"] + [fail_event]
                return result

        events: list[Event] = []
        persisted_events: list[Event] = []
        if node.type == NodeType.TASK:
            execution_result = self._execute_task(node, node_instance)
            events.extend(execution_result["events"])
            persisted_events.extend(execution_result.get("persisted_events", []))
        elif node.type == NodeType.GATE:
            execution_result = self._execute_gate(node, node_instance)
            events.extend(execution_result["events"])
        elif node.type == NodeType.HOOK:
            execution_result = self._execute_hook(node, node_instance)
            events.extend(execution_result["events"])
            persisted_events.extend(execution_result.get("persisted_events", []))
        elif node.type == NodeType.SUB_WORKFLOW:
            depth = getattr(self, "_sub_workflow_depth", 0)
            execution_result = self._execute_sub_workflow(node, node_instance, _depth=depth)
            events.extend(execution_result["events"])
            persisted_events.extend(execution_result.get("persisted_events", []))
        else:
            execution_result = self._make_failure_result("Unknown node type")

        result["executed"] = True
        result["success"] = execution_result.get("success", False)

        new_state = execution_result.get("state", NodeState.TASK_FAILED)
        update_node_instance_state(self.session, node_id, new_state, execution_result)

        # Recovery check for non-exception task failures
        if new_state == NodeState.TASK_FAILED and node.type == NodeType.TASK:
            retry_result = try_recovery_for_result(
                self, node_id, execution_result, events, persisted_events
            )
            if retry_result is not None:
                return retry_result

        if self.state_bridge and node.type == NodeType.TASK and self.session.feature_id:
            self._trigger_entity_transition(
                node_id, execution_result.get("success", False), execution_result.get("error")
            )

        # Version stage outputs on success
        if node.type == NodeType.TASK and execution_result.get("success", False):
            self._version_stage_outputs(node_id)

        # Follow outgoing edges
        next_nodes = follow_edges(
            self,
            node_id,
            execution_result.get("result_state", "failed"),
            execution_result.get("failure_kind"),
        )

        source_reset_deferred = False
        if next_nodes and execution_result.get("success", False):
            source_reset_deferred = process_condition_loop_resets(
                self, node_id, next_nodes, defer_source_reset=True
            )

        cursor = self.session.executor_cursor
        if cursor:
            cursor.current_node_id = None
            cursor.remove_from_ready_queue(node_id)
            for next_node in next_nodes:
                cursor.add_to_ready_queue(next_node)

        self._emit_events_batch(events)

        final_event_type = execution_result.get("final_event_type")
        if not isinstance(final_event_type, EventType):
            raise StateError(
                "Execution result missing final_event_type",
                invariant="final_event_type",
                details=str(final_event_type),
            )

        final_payload = execution_result.get("final_event_payload", {})
        final_event = self._commit_transition(
            event_type=final_event_type,
            node_id=node_id,
            payload=final_payload,
            from_state=None,
            to_state=new_state,
        )

        if source_reset_deferred:
            reset_instance_to_pending(self.session, node_id)

        result["events"] = persisted_events + events + [final_event]
        return result

    # Core Step Algorithm (Sequential — Legacy)

    def step(self) -> dict[str, Any]:
        """Execute one step of the graph.

        Returns:
            Step result with:
                - executed: bool - whether a node was executed
                - node_id: str | None - which node was executed
                - events: list[Event] - events generated
                - status: SessionStatus - current session status
                - terminal: bool - whether execution is complete

        Algorithm:
        1. Get ready nodes from executor_cursor.ready_queue
        2. If empty, compute new ready nodes:
           - Find nodes whose predecessors completed successfully
           - Check loop constraints (can_enter)
           - Check gate conditions
        3. Execute first ready node (or parallel batch)
        4. Append event (task_started, gate_requested, etc.)
        5. Update node_instance state
        6. Follow outgoing edges based on result:
           - SUCCESS edge -> add to ready_queue
           - FAILURE edge -> add to ready_queue
           - LOOP edge -> record_iteration, check max
        7. Update executor_cursor
        8. Check terminal condition
        9. Save session to DB
        """
        result = {
            "executed": False,
            "node_id": None,
            "events": [],
            "status": None,  # Computed lazily — set before return
            "terminal": False,
        }
        node_id: str | None = None

        try:
            # Check interrupt signal before processing (GAP-11)
            if self.orchestrator and hasattr(self.orchestrator, "_interrupt_event"):
                if self.orchestrator._interrupt_event.is_set():
                    logger.info("Interrupt detected in GraphExecutor.step(), pausing session")
                    self.session.status = SessionStatus.PAUSED
                    self.session.pause_reason = "Interrupted by parent"
                    checkpoint_event = self._checkpoint(reason="interrupted")
                    result["events"].append(checkpoint_event)
                    result["status"] = SessionStatus.PAUSED
                    result["terminal"] = False
                    return result

            cursor = self.session.executor_cursor
            if cursor is None:
                cursor = self._initialize_cursor()
                self.session.executor_cursor = cursor

            ready_queue = cursor.ready_queue

            if not ready_queue:
                process_gate_rejections(self)
                ready_queue = self._compute_ready_queue()
                cursor.ready_queue = ready_queue

            # If still no ready nodes, check if we're done
            if not ready_queue:
                status = self._compute_status()
                result["status"] = status
                result["terminal"] = self._is_terminal(status)
                checkpoint_event = self._checkpoint(reason="idle")
                result["events"].append(checkpoint_event)

                if not result["terminal"]:
                    diagnostic_event = self._commit_transition(
                        event_type=EventType.RECOVERY_NO_RUNNABLE_NODE,
                        node_id=None,
                        payload=self._build_no_runnable_diagnostics(),
                        from_state=None,
                        to_state=None,
                    )
                    result["events"].append(diagnostic_event)

                self._finalize_terminal_session(result)
                return result

            node_id = ready_queue[0]
            cursor.current_node_id = node_id

            graph = self.snapshot.graph
            node = graph.nodes.get(node_id)
            if not node:
                raise StateError(
                    f"Node '{node_id}' not found in snapshot",
                    invariant="node_lookup",
                    details=node_id,
                )

            node_instance = get_or_create_node_instance(self.session, node_id)
            result["node_id"] = node_id

            if (
                node.type in (NodeType.TASK, NodeType.SUB_WORKFLOW)
                and self.session.frozen_artifacts
            ):
                frozen_check = self._pre_execution_frozen_check(node)
                if frozen_check is not None:
                    # Frozen artifact violated — fail before executing
                    result["executed"] = True
                    result["success"] = False

                    for event in frozen_check["events"]:
                        self._emit_event(event)

                    update_node_instance_state(
                        self.session,
                        node.id,
                        NodeState.TASK_FAILED,
                        {
                            "failure_kind": "frozen_violation",
                            "error": frozen_check["error"],
                            "error_type": "contract_error",
                        },
                    )
                    cursor.current_node_id = None
                    cursor.remove_from_ready_queue(node_id)

                    fail_event = self._commit_transition(
                        event_type=EventType.TASK_FAILED,
                        node_id=node_id,
                        payload={
                            "error": frozen_check["error"],
                            "failure_kind": "frozen_violation",
                            "error_type": "contract_error",
                        },
                        from_state=None,
                        to_state=NodeState.TASK_FAILED,
                    )

                    result["events"] = frozen_check["events"] + [fail_event]
                    status = self._compute_status()
                    result["status"] = status
                    result["terminal"] = self._is_terminal(status)

                    self._finalize_terminal_session(result)
                    return result

            events: list[Event] = []
            persisted_events: list[Event] = []
            if node.type == NodeType.TASK:
                execution_result = self._execute_task(node, node_instance)
                events.extend(execution_result["events"])
                persisted_events.extend(execution_result.get("persisted_events", []))
            elif node.type == NodeType.GATE:
                execution_result = self._execute_gate(node, node_instance)
                events.extend(execution_result["events"])
            elif node.type == NodeType.HOOK:
                execution_result = self._execute_hook(node, node_instance)
                events.extend(execution_result["events"])
                persisted_events.extend(execution_result.get("persisted_events", []))
            elif node.type == NodeType.SUB_WORKFLOW:
                depth = getattr(self, "_sub_workflow_depth", 0)
                execution_result = self._execute_sub_workflow(node, node_instance, _depth=depth)
                events.extend(execution_result["events"])
                persisted_events.extend(execution_result.get("persisted_events", []))
            else:
                execution_result = self._make_failure_result("Unknown node type")

            result["executed"] = True
            result["success"] = execution_result.get("success", False)

            new_state = execution_result.get("state", NodeState.TASK_FAILED)
            update_node_instance_state(self.session, node_id, new_state, execution_result)

            if new_state == NodeState.TASK_FAILED and node.type == NodeType.TASK:
                retry_result = try_recovery_for_result(
                    self,
                    node_id,
                    execution_result,
                    events,
                    persisted_events,
                )
                if retry_result is not None:
                    return retry_result

            if self.state_bridge and node.type == NodeType.TASK and self.session.feature_id:
                self._trigger_entity_transition(
                    node_id,
                    execution_result.get("success", False),
                    execution_result.get("error"),
                )

            if node.type == NodeType.TASK and execution_result.get("success", False):
                self._version_stage_outputs(node_id)

            next_nodes = follow_edges(
                self,
                node_id,
                execution_result.get("result_state", "failed"),
                execution_result.get("failure_kind"),
            )

            # Defer resetting the source node (node_id) — it must stay in its
            # completed/failed state until _commit_transition persists the event.
            source_reset_deferred = False
            if next_nodes and execution_result.get("success", False):
                source_reset_deferred = process_condition_loop_resets(
                    self,
                    node_id,
                    next_nodes,
                    defer_source_reset=True,
                )

            cursor.current_node_id = None
            cursor.remove_from_ready_queue(node_id)
            for next_node in next_nodes:
                cursor.add_to_ready_queue(next_node)

            status = self._compute_status()
            result["status"] = status
            result["terminal"] = self._is_terminal(status)

            self._emit_events_batch(events)

            final_event_type = execution_result.get("final_event_type")
            if not isinstance(final_event_type, EventType):
                raise StateError(
                    "Execution result missing final_event_type",
                    invariant="final_event_type",
                    details=str(final_event_type),
                )
            final_payload = execution_result.get("final_event_payload", {})
            final_event = self._commit_transition(
                event_type=final_event_type,
                node_id=node_id,
                payload=final_payload,
                from_state=None,
                to_state=new_state,
            )

            # source node for the condition loop revision pass.
            if source_reset_deferred:
                reset_instance_to_pending(self.session, node_id)

            result["events"] = persisted_events + events + [final_event]

            self._finalize_terminal_session(result)
            return result

        except PixlError as exc:
            return handle_pixl_error(self, exc, node_id, result)
        except Exception as exc:
            return handle_pixl_error(
                self,
                StateError(
                    "Unhandled executor error",
                    invariant="executor_step",
                    details=str(exc),
                    cause=exc,
                ),
                node_id,
                result,
            )

    # Ready Queue Computation

    def _initialize_cursor(self) -> ExecutorCursor:
        """Initialize executor cursor with entry nodes.

        Performs pre-flight validation: verifies the feature data is
        loadable before any node executes. If the feature has data in
        SQLite that can't be deserialized, the session fails immediately
        with a clear StateError instead of silently proceeding with empty
        context.
        """
        from pixl.models.session import ExecutorCursor

        # Pre-flight: verify feature data is loadable (fail fast on corruption)
        load_feature_context(
            session=self.session,
            project_root=self.project_root,
            snapshot=self.snapshot,
            node_id=None,
        )

        entry_nodes = self.snapshot.graph.entry_nodes
        return ExecutorCursor(ready_queue=sorted(entry_nodes))

    def _compute_ready_queue(self) -> list[str]:
        """Compute ready nodes with deterministic ordering.

        A node is ready if:
        1. All its predecessors are in terminal success states
        2. Any loop constraints allow entry
        3. It's not already completed or failed

        Returns:
            Sorted list of ready node IDs
        """
        ready = []
        graph = self.snapshot.graph

        for node_id, _node in graph.nodes.items():
            # Skip nodes in terminal states (completed, failed, or skipped)
            instance = self.session.get_node_instance(node_id)
            if instance:
                state = instance.get("state", "")
                # Skip completed/approved/skipped nodes
                if state in (
                    NodeState.TASK_COMPLETED.value,
                    NodeState.GATE_APPROVED.value,
                    NodeState.TASK_SKIPPED.value,
                ):
                    continue
                # Skip rejected gates — processed by _process_gate_rejections
                if state == NodeState.GATE_REJECTED.value:
                    continue
                # Skip gates waiting for external approval
                if state == NodeState.GATE_WAITING.value:
                    continue
                # Skip blocked tasks until explicitly resumed/unblocked.
                if state == NodeState.TASK_BLOCKED.value:
                    continue
                # Skip tasks already running (prevents re-queuing zombies)
                if state == NodeState.TASK_RUNNING.value:
                    continue
                # Skip failed nodes unless they have a retry loop configured
                if state == NodeState.TASK_FAILED.value:
                    has_retry_loop = False
                    for constraint in self._loop_constraints_by_from.get(node_id, ()):
                        if constraint.edge_trigger.value == "failure":
                            loop_state = self.session.get_loop_state(constraint.id)
                            if not loop_state or loop_state.can_enter():
                                has_retry_loop = True
                                break
                    if not has_retry_loop:
                        continue

            # Check if all predecessors are complete (exclude loop-back edges to avoid deadlock)
            predecessors = graph.get_predecessors(node_id, exclude_loop_edges=True)
            all_predecessors_complete = True

            for pred_id in predecessors:
                pred_instance = self.session.get_node_instance(pred_id)
                if not pred_instance:
                    all_predecessors_complete = False
                    break

                pred_state = pred_instance.get("state", "")
                if pred_state not in (
                    NodeState.TASK_COMPLETED.value,
                    NodeState.GATE_APPROVED.value,
                    NodeState.TASK_SKIPPED.value,
                ):
                    all_predecessors_complete = False
                    break

            if not all_predecessors_complete:
                continue

            # Check loop constraints
            if self._check_loop_constraints(node_id):
                ready.append(node_id)

        # Deterministic ordering: by priority (desc) then node_id (asc)
        ready.sort(
            key=lambda nid: (
                -graph.nodes[nid].priority,
                nid,
            )
        )

        return ready

    def _check_loop_constraints(self, node_id: str) -> bool:
        """Check if any loop constraints prevent entering this node.

        Args:
            node_id: Node ID to check

        Returns:
            True if node can be entered
        """
        for constraint in self._loop_constraints_by_to.get(node_id, ()):
            loop_state = self.session.get_loop_state(constraint.id)
            if loop_state and not loop_state.can_enter():
                return False
        return True

    def _build_no_runnable_diagnostics(self) -> dict[str, Any]:
        """Build diagnostics for idle cycles where no node is runnable."""
        graph = self.snapshot.graph
        diagnostics: list[dict[str, Any]] = []

        for node_id in sorted(graph.nodes.keys()):
            instance = self.session.get_node_instance(node_id) or {}
            state = str(instance.get("state") or "")
            if state in (
                NodeState.TASK_COMPLETED.value,
                NodeState.GATE_APPROVED.value,
                NodeState.TASK_SKIPPED.value,
                NodeState.TASK_RUNNING.value,
                NodeState.GATE_WAITING.value,
            ):
                continue

            predecessors = graph.get_predecessors(node_id)
            predecessor_states = [
                {
                    "node_id": pred_id,
                    "state": (self.session.get_node_instance(pred_id) or {}).get("state"),
                }
                for pred_id in predecessors
            ]
            all_predecessors_terminal = all(
                p["state"]
                in (
                    NodeState.TASK_COMPLETED.value,
                    NodeState.GATE_APPROVED.value,
                    NodeState.TASK_SKIPPED.value,
                )
                for p in predecessor_states
            )
            diagnostics.append(
                {
                    "node_id": node_id,
                    "node_state": state or "unknown",
                    "all_predecessors_terminal": all_predecessors_terminal,
                    "predecessors": predecessor_states,
                    "loop_constraints_ok": self._check_loop_constraints(node_id),
                }
            )
            if len(diagnostics) >= 20:
                break

        return {
            "reason": "no_nodes_ready",
            "ready_queue": list(self.session.executor_cursor.ready_queue)
            if self.session.executor_cursor
            else [],
            "nodes": diagnostics,
        }

    # Node Execution
    # Event emission — thin wrappers delegating to self.event_emitter (S1 extraction)

    def _emit_event(self, event: Event) -> None:
        """Emit event to store and callback. Delegates to EventEmitter."""
        self.event_emitter.emit_event(event)

    def _emit_events_batch(self, events: list[Event]) -> None:
        """Emit multiple events in a single DB transaction. Delegates to EventEmitter."""
        self.event_emitter.emit_events_batch(events)

    def _emit_error_event(self, error: PixlError, node_id: str | None = None) -> Event | None:
        """Emit a structured error event. Delegates to EventEmitter."""
        return self.event_emitter.emit_error_event(error, node_id=node_id)

    def _persist_event(self, event: Event) -> None:
        """Persist a pre-built Event to storage. Delegates to EventEmitter."""
        self.event_emitter.persist_event(event)

    def _commit_transition(
        self,
        *,
        event_type: EventType,
        node_id: str | None,
        payload: dict[str, Any] | None,
        from_state: NodeState | None,
        to_state: NodeState | None,
    ) -> Event:
        """Commit an event + session state update atomically. Delegates to EventEmitter."""
        return self.event_emitter.commit_transition(
            session=self.session,
            event_type=event_type,
            node_id=node_id,
            payload=payload,
            from_state=from_state,
            to_state=to_state,
        )

    def _checkpoint(self, reason: str | None = None) -> Event:
        """Persist a checkpoint event and session snapshot. Delegates to EventEmitter."""
        return self.event_emitter.checkpoint(session=self.session, reason=reason)

    def _compute_status(self) -> SessionStatus:
        """Shorthand for computing session status with the current snapshot."""
        return self.session.compute_status_with_snapshot(self.snapshot)

    def _finalize_terminal_session(self, result: dict[str, Any]) -> None:
        """Emit completion/failure event and mark session ended if result is terminal."""
        if not result.get("terminal"):
            return

        terminal_event = (
            Event.session_completed(self.session.id)
            if result["status"] == SessionStatus.COMPLETED
            else Event.session_failed(self.session.id, "Workflow terminated")
        )
        terminal_committed = self._commit_transition(
            event_type=terminal_event.type,
            node_id=None,
            payload=terminal_event.data,
            from_state=None,
            to_state=None,
        )
        result["events"].append(terminal_committed)
        self._mark_session_ended()
        self._save_session_summary()

        # Cleanup persistent SDK clients on workflow end
        if self.orchestrator and hasattr(self.orchestrator, "cleanup_sdk_clients"):
            try:
                from pixl.utils.async_compat import run_coroutine_sync

                run_coroutine_sync(self.orchestrator.cleanup_sdk_clients())
            except Exception:
                logger.debug("Failed to cleanup SDK clients on session end", exc_info=True)

    def _make_failure_result(
        self,
        error: str,
        *,
        failure_kind: str = "fatal",
        error_type: str = "state_error",
        events: list[Event] | None = None,
        persisted_events: list[Event] | None = None,
        state: NodeState = NodeState.TASK_FAILED,
        result_state: str = "failed",
        final_event_type: EventType = EventType.TASK_FAILED,
        extra: dict[str, Any] | None = None,
        extra_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build a standardized task/hook failure result dict."""
        payload: dict[str, Any] = {
            "error": error,
            "failure_kind": failure_kind,
            "error_type": error_type,
        }
        if extra_payload:
            payload.update(extra_payload)

        result: dict[str, Any] = {
            "success": False,
            "state": state,
            "result_state": result_state,
            "failure_kind": failure_kind,
            "error": error,
            "error_type": error_type,
            "final_event_type": final_event_type,
            "final_event_payload": payload,
        }
        if events is not None:
            result["events"] = events
        if persisted_events is not None:
            result["persisted_events"] = persisted_events
        if extra:
            result.update(extra)
        return result

    def _get_stage_config(self, stage_id: str) -> dict:
        """Return stage config or an empty dict with a one-time warning."""
        config = self._stage_configs.get(stage_id)
        if not config and stage_id not in self._missing_stage_configs_logged:
            logger.warning(
                "No stage config found for '%s'; using defaults",
                stage_id,
            )
            self._missing_stage_configs_logged.add(stage_id)
        return config or {}

    def _execute_task(self, node: Node, instance: dict) -> dict:
        """Execute a task node.

        If orchestrator is available, invokes the agent/model via SDK.
        Otherwise simulates execution for testing.

        Args:
            node: Node definition
            instance: Node instance

        Returns:
            Execution result with events
        """
        events: list[Event] = []
        persisted_events: list[Event] = []

        # Hoist stage config lookup — reused by state bridge and input validation
        stage_config = self._get_stage_config(node.id)

        # Use source_entity_id (epic/roadmap) when available.
        if self.state_bridge and self.session.feature_id:
            start_entity_id = (
                self.snapshot.workflow_config.get("variables", {}).get("source_entity_id")
                or self.session.feature_id
            )
            try:
                self.state_bridge.on_stage_start(
                    start_entity_id,
                    node.id,
                    stage_config,
                    session_id=self.session.id,
                )
            except Exception as exc:
                self._emit_error_event(
                    StateError(
                        "State bridge failed on stage start",
                        invariant="state_bridge_start",
                        details=str(exc),
                        cause=exc,
                        metadata={"node_id": node.id, "entity_id": start_entity_id},
                    ),
                    node_id=node.id,
                )

        # Pre-execution input validation
        required_inputs = stage_config.get("required_artifacts", [])
        artifact_handoff_manifest = self._build_artifact_handoff_manifest(node.id, required_inputs)
        events.append(
            Event.artifact_handoff(
                self.session.id,
                node.id,
                payload={
                    "required_artifacts": required_inputs,
                    "manifest": artifact_handoff_manifest,
                },
            )
        )
        if required_inputs:
            missing = [entry["path"] for entry in artifact_handoff_manifest if not entry["exists"]]
            if missing:
                error_msg = f"Required input artifacts missing: {', '.join(missing)}"
                return self._make_failure_result(
                    error_msg,
                    failure_kind="missing_inputs",
                    events=events,
                    persisted_events=persisted_events,
                    extra={
                        "missing_inputs": missing,
                        "artifact_handoff_manifest": artifact_handoff_manifest,
                    },
                    extra_payload={
                        "missing_inputs": missing,
                        "artifact_handoff_manifest": artifact_handoff_manifest,
                    },
                )

        # Phase 5: Acquire node execution lock
        run_id = getattr(self, "_current_run_id", None) or "unknown"
        locked = False
        if self.db:
            locked = self.db.sessions.lock_node(self.session.id, node.id, run_id)
            if not locked:
                return self._make_failure_result(
                    f"Node {node.id} is locked by another run",
                    events=events,
                    persisted_events=persisted_events,
                )

        agent_name, effective_model = resolve_agent_and_model(node, self.project_root)

        update_node_instance_metadata(
            self.session,
            node.id,
            agent_name=agent_name,
            model_name=effective_model,
            max_attempts=workflow_max_attempts(self.snapshot),
        )

        # the cursor update and state transition are persisted atomically.
        # This closes the crash window where a node is TASK_RUNNING but still queued.
        cursor = self.session.executor_cursor
        if cursor:
            cursor.remove_from_ready_queue(node.id)

        # Transition to running
        update_node_instance_state(self.session, node.id, NodeState.TASK_RUNNING, {})
        self._mark_session_started()  # idempotent — sets started_at once
        start_payload: dict[str, Any] = {}
        if agent_name:
            start_payload["agent_name"] = agent_name
        if effective_model:
            start_payload["effective_model"] = effective_model
        if self.snapshot.workflow_config:
            sm = self.snapshot.workflow_config.get("session_mode")
            wf = self.snapshot.workflow_config.get("workflow_format")
            if sm:
                start_payload["session_mode"] = sm
            if wf:
                start_payload["workflow_format"] = wf

        start_event = self._commit_transition(
            event_type=EventType.TASK_STARTED,
            node_id=node.id,
            payload=start_payload,
            from_state=None,
            to_state=NodeState.TASK_RUNNING,
        )
        persisted_events.append(start_event)

        # Execute with orchestrator. Simulated success is allowed only in
        # explicit simulation contexts (tests/dev), never silently in production.
        try:
            if allow_simulated_execution():
                execution_result = execute_simulated(node, instance)
            elif self.orchestrator and node.task_config:
                execution_result = execute_with_orchestrator(
                    self,
                    node,
                    instance,
                    effective_model=effective_model,
                    artifact_handoff_manifest=artifact_handoff_manifest,
                )
            else:
                missing = []
                if not self.orchestrator:
                    missing.append("orchestrator")
                if not node.task_config:
                    missing.append("task_config")
                missing_str = ", ".join(missing) if missing else "execution wiring"
                error_msg = f"Task execution unavailable: missing {missing_str}"
                execution_result = self._make_failure_result(
                    error_msg,
                    events=[],
                )

            events.extend(execution_result["events"])
            execution_result["events"] = events
            execution_result["persisted_events"] = persisted_events
            return execution_result
        finally:
            # Phase 5: Release node execution lock
            if locked and self.db:
                self.db.sessions.release_node(self.session.id, node.id, run_id)

    # Pre-Execution Input Validation
    # Artifact resolution — thin wrappers delegating to self.artifact_resolver (S2 extraction)

    def _check_required_inputs(
        self,
        node_id: str,
        required_artifacts: list[str],
    ) -> list[str]:
        """Check required input artifacts. Delegates to ArtifactResolver."""
        return self.artifact_resolver.check_required_inputs(node_id, required_artifacts)

    def _resolve_required_artifact_path(self, artifact: str, variables: dict[str, str]) -> str:
        """Resolve and normalize a required artifact path. Delegates to ArtifactResolver."""
        return self.artifact_resolver.resolve_required_artifact_path(artifact, variables)

    def _load_artifact_row_safe(self, path: str) -> dict[str, Any] | None:
        """Best-effort DB artifact-row loader. Delegates to ArtifactResolver."""
        return self.artifact_resolver.load_artifact_row_safe(path)

    def _build_artifact_handoff_manifest(
        self,
        node_id: str,
        required_artifacts: list[str],
    ) -> list[dict[str, Any]]:
        """Build deterministic handoff metadata. Delegates to ArtifactResolver."""
        return self.artifact_resolver.build_artifact_handoff_manifest(node_id, required_artifacts)

    # Template Variable Resolution

    def _build_contract_variables(self, node_id: str) -> dict[str, str]:
        """Build complete variables dictionary for contract/output resolution."""
        return build_contract_variables(
            node_id,
            session=self.session,
            snapshot=self.snapshot,
            project_root=self.project_root,
            artifacts_dir=self.artifacts_dir,
            pixl_dir=self.pixl_dir,
            get_stage_config=self._get_stage_config,
            workspace_root=self._workspace_root,
        )

    def _resolve_contract_data(self, contract_data: dict, node_id: str) -> dict:
        """Resolve template variables in contract data."""
        return resolve_contract_data(
            contract_data,
            node_id,
            build_variables=self._build_contract_variables,
        )

    def _load_session_artifact_safe(self, path: str) -> str | None:
        """Best-effort session artifact loader for DB-first validation hooks."""
        try:
            return self.store.load_artifact(self.session.id, path)
        except Exception:
            return None

    def _save_session_artifact_safe(self, path: str, content: str) -> None:
        """Best-effort session artifact saver for auto-registration during validation."""
        try:
            self.store.save_artifact(self.session.id, path, content)
        except Exception:
            logger.debug("Failed to auto-register artifact %s", path, exc_info=True)

    # Contract & Frozen Artifact Validation

    def _get_contract_validator(self):
        """Return the cached ContractValidator, creating it on first use."""
        if self._contract_validator is None:
            from pixl.execution.contract_validator import ContractValidator

            self._contract_validator = ContractValidator(
                project_root=self._workspace_root,
                artifacts_dir=self.artifacts_dir,
                baseline_commit=self.session.baseline_commit,
                artifact_loader=self._load_session_artifact_safe,
                artifact_saver=self._save_session_artifact_safe,
            )
        return self._contract_validator

    def _validate_contract(self, node_id: str) -> ContractValidationResult | None:
        """Validate stage output contract after task completion.

        Args:
            node_id: Node ID to validate

        Returns:
            ContractValidationResult or None if no contract defined
        """
        contract_data = self._stage_contracts.get(node_id)
        if not contract_data:
            return None

        from pixl.models.workflow_config import StageContract

        resolved_data = resolve_contract_data(
            contract_data, node_id, build_variables=self._build_contract_variables
        )
        contract = StageContract.model_validate(resolved_data)
        validator = self._get_contract_validator()

        success_criteria = None
        if contract.verify_success_criteria:
            try:
                backlog = BacklogStore(self.project_root)
                feature = backlog.get_feature(self.session.feature_id)
                if feature:
                    success_criteria = feature.success_criteria
            except Exception as exc:
                self._emit_error_event(
                    StorageError(
                        "Failed to load success criteria",
                        op="load_success_criteria",
                        details=str(exc),
                        metadata={"node_id": node_id, "feature_id": self.session.feature_id},
                        cause=exc,
                    ),
                    node_id=node_id,
                )
                success_criteria = None

        max_context_tokens = None
        try:
            stage_cfg = self._stage_configs.get(node_id, {})
            model = stage_cfg.get("model")
            if model:
                from pixl.providers import ProviderRegistry

                provider, _ = ProviderRegistry().resolve_model_string(model)
                max_context_tokens = provider.max_context_tokens
        except Exception as exc:
            self._emit_error_event(
                StateError(
                    "Failed to resolve model context window",
                    invariant="model_resolution",
                    details=str(exc),
                    cause=exc,
                    metadata={"node_id": node_id, "model": model},  # type: ignore[reportPossiblyUnbound]
                ),
                node_id=node_id,
            )
            max_context_tokens = None

        result = validator.validate(
            contract,
            success_criteria=success_criteria,
            max_context_tokens=max_context_tokens,
        )

        for check in result.git_unavailable_checks:
            self._emit_event(Event.git_unavailable(self.session.id, node_id, check))

        if result.warnings:
            for warning in result.warnings:
                self._emit_event(Event.contract_warning(self.session.id, node_id, warning))

        return result

    def _pre_execution_frozen_check(self, node: Node) -> dict | None:
        """Pre-execution check: verify frozen artifacts haven't been modified.

        If the current stage has a change_request_target, frozen artifacts
        belonging to that target are exempt from validation.

        Args:
            node: Node about to be executed

        Returns:
            Failure result dict if violated, None if passed
        """
        if not self.session.frozen_artifacts:
            return None

        # Determine which frozen artifacts to check
        frozen_to_check = dict(self.session.frozen_artifacts)

        # If this stage has change_request_target, skip those artifacts
        stage_config = self._stage_configs.get(node.id, {})
        change_request_target = stage_config.get("change_request_target")
        if change_request_target:
            target_config = self._stage_configs.get(change_request_target, {})
            variables = self._build_contract_variables(change_request_target)
            exempt_paths = {
                resolve_template_string(p, variables)
                for p in target_config.get("freeze_artifacts", [])
            }
            frozen_to_check = {
                path: h for path, h in frozen_to_check.items() if path not in exempt_paths
            }

        if not frozen_to_check:
            return None

        validator = self._get_contract_validator()
        result = validator.validate_frozen_artifacts(frozen_to_check)

        if result.passed:
            return None

        events = []
        for v in result.violations:
            events.append(
                Event.frozen_artifact_violated(
                    self.session.id,
                    node.id,
                    path=v.message.split(":")[0] if ":" in v.message else v.message,
                    expected_hash="",
                    actual_hash=None,
                )
            )

        return {
            "success": False,
            "state": NodeState.TASK_FAILED,
            "result_state": "failed",
            "failure_kind": "frozen_violation",
            "events": events,
            "error": "; ".join(result.violation_messages),
        }

    def _build_frozen_context(self) -> str:
        """Build frozen artifact context for prompt injection."""
        return build_frozen_context(
            frozen_artifacts=self.session.frozen_artifacts,
            artifacts_dir=self.artifacts_dir,
            project_root=self.project_root,
            emit_error_event=self._emit_error_event,
        )

    def _build_change_request_context(self, node: Node) -> str:
        """Build change request context for prompt injection."""
        return build_change_request_context(
            node,
            stage_configs=self._stage_configs,
            artifacts_dir=self.artifacts_dir,
            build_variables=self._build_contract_variables,
        )

    # Gate Rejection & Prompt Building (convenience wrappers binding self.*)

    def _write_rejection_feedback(self, gate_id: str) -> None:
        """Write gate rejection feedback to artifact file."""
        write_rejection_feedback(
            gate_id,
            store=self.store,
            session=self.session,
            snapshot=self.snapshot,
            artifacts_dir=self.artifacts_dir,
        )

    def _build_rejection_feedback_context(self, node: Node) -> str:
        """Build rejection feedback context for revision passes."""
        return build_rejection_feedback_context(
            node,
            snapshot=self.snapshot,
            artifacts_dir=self.artifacts_dir,
            store=self.store,
            session_id=self.session.id,
        )

    def _build_task_prompt(
        self,
        node: Node,
        artifact_handoff_manifest: list[dict[str, Any]] | None = None,
    ) -> str:
        """Build prompt for a task node using the unified context compiler."""
        return build_unified_prompt(
            node,
            session=self.session,
            snapshot=self.snapshot,
            project_root=self.project_root,
            artifacts_dir=self.artifacts_dir,
            pixl_dir=self.pixl_dir,
            stage_configs=self._stage_configs,
            summarizer=self._artifact_summarizer,
            differ=self._artifact_differ,
            workspace_root=self._workspace_root,
            store=self.store,
            artifact_handoff_manifest=artifact_handoff_manifest,
        )

    def _load_feature_context(self, node_id: str | None = None) -> tuple[str, str]:
        """Load feature title and description, failing fast on data corruption."""
        return load_feature_context(
            session=self.session,
            project_root=self.project_root,
            snapshot=self.snapshot,
            node_id=node_id,
        )

    def _execute_gate(self, node: Node, instance: dict) -> dict:
        """Execute a gate node (wait for human approval).

        Args:
            node: Node definition
            instance: Node instance

        Returns:
            Execution result
        """
        instance["state"] = NodeState.GATE_WAITING.value
        instance["ready_at"] = datetime.now().isoformat()

        gate_config = node.gate_config
        required_artifacts = gate_config.required_artifacts if gate_config else []

        return {
            "success": False,  # Waiting for human
            "state": NodeState.GATE_WAITING,
            "result_state": "waiting",
            "events": [],
            "final_event_type": EventType.GATE_REQUESTED,
            "final_event_payload": {
                "artifacts": required_artifacts,
            },
        }

    def _execute_hook(self, node: Node, instance: dict) -> dict:
        """Execute a hook node (deterministic Python function).

        Args:
            node: Node definition (must have hook_config)
            instance: Node instance

        Returns:
            Execution result with events
        """
        from pixl.execution.hooks import HookContext, get_hook

        events: list[Event] = []
        persisted_events: list[Event] = []

        cursor = self.session.executor_cursor
        if cursor:
            cursor.remove_from_ready_queue(node.id)

        update_node_instance_state(self.session, node.id, NodeState.TASK_RUNNING, {})
        start_event = self._commit_transition(
            event_type=EventType.TASK_STARTED,
            node_id=node.id,
            payload={},
            from_state=None,
            to_state=NodeState.TASK_RUNNING,
        )
        persisted_events.append(start_event)

        hook_fn = get_hook(node.hook_config.hook_id)
        if not hook_fn:
            error = f"Unknown hook: {node.hook_config.hook_id}"
            return self._make_failure_result(
                error,
                events=events,
                persisted_events=persisted_events,
            )

        ctx = HookContext(
            session=self.session,
            project_root=self.project_root,
            session_dir=self.session_dir,
            artifacts_dir=self.artifacts_dir,
            feature_id=self.session.feature_id or "",
            params=node.hook_config.params,
        )

        result = hook_fn(ctx)

        if result.workspace_root:
            self.session.workspace_root = result.workspace_root
            self.project_root = Path(result.workspace_root)
            from pixl.storage.workflow_session_store import WorkflowSessionStore

            self.store = WorkflowSessionStore(self.project_root)

        if result.success:
            return {
                "success": True,
                "state": NodeState.TASK_COMPLETED,
                "result_state": "success",
                "events": events,
                "persisted_events": persisted_events,
                "final_event_type": EventType.TASK_COMPLETED,
                "final_event_payload": {},
            }
        return self._make_failure_result(
            result.error or "Hook failed",
            events=events,
            persisted_events=persisted_events,
        )

    # Sub-Workflow Execution

    # Maximum sub-workflow nesting depth to prevent circular references
    _MAX_SUB_WORKFLOW_DEPTH = 5

    def _execute_sub_workflow(self, node: Node, instance: dict, *, _depth: int = 0) -> dict:
        """Execute a sub-workflow node by spawning a child GraphExecutor.

        The child workflow:
        - Must be tier=task and routing.sub_invocable=True
        - Shares the parent's artifacts_dir (context.md, design.md available)
        - Has its init block stages pre-marked as completed (skip redundant init)
        - Runs synchronously to completion
        - Maps child success/failure to parent node result

        Args:
            node: Node definition (metadata must contain 'sub_workflow' key)
            instance: Node instance
            _depth: Current nesting depth (internal, for recursion guard)

        Returns:
            Execution result with events
        """
        from pixl.config.workflow_loader import WorkflowLoader

        events: list[Event] = []
        persisted_events: list[Event] = []

        cursor = self.session.executor_cursor
        if cursor:
            cursor.remove_from_ready_queue(node.id)

        update_node_instance_state(self.session, node.id, NodeState.TASK_RUNNING, {})
        start_event = self._commit_transition(
            event_type=EventType.TASK_STARTED,
            node_id=node.id,
            payload={"sub_workflow": node.metadata.get("sub_workflow", "")},
            from_state=None,
            to_state=NodeState.TASK_RUNNING,
        )
        persisted_events.append(start_event)

        # Recursion depth guard
        if _depth >= self._MAX_SUB_WORKFLOW_DEPTH:
            return self._make_failure_result(
                f"Sub-workflow nesting depth exceeded maximum of {self._MAX_SUB_WORKFLOW_DEPTH}",
                events=events,
                persisted_events=persisted_events,
            )

        sub_workflow_id = node.metadata.get("sub_workflow", "")
        if not sub_workflow_id:
            return self._make_failure_result(
                "Sub-workflow node missing 'sub_workflow' metadata",
                events=events,
                persisted_events=persisted_events,
            )

        try:
            loader = WorkflowLoader(self.project_root or Path.cwd())
            child_config = loader.load_workflow(sub_workflow_id)
        except Exception as exc:
            return self._make_failure_result(
                f"Failed to load sub-workflow '{sub_workflow_id}': {exc}",
                events=events,
                persisted_events=persisted_events,
            )

        if child_config.tier is not None:
            from pixl.models.workflow_config import WorkflowTier

            if child_config.tier != WorkflowTier.TASK:
                return self._make_failure_result(
                    f"Sub-workflow '{sub_workflow_id}' has tier '{child_config.tier}', "
                    "only 'task' tier workflows can be invoked as sub-workflows",
                    events=events,
                    persisted_events=persisted_events,
                )
        if child_config.routing and not child_config.routing.sub_invocable:
            return self._make_failure_result(
                f"Sub-workflow '{sub_workflow_id}' is not marked as sub_invocable",
                events=events,
                persisted_events=persisted_events,
            )

        try:
            child_snapshot = loader.convert_to_template(child_config).snapshot
        except Exception as exc:
            return self._make_failure_result(
                f"Failed to build graph for sub-workflow '{sub_workflow_id}': {exc}",
                events=events,
                persisted_events=persisted_events,
            )

        try:
            child_session = self.store.create_session(
                self.session.feature_id or "",
                child_snapshot,
            )
            child_session.workspace_root = self.session.workspace_root
        except Exception as exc:
            return self._make_failure_result(
                f"Failed to create child session for sub-workflow '{sub_workflow_id}': {exc}",
                events=events,
                persisted_events=persisted_events,
            )

        # Pre-mark init block stages as completed (skip redundant init)
        init_stage_ids = _collect_init_stage_ids(child_snapshot)
        for stage_id in init_stage_ids:
            get_or_create_node_instance(child_session, stage_id)
            update_node_instance_state(
                child_session,
                stage_id,
                NodeState.TASK_COMPLETED,
                {"skipped": True, "reason": "parent_context_available"},
            )

        child_session_dir = self.session_dir.parent / child_session.id
        child_session_dir.mkdir(parents=True, exist_ok=True)
        child_executor = GraphExecutor(
            session=child_session,
            snapshot=child_snapshot,
            session_dir=child_session_dir,
            project_root=self.project_root,
            artifacts_dir=self.artifacts_dir,
            orchestrator=self.orchestrator,
            event_callback=self.event_callback,
            session_manager=self.session_manager,
            state_bridge=None,  # Don't propagate state transitions from child
        )
        child_executor._sub_workflow_depth = _depth + 1

        max_steps = 200  # Safety limit
        for _ in range(max_steps):
            step_result = child_executor.step()
            if step_result.get("terminal", False):
                break

        child_status = child_session.compute_status_with_snapshot(child_snapshot)
        if child_status == SessionStatus.COMPLETED:
            return {
                "success": True,
                "state": NodeState.TASK_COMPLETED,
                "result_state": "success",
                "events": events,
                "persisted_events": persisted_events,
                "final_event_type": EventType.TASK_COMPLETED,
                "final_event_payload": {"sub_workflow": sub_workflow_id},
            }
        return self._make_failure_result(
            f"Sub-workflow '{sub_workflow_id}' finished with status: {child_status}",
            events=events,
            persisted_events=persisted_events,
        )

    # Edge Traversal

    # State Management (convenience wrappers binding self.*)

    def _version_stage_outputs(self, node_id: str) -> None:
        """Version stage outputs defined in workflow config."""
        variables = self._build_contract_variables(node_id)
        version_stage_outputs(
            node_id=node_id,
            stage_configs=self._stage_configs,
            session=self.session,
            store=self.store,
            artifacts_dir=self.artifacts_dir,
            project_root=self.project_root,
            variables=variables,
            resolve_template_string=resolve_template_string,
            emit_error_event=self._emit_error_event,
        )

    def _trigger_entity_transition(
        self,
        node_id: str,
        success: bool,
        error: str | None = None,
    ) -> None:
        """Trigger entity state transition via the workflow bridge.

        Called after a task node completes or fails, if a state bridge
        is configured. The bridge resolves the target status from the
        stage's ``transitions`` YAML config or implicit stage-name mapping.

        Args:
            node_id: Stage/node ID that completed
            success: Whether the stage succeeded
            error: Error message if failed
        """
        if not self.state_bridge:
            return

        # Use the source entity ID (epic/roadmap) for state transitions
        # when available, falling back to the session's placeholder feature ID.
        entity_id = (
            self.snapshot.workflow_config.get("variables", {}).get("source_entity_id")
            or self.session.feature_id
        )
        if not entity_id:
            return

        stage_config = self._stage_configs.get(node_id, {})

        try:
            if success:
                self.state_bridge.on_stage_complete(
                    entity_id,
                    node_id,
                    stage_config,
                    session_id=self.session.id,
                )
            else:
                self.state_bridge.on_stage_failed(
                    entity_id,
                    node_id,
                    stage_config,
                    session_id=self.session.id,
                    error=error,
                )
        except Exception as exc:
            self._emit_error_event(
                StateError(
                    "State bridge failed during transition",
                    invariant="state_bridge_transition",
                    details=str(exc),
                    cause=exc,
                    metadata={"node_id": node_id, "entity_id": entity_id},
                ),
                node_id=node_id,
            )

    def _is_terminal(self, status: SessionStatus | None = None) -> bool:
        """Check if execution is complete.

        Args:
            status: Pre-computed session status. If None, will be computed.

        Returns:
            True if in terminal state
        """
        if status is None:
            status = self._compute_status()
        return status in (
            SessionStatus.COMPLETED,
            SessionStatus.FAILED,
            SessionStatus.CANCELLED,
        )

    def _save_checkpoint(self) -> None:
        """Save session checkpoint atomically."""
        self._checkpoint(reason="manual")

    def _mark_session_started(self) -> None:
        """Set started_at on the DB session (idempotent — skips if already set)."""
        self.store.mark_session_started(self.session.id)

    def _mark_session_ended(self) -> None:
        """Set ended_at on the DB session so computed status becomes terminal."""
        self.store.mark_session_ended(self.session.id)

    def _save_session_summary(self) -> None:
        """Generate and save a human-readable session summary."""
        save_session_summary(
            session=self.session,
            snapshot=self.snapshot,
            store=self.store,
            session_dir=self.session_dir,
            artifacts_dir=self.artifacts_dir,
        )


def _collect_init_stage_ids(snapshot: WorkflowSnapshot) -> list[str]:
    """Collect stage IDs from the init block in a workflow snapshot.

    Init block stages typically have IDs like 'detect-context' and 'refine-prompt'.
    These are skipped when the sub-workflow is invoked from a parent that already
    built context.md and design.md.

    Args:
        snapshot: The child workflow snapshot

    Returns:
        List of stage IDs belonging to the init block
    """
    init_ids: list[str] = []
    known_init_stages = {"detect-context", "refine-prompt"}
    for node_id in snapshot.graph.nodes:
        if node_id in known_init_stages:
            init_ids.append(node_id)
    return init_ids


def resume_session(session_dir: Path, project_root: Path | None = None) -> GraphExecutor:
    """Resume a workflow session.

    Args:
        session_dir: Path to session directory
        project_root: Optional project root (repo). If not provided, will attempt
            to infer from session.json's workspace_root field.

    Returns:
        GraphExecutor for the session
    """
    from pixl.storage.workflow_session_store import WorkflowSessionStore

    # Try to resolve project_root from DB session if not provided
    if project_root is None:
        session_file = session_dir / "session.json"
        if session_file.exists():
            try:
                data = json.loads(session_file.read_text())
                file_session = WorkflowSession.model_validate(data)
                if file_session.workspace_root:
                    project_root = Path(file_session.workspace_root)
            except Exception as exc:
                try:
                    event = Event.error(
                        session_dir.name,
                        message="Failed to parse session.json for workspace_root",
                        error_type="storage_error",
                        metadata={"path": str(session_file)},
                        cause=str(exc),
                    )
                    events_file = session_dir / "events.jsonl"
                    with open(events_file, "a", encoding="utf-8") as f:
                        f.write(event.model_dump_json(exclude_none=True) + "\n")
                        f.flush()
                        os.fsync(f.fileno())
                except Exception as exc:
                    # If we can't record the error event, continue with fallback
                    _ = exc
                project_root = None
    if project_root is None:
        raise ValueError(
            f"Cannot determine project root for session {session_dir.name}: "
            "session.json has no workspace_root field"
        )

    store = WorkflowSessionStore(project_root)
    session_id = session_dir.name

    session = store.load_session(session_id)
    if not session:
        raise ValueError(f"Session not found in {session_dir}")

    # Prefer workspace_root from DB session record
    if session.workspace_root:
        project_root = Path(session.workspace_root)

    snapshot = store.load_snapshot(session.id)
    if not snapshot:
        raise ValueError(f"Snapshot not found for session {session.id}")

    return GraphExecutor(session, snapshot, session_dir, project_root=project_root)

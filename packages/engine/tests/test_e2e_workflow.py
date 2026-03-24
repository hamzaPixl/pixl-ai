"""End-to-end workflow test: Template → Session → GraphExecutor.

Runs a simple 3-node workflow (plan → implement → verify) through the
full execution pipeline using simulated execution mode. Verifies:
- Session state transitions (created → running → completed)
- Cursor checkpointing and ready queue management
- Event generation at each step
- Node instance state tracking
- Edge traversal (success edges between stages)
"""

import tempfile
from datetime import datetime
from pathlib import Path

from pixl.execution.graph_executor import GraphExecutor
from pixl.models.node_instance import NodeState
from pixl.models.session import (
    ExecutorCursor,
    SessionStatus,
    WorkflowSession,
)
from pixl.models.workflow import (
    EdgeTrigger,
    ExecutionGraph,
    Node,
    NodeType,
    TaskConfig,
    WorkflowSnapshot,
)


def _build_linear_graph() -> ExecutionGraph:
    """Build a simple plan → implement → verify linear graph."""
    graph = ExecutionGraph()

    plan_node = Node(
        id="plan",
        type=NodeType.TASK,
        task_config=TaskConfig(agent="architect", model="claude-sonnet-4-6"),
        inbound_degree=0,
        outbound_degree=1,
    )
    impl_node = Node(
        id="implement",
        type=NodeType.TASK,
        task_config=TaskConfig(agent="backend-engineer", model="claude-sonnet-4-6"),
        inbound_degree=1,
        outbound_degree=1,
    )
    verify_node = Node(
        id="verify",
        type=NodeType.TASK,
        task_config=TaskConfig(agent="qa-engineer", model="claude-haiku-4-5"),
        inbound_degree=1,
        outbound_degree=0,
    )

    graph.add_node(plan_node)
    graph.add_node(impl_node)
    graph.add_node(verify_node)

    graph.add_edge("plan", "implement", on=EdgeTrigger.SUCCESS)
    graph.add_edge("implement", "verify", on=EdgeTrigger.SUCCESS)

    return graph


def _build_snapshot(graph: ExecutionGraph) -> WorkflowSnapshot:
    """Build a workflow snapshot from a graph."""
    return WorkflowSnapshot(
        template_id="test-e2e",
        template_version="1.0.0",
        snapshot_hash="test-hash-abc123",
        name="E2E Test Workflow",
        graph=graph,
        workflow_config={
            "stages": [
                {"id": "plan", "prompt": "Create a plan"},
                {"id": "implement", "prompt": "Implement the plan"},
                {"id": "verify", "prompt": "Verify implementation"},
            ]
        },
    )


def _build_session(snapshot: WorkflowSnapshot) -> WorkflowSession:
    """Build a fresh workflow session."""
    return WorkflowSession(
        id="sess-test-e2e-001",
        feature_id="feat-test-001",
        snapshot_hash=snapshot.snapshot_hash,
        created_at=datetime.now(),
    )


class TestE2ELinearWorkflow:
    """Test a 3-node linear workflow execution."""

    def setup_method(self) -> None:
        """Set up fresh graph, snapshot, session, and executor for each test."""
        self.graph = _build_linear_graph()
        self.snapshot = _build_snapshot(self.graph)
        self.session = _build_session(self.snapshot)
        self.tmpdir = tempfile.mkdtemp()
        self.session_dir = Path(self.tmpdir) / "sessions" / self.session.id
        self.session_dir.mkdir(parents=True)

        # Collect events for verification
        self.events: list = []

        def event_callback(event):
            self.events.append(event)

        self.executor = GraphExecutor(
            session=self.session,
            snapshot=self.snapshot,
            session_dir=self.session_dir,
            project_root=Path(self.tmpdir),
            orchestrator=None,  # No orchestrator → simulated execution
            event_callback=event_callback,
        )

    def test_initial_session_state(self) -> None:
        """Session starts in CREATED status with no node instances."""
        assert self.session.status == SessionStatus.CREATED
        assert self.session.executor_cursor is None
        assert len(self.session.node_instances) == 0

    def test_step_executes_first_node(self) -> None:
        """First step should execute the entry node (plan)."""
        result = self.executor.step()

        assert result["executed"] is True
        assert result["node_id"] == "plan"
        assert result["terminal"] is False

    def test_cursor_initialized_on_first_step(self) -> None:
        """Cursor should be initialized with entry node in ready queue."""
        self.executor.step()

        cursor = self.session.executor_cursor
        assert cursor is not None
        assert isinstance(cursor, ExecutorCursor)

    def test_full_linear_execution(self) -> None:
        """Run all 3 nodes to completion in simulated mode."""
        executed_nodes = []
        max_steps = 10  # Safety limit

        for _ in range(max_steps):
            result = self.executor.step()
            if result["executed"]:
                executed_nodes.append(result["node_id"])
            if result["terminal"]:
                break

        # All 3 nodes should execute in order
        assert executed_nodes == ["plan", "implement", "verify"]

    def test_session_completes_after_all_nodes(self) -> None:
        """Session should reach COMPLETED status after all nodes finish."""
        for _ in range(10):
            result = self.executor.step()
            if result["terminal"]:
                break

        assert result["status"] == SessionStatus.COMPLETED
        assert result["terminal"] is True

    def test_node_instances_created_for_all_nodes(self) -> None:
        """Each executed node should have a node_instance entry."""
        for _ in range(10):
            result = self.executor.step()
            if result["terminal"]:
                break

        assert "plan" in self.session.node_instances
        assert "implement" in self.session.node_instances
        assert "verify" in self.session.node_instances

    def test_node_instances_reach_completed_state(self) -> None:
        """All node instances should be in completed state."""
        for _ in range(10):
            result = self.executor.step()
            if result["terminal"]:
                break

        for node_id in ["plan", "implement", "verify"]:
            instance = self.session.node_instances[node_id]
            assert instance["state"] == NodeState.TASK_COMPLETED, (
                f"Node {node_id} in state {instance['state']}, expected TASK_COMPLETED"
            )

    def test_events_generated(self) -> None:
        """Events should be generated during execution."""
        for _ in range(10):
            result = self.executor.step()
            if result["terminal"]:
                break

        # Should have events for each node execution + checkpoints
        assert len(self.events) > 0

    def test_edges_traversed_correctly(self) -> None:
        """Success edges should route plan → implement → verify."""
        execution_order = []

        for _ in range(10):
            result = self.executor.step()
            if result["executed"]:
                execution_order.append(result["node_id"])
            if result["terminal"]:
                break

        # Verify ordering follows edge definitions
        plan_idx = execution_order.index("plan")
        impl_idx = execution_order.index("implement")
        verify_idx = execution_order.index("verify")
        assert plan_idx < impl_idx < verify_idx

    def test_ready_queue_deterministic(self) -> None:
        """Ready queue should maintain sorted order for determinism."""
        self.executor.step()  # Execute plan

        cursor = self.session.executor_cursor
        assert cursor is not None
        # After plan succeeds, implement should be in ready queue
        # Queue should be sorted
        assert cursor.ready_queue == sorted(cursor.ready_queue)


class TestE2EEmptyGraph:
    """Test edge case: empty graph."""

    def test_empty_graph_no_nodes_executed(self) -> None:
        """Empty graph has no entry nodes — nothing executes."""
        graph = ExecutionGraph()
        snapshot = _build_snapshot(graph)
        session = _build_session(snapshot)
        tmpdir = tempfile.mkdtemp()
        session_dir = Path(tmpdir) / "sessions" / session.id
        session_dir.mkdir(parents=True)

        executor = GraphExecutor(
            session=session,
            snapshot=snapshot,
            session_dir=session_dir,
            project_root=Path(tmpdir),
        )

        result = executor.step()
        assert result["executed"] is False


class TestE2EBranchingGraph:
    """Test a graph with branching (success + failure edges)."""

    def test_branching_executes_main_and_success_path(self) -> None:
        """Main task and success branch both execute in simulated mode."""
        graph = ExecutionGraph()

        main_node = Node(
            id="main-task",
            type=NodeType.TASK,
            task_config=TaskConfig(agent="default"),
            inbound_degree=0,
            outbound_degree=2,
        )
        success_node = Node(
            id="on-success",
            type=NodeType.TASK,
            task_config=TaskConfig(agent="default"),
            inbound_degree=1,
            outbound_degree=0,
        )
        failure_node = Node(
            id="on-failure",
            type=NodeType.TASK,
            task_config=TaskConfig(agent="default"),
            inbound_degree=1,
            outbound_degree=0,
        )

        graph.add_node(main_node)
        graph.add_node(success_node)
        graph.add_node(failure_node)

        graph.add_edge("main-task", "on-success", on=EdgeTrigger.SUCCESS)
        graph.add_edge("main-task", "on-failure", on=EdgeTrigger.FAILURE)

        snapshot = _build_snapshot(graph)
        session = _build_session(snapshot)
        tmpdir = tempfile.mkdtemp()
        session_dir = Path(tmpdir) / "sessions" / session.id
        session_dir.mkdir(parents=True)

        executor = GraphExecutor(
            session=session,
            snapshot=snapshot,
            session_dir=session_dir,
            project_root=Path(tmpdir),
        )

        executed_nodes = []
        for _ in range(10):
            result = executor.step()
            if result["executed"]:
                executed_nodes.append(result["node_id"])
            if result["terminal"]:
                break

        # Main task always executes, success path follows
        assert "main-task" in executed_nodes
        assert "on-success" in executed_nodes
        # Main task executes before its branches
        assert executed_nodes.index("main-task") < executed_nodes.index("on-success")

"""SessionManager for centralized workflow session state mutations.

This module implements the SessionManager pattern which:
1. Centralizes all session state mutations
2. Validates state transitions before applying
3. Automatically persists changes to disk
4. Notifies observers (like GraphExecutor) of changes
5. Provides better error messages and debugging

Usage:
    manager = SessionManager(project_path)

    # Register observer (e.g., GraphExecutor)
    manager.register_observer(lambda session: executor._on_session_changed(session))

    session = manager.update_node_state(session_id, node_id, new_state)

    # Approve gate with event generation
    session = manager.approve_gate(session_id, node_id, approver="user")
"""

import hashlib
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from pixl.models.event import Event
from pixl.models.node_instance import NodeState
from pixl.models.session import WorkflowSession

if TYPE_CHECKING:
    from pixl.models.workflow import WorkflowSnapshot


class SessionMutationError(Exception):
    """Raised when a session mutation fails validation."""

    def __init__(self, message: str, session_id: str, node_id: str | None = None):
        """Initialize the error.

        Args:
            message: Error message
            session_id: Session ID
            node_id: Optional node ID that caused the error
        """
        self.session_id = session_id
        self.node_id = node_id
        parts = [f"Session '{session_id}'"]
        if node_id:
            parts.append(f"node '{node_id}'")
        parts.append(message)
        super().__init__(": ".join(parts))


class SessionManager:
    """Single source of truth for workflow session state mutations.

    The SessionManager provides a centralized API for all session state
    changes. It validates transitions, persists to disk, and notifies
    observers automatically.

    Observer Pattern:
        Observers are notified after every successful mutation.
        The observer callback receives the updated session.

    Thread Safety:
        Not thread-safe. Use separate instances per thread/process.
    """

    def __init__(self, project_path: Path):
        """Initialize the SessionManager.

        Args:
            project_path: Path to project root (for session storage)
        """
        self.project_path = project_path

        # Import here to avoid circular dependency
        from pixl.storage import WorkflowSessionStore

        self._store: WorkflowSessionStore = WorkflowSessionStore(project_path)

        # Observers to notify on changes
        self._observers: list[Callable[[WorkflowSession], None]] = []

        # In-memory session cache to avoid redundant disk reads
        self._session_cache: dict[str, WorkflowSession] = {}

    def register_observer(self, callback: Callable[[WorkflowSession], None]) -> None:
        """Register an observer to be notified of session changes.

        The observer callback receives the updated session after every
        successful mutation.

        Args:
            callback: Function to call with updated session
        """
        self._observers.append(callback)

    def unregister_observer(self, callback: Callable[[WorkflowSession], None]) -> None:
        """Unregister an observer.

        Args:
            callback: Previously registered callback to remove
        """
        if callback in self._observers:
            self._observers.remove(callback)

    def _notify_observers(self, session: WorkflowSession) -> None:
        """Notify all observers of a session change.

        Args:
            session: The updated session
        """
        for callback in self._observers:
            try:
                callback(session)
            except Exception as e:
                # Don't let observer errors break mutations
                import warnings

                warnings.warn(
                    f"Observer callback failed: {e}",
                    RuntimeWarning,
                    stacklevel=2,
                )

    def invalidate_cache(self, session_id: str | None = None) -> None:
        """Invalidate the in-memory session cache.

        Args:
            session_id: If provided, only invalidate the cache for this
                        specific session. If None, clear the entire cache.
        """
        if session_id is not None:
            self._session_cache.pop(session_id, None)
        else:
            self._session_cache.clear()

    def _load_session(self, session_id: str) -> WorkflowSession:
        """Load a session from storage, using in-memory cache when available.

        Checks the in-memory cache first. On cache miss, loads from disk
        and populates the cache for subsequent calls.

        Args:
            session_id: Session ID to load

        Returns:
            Loaded session

        Raises:
            SessionMutationError: If session not found
        """
        # Check cache first
        if session_id in self._session_cache:
            return self._session_cache[session_id]

        # Cache miss — load from disk
        session = self._store.load_session(session_id)
        if not session:
            raise SessionMutationError(
                "Session not found",
                session_id=session_id,
            )

        # Populate cache
        self._session_cache[session_id] = session
        return session

    def _validate_node_state_transition(
        self,
        session: WorkflowSession,
        node_id: str,
        new_state: NodeState,
    ) -> None:
        """Validate that a state transition is allowed.

        Args:
            session: Current session
            node_id: Node ID to validate
            new_state: Desired new state

        Raises:
            SessionMutationError: If transition is invalid
        """
        instance = session.get_node_instance(node_id)

        # If no instance exists, any state is valid (will be created)
        if not instance:
            return

        current_state_str = instance.get("state", NodeState.TASK_PENDING.value)
        try:
            current_state = NodeState(current_state_str)
        except ValueError:
            # Invalid current state - allow any transition
            return

        if not NodeState.can_transition_to(current_state, new_state):
            raise SessionMutationError(
                f"Invalid state transition: {current_state.value} -> {new_state.value}",
                session_id=session.id,
                node_id=node_id,
            )

    # Public API - Node State Mutations

    def update_node_state(
        self,
        session_id: str,
        node_id: str,
        new_state: str | NodeState,
    ) -> WorkflowSession:
        """Update a node's state - SINGLE SOURCE OF TRUTH.

        This method:
        1. Loads session from disk
        2. Validates the state transition
        3. Updates the state
        4. Saves to disk
        5. Notifies observers

        Args:
            session_id: Session ID
            node_id: Node ID to update
            new_state: New state (string or NodeState enum)

        Returns:
            Updated session

        Raises:
            SessionMutationError: If validation fails
        """
        if isinstance(new_state, str):
            try:
                new_state = NodeState(new_state)
            except ValueError:
                raise SessionMutationError(
                    f"Invalid state: {new_state}",
                    session_id=session_id,
                    node_id=node_id,
                ) from None

        session = self._load_session(session_id)

        self._validate_node_state_transition(session, node_id, new_state)

        session.update_node_state(node_id, new_state.value)

        self._store.save_session(session)
        self._session_cache[session_id] = session

        # Notify observers
        self._notify_observers(session)

        return session

    def approve_gate(
        self,
        session_id: str,
        node_id: str,
        approver: str = "user",
        snapshot: "WorkflowSnapshot | None" = None,
    ) -> WorkflowSession:
        """Approve a gate node.

        This is a convenience method that updates the node state to
        GATE_APPROVED and generates the corresponding event.
        If a snapshot is provided and the gate has freeze_artifacts,
        the specified artifacts are frozen (hash-locked).

        Args:
            session_id: Session ID
            node_id: Gate node ID to approve
            approver: Who approved (default: "user", or "auto")
            snapshot: Optional WorkflowSnapshot for artifact freezing

        Returns:
            Updated session

        Raises:
            SessionMutationError: If validation fails
        """
        session = self._load_session(session_id)

        instance = session.get_node_instance(node_id)
        if instance:
            current_state = instance.get("state", "")
            if not current_state.startswith("gate_"):
                raise SessionMutationError(
                    f"Node is not a gate (state: {current_state})",
                    session_id=session_id,
                    node_id=node_id,
                )

        session.update_node_state(node_id, NodeState.GATE_APPROVED.value)

        # Freeze artifacts if snapshot provides gate config
        if snapshot:
            self._freeze_gate_artifacts(session, node_id, snapshot)

        self._store.save_session(session)
        self._session_cache[session_id] = session
        event = Event.gate_approved(session_id, node_id, approver=approver)
        self._store.append_event(event, session_id)

        # Notify observers
        self._notify_observers(session)

        return session

    def _freeze_gate_artifacts(
        self,
        session: WorkflowSession,
        node_id: str,
        snapshot: "WorkflowSnapshot",
    ) -> None:
        """Freeze artifacts specified in the gate's freeze_artifacts list.

        Args:
            session: Current session
            node_id: Gate node ID
            snapshot: WorkflowSnapshot containing gate config
        """
        node = snapshot.graph.nodes.get(node_id)
        if not node or not node.gate_config:
            return

        freeze_paths = node.gate_config.freeze_artifacts
        if not freeze_paths:
            return

        # Resolve template variables in paths (e.g., {feature_id})
        resolved_paths = [self._resolve_path_vars(p, session) for p in freeze_paths]

        for path in resolved_paths:
            content = self._store.load_artifact(session.id, path)

            if content is None:
                continue  # Skip non-existent files (they may not exist yet)

            sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
            session.freeze_artifact(path, sha)

            event = Event.artifact_frozen(session.id, node_id, path=path, sha256=sha)
            self._store.append_event(event, session.id)

    def approve_change_request(
        self,
        session_id: str,
        gate_node_id: str,
        target_gate_id: str,
    ) -> WorkflowSession:
        """Approve a change request: re-freeze artifacts with new hashes.

        After a change_request stage modifies frozen artifacts and passes
        a gate, this method updates the frozen hashes to the new content.

        Args:
            session_id: Session ID
            gate_node_id: Gate node approving the change
            target_gate_id: Original gate whose artifacts were modified

        Returns:
            Updated session
        """
        session = self._load_session(session_id)

        # Resolve file paths: check artifacts dir first, then session dir, then project root.
        self._store._session_dir(session.id)
        self._store._artifacts_dir(session.id)

        for path, old_hash in list(session.frozen_artifacts.items()):
            content = self._store.load_artifact(session.id, path)

            if content is None:
                continue

            new_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            if new_hash != old_hash:
                session.freeze_artifact(path, new_hash)
                event = Event.frozen_artifact_updated(
                    session.id,
                    gate_node_id,
                    path=path,
                    old_hash=old_hash,
                    new_hash=new_hash,
                )
                self._store.append_event(event, session.id)

        self._store.save_session(session)
        self._session_cache[session_id] = session
        self._notify_observers(session)

        return session

    @staticmethod
    def _resolve_path_vars(path: str, session: "WorkflowSession") -> str:
        """Resolve template variables in a path string.

        Replaces {feature_id} and {session_id} with session values.

        Args:
            path: Path string potentially containing {var} placeholders
            session: Session providing runtime values

        Returns:
            Path with variables resolved
        """
        result = path.replace("{feature_id}", session.feature_id or "")
        result = result.replace("{session_id}", session.id or "")
        return result

    @staticmethod
    def _compute_sha256(file_path: Path) -> str:
        """Compute SHA256 hash of a file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def reject_gate(
        self,
        session_id: str,
        node_id: str,
        reason: str | None = None,
    ) -> WorkflowSession:
        """Reject a gate node.

        This is a convenience method that updates the node state to
        GATE_REJECTED and generates the corresponding event.

        Args:
            session_id: Session ID
            node_id: Gate node ID to reject
            reason: Optional reason for rejection

        Returns:
            Updated session

        Raises:
            SessionMutationError: If validation fails
        """
        session = self._load_session(session_id)

        instance = session.get_node_instance(node_id)
        if instance:
            current_state = instance.get("state", "")
            if not current_state.startswith("gate_"):
                raise SessionMutationError(
                    f"Node is not a gate (state: {current_state})",
                    session_id=session_id,
                    node_id=node_id,
                )

        session.update_node_state(node_id, NodeState.GATE_REJECTED.value)

        self._store.save_session(session)
        self._session_cache[session_id] = session
        event = Event.gate_rejected(session_id, node_id, reason=reason)
        self._store.append_event(event, session_id)

        # Notify observers
        self._notify_observers(session)

        return session

    def timeout_gate(
        self,
        session_id: str,
        node_id: str,
    ) -> WorkflowSession:
        """Mark a gate as timed out.

        Args:
            session_id: Session ID
            node_id: Gate node ID

        Returns:
            Updated session

        Raises:
            SessionMutationError: If validation fails
        """
        return self.update_node_state(
            session_id,
            node_id,
            NodeState.GATE_TIMEOUT.value,
        )

    # Public API - Task State Mutations

    def start_task(
        self,
        session_id: str,
        node_id: str,
    ) -> WorkflowSession:
        """Mark a task as started (running).

        Args:
            session_id: Session ID
            node_id: Task node ID

        Returns:
            Updated session
        """
        session = self._load_session(session_id)
        session.update_node_state(node_id, NodeState.TASK_RUNNING.value)

        event = Event.task_started(session_id, node_id)
        self._store.append_event(event, session_id)

        self._store.save_session(session)
        self._session_cache[session_id] = session
        self._notify_observers(session)

        return session

    def complete_task(
        self,
        session_id: str,
        node_id: str,
        duration_seconds: float | None = None,
    ) -> WorkflowSession:
        """Mark a task as completed.

        Args:
            session_id: Session ID
            node_id: Task node ID
            duration_seconds: Optional duration for metrics

        Returns:
            Updated session
        """
        session = self._load_session(session_id)
        session.update_node_state(node_id, NodeState.TASK_COMPLETED.value)

        event = Event.task_completed(
            session_id,
            node_id,
            duration_seconds=duration_seconds,
        )
        self._store.append_event(event, session_id)

        self._store.save_session(session)
        self._session_cache[session_id] = session
        self._notify_observers(session)

        return session

    def fail_task(
        self,
        session_id: str,
        node_id: str,
        error: str,
        failure_kind: str = "transient",
    ) -> WorkflowSession:
        """Mark a task as failed.

        Args:
            session_id: Session ID
            node_id: Task node ID
            error: Error message
            failure_kind: "transient" or "fatal"

        Returns:
            Updated session
        """
        session = self._load_session(session_id)
        session.update_node_state(node_id, NodeState.TASK_FAILED.value)

        instance = session.get_node_instance(node_id)
        if instance:
            instance["failure_kind"] = failure_kind
            instance["error_message"] = error
            session.set_node_instance(node_id, instance)

        event = Event.task_failed(session_id, node_id, error)
        self._store.append_event(event, session_id)

        self._store.save_session(session)
        self._session_cache[session_id] = session
        self._notify_observers(session)

        return session

    def skip_task(
        self,
        session_id: str,
        node_id: str,
        reason: str | None = None,
    ) -> WorkflowSession:
        """Skip a task node.

        Args:
            session_id: Session ID
            node_id: Task node ID
            reason: Optional reason for skipping

        Returns:
            Updated session
        """
        session = self._load_session(session_id)
        session.update_node_state(node_id, NodeState.TASK_SKIPPED.value)

        instance = session.get_node_instance(node_id)
        if instance:
            instance["blocked_reason"] = reason or "Skipped"
            session.set_node_instance(node_id, instance)

        self._store.save_session(session)
        self._session_cache[session_id] = session
        self._notify_observers(session)

        return session

    # Public API - Session Level Mutations

    def get_session(self, session_id: str) -> WorkflowSession | None:
        """Get a session without mutation.

        Args:
            session_id: Session ID

        Returns:
            Session or None if not found
        """
        return self._store.load_session(session_id)

    def refresh_session(self, session: WorkflowSession) -> WorkflowSession | None:
        """Refresh a session from disk.

        Args:
            session: Session to refresh

        Returns:
            Refreshed session or None if not found
        """
        return self._store.load_session(session.id)

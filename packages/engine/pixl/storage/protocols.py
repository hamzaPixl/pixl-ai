"""Storage protocol interfaces for Pixl.

These Protocol classes define the contracts that ANY storage backend
must satisfy. Callers depend on these interfaces, never on concrete
implementations. This enables swapping SQLite for PostgreSQL, DuckDB,
or even a remote API without changing any calling code.

Architecture (Onion / Ports & Adapters):

    Callers (CLI, orchestration, execution)
        │
        ▼
    protocols.py  ← You are here (ports / interfaces)
        │
        ▼
    db/           ← SQLite adapter (current)
    pg/           ← PostgreSQL adapter (future)
    api/          ← Remote API adapter (future)

Usage:
    from pixl.storage.protocols import StorageBackend, BacklogStore

    def plan_feature(store: BacklogStore, feature_id: str) -> None:
        feature = store.get_feature(feature_id)
        deps_met, unmet = store.check_dependencies_met(feature_id)
        ...

    def init_storage(project_path: Path) -> StorageBackend:
        from pixl.storage import create_storage
        return create_storage(project_path)
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

# Backlog store (roadmaps, epics, features)


@runtime_checkable
class BacklogStore(Protocol):
    """Interface for roadmap -> epic -> feature hierarchy management."""

    def add_roadmap(
        self,
        title: str,
        original_prompt: str = "",
        status: str = "drafting",
    ) -> dict[str, Any]: ...

    def get_roadmap(self, roadmap_id: str) -> dict[str, Any] | None: ...

    def update_roadmap(self, roadmap_id: str, **fields: Any) -> bool: ...

    def update_roadmap_status(
        self,
        roadmap_id: str,
        status: str,
        note: str | None = None,
        trigger: str | None = None,
    ) -> dict[str, Any] | None: ...

    def list_roadmaps(self, status: str | None = None) -> list[dict[str, Any]]: ...

    def add_milestone(
        self,
        roadmap_id: str,
        name: str,
        target_date: str | None = None,
        sort_order: int = 0,
    ) -> dict[str, Any]: ...

    def add_epic(
        self,
        title: str,
        original_prompt: str = "",
        workflow_id: str | None = None,
        outcome: str = "",
        kpis: list[dict[str, Any]] | None = None,
        roadmap_id: str | None = None,
        milestone_id: int | None = None,
        status: str = "drafting",
    ) -> dict[str, Any]: ...

    def get_epic(self, epic_id: str) -> dict[str, Any] | None: ...

    def update_epic(self, epic_id: str, **fields: Any) -> bool: ...

    def update_epic_status(
        self,
        epic_id: str,
        status: str,
        note: str | None = None,
        trigger: str | None = None,
    ) -> dict[str, Any] | None: ...

    def list_epics(
        self,
        status: str | None = None,
        roadmap_id: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def add_feature(
        self,
        title: str,
        description: str = "",
        feature_type: str = "feature",
        priority: str = "P2",
        depends_on: list[str] | None = None,
        epic_id: str | None = None,
        roadmap_id: str | None = None,
        acceptance_criteria: list[str] | None = None,
        status: str = "backlog",
    ) -> dict[str, Any]: ...

    def get_feature(self, feature_id: str) -> dict[str, Any] | None: ...

    def update_feature(self, feature_id: str, **fields: Any) -> bool: ...

    def update_feature_status(
        self,
        feature_id: str,
        status: str,
        note: str | None = None,
        trigger: str | None = None,
        trigger_id: str | None = None,
    ) -> dict[str, Any] | None: ...

    def remove_feature(self, feature_id: str) -> bool: ...

    def list_features(
        self,
        status: str | None = None,
        epic_id: str | None = None,
        roadmap_id: str | None = None,
        priority: str | None = None,
        feature_type: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def get_stats(self) -> dict[str, Any]: ...

    def get_dependency_graph(self, epic_id: str | None = None) -> dict[str, list[str]]: ...

    def get_execution_order(self, epic_id: str) -> list[str]: ...

    def get_unblocked_features(self, epic_id: str | None = None) -> list[dict[str, Any]]: ...

    def check_dependencies_met(self, feature_id: str) -> tuple[bool, list[str]]: ...

    def add_note(self, entity_type: str, entity_id: str, content: str) -> None: ...


# Knowledge / RAG store


@runtime_checkable
class KnowledgeStore(Protocol):
    """Interface for knowledge indexing and FTS search."""

    def upsert_document(self, path: str, content_hash: str) -> int: ...

    def get_document(self, path: str) -> dict[str, Any] | None: ...

    def get_changed_documents(self, file_hashes: dict[str, str]) -> list[str]: ...

    def remove_stale_documents(self, current_paths: set[str]) -> int: ...

    def add_chunk(
        self,
        chunk_id: str,
        document_id: int,
        title: str,
        content: str,
        source: str,
        chunk_type: str = "concept",
        keywords: list[str] | None = None,
        line_start: int | None = None,
        line_end: int | None = None,
    ) -> None: ...

    def remove_chunks_for_document(self, document_id: int) -> int: ...

    def add_chunks_batch(self, chunks: list[dict[str, Any]], document_id: int) -> int: ...
    def list_chunks(self) -> list[dict[str, Any]]: ...

    def search(
        self,
        query: str,
        limit: int = 5,
        chunk_types: list[str] | None = None,
        source_filter: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def search_for_context(
        self,
        query: str,
        max_tokens: int = 4000,
        chunk_types: list[str] | None = None,
    ) -> str: ...

    def search_for_feature(
        self,
        title: str,
        description: str = "",
        max_tokens: int = 3000,
    ) -> str: ...

    def update_manifest(
        self,
        chunk_count: int,
        source_count: int,
        build_duration_ms: int,
    ) -> None: ...

    def get_manifest(self) -> dict[str, Any] | None: ...

    def get_status(self) -> dict[str, Any]: ...

    def clear(self) -> None: ...


# Artifact store


@runtime_checkable
class ArtifactStore(Protocol):
    """Interface for artifact storage with full-text search."""

    def put(
        self,
        *,
        session_id: str,
        logical_path: str,
        content: str | None,
        artifact_type: str = "other",
        task_id: str = "manual",
        name: str | None = None,
        feature_id: str | None = None,
        epic_id: str | None = None,
        tags: list[str] | None = None,
        extra: dict[str, Any] | None = None,
        version: str | None = None,
        previous_version_id: str | None = None,
        change_description: str | None = None,
        mime_type: str | None = None,
    ) -> dict[str, Any]: ...

    def get_by_session_path(self, session_id: str, logical_path: str) -> dict[str, Any] | None: ...

    def list_page(
        self,
        *,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]: ...

    def materialize(self, *, session_id: str, logical_path: str) -> str | None: ...

    def create(
        self,
        name: str,
        artifact_type: str,
        task_id: str,
        session_id: str,
        content: str | None = None,
        path: str | None = None,
        feature_id: str | None = None,
        epic_id: str | None = None,
        tags: list[str] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    def get(self, artifact_id: str) -> dict[str, Any] | None: ...

    def update(self, artifact_id: str, **fields: Any) -> bool: ...

    def delete(self, artifact_id: str) -> bool: ...

    def list_by_session(self, session_id: str) -> list[dict[str, Any]]: ...

    def list_by_feature(self, feature_id: str) -> list[dict[str, Any]]: ...

    def list_by_type(self, artifact_type: str) -> list[dict[str, Any]]: ...

    def list_by_task(
        self,
        task_id: str,
        session_id: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def find_by_hash(self, content_hash: str) -> dict[str, Any] | None: ...

    def search(
        self,
        query: str,
        limit: int = 5,
        artifact_type: str | None = None,
        feature_id: str | None = None,
        epic_id: str | None = None,
        session_id: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def search_session(
        self,
        *,
        session_id: str,
        query: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]: ...

    def list_by_epic(self, epic_id: str) -> list[dict[str, Any]]: ...

    def list_versions_by_path(
        self, path: str, session_id: str | None = None
    ) -> list[dict[str, Any]]: ...

    def create_version(
        self,
        original_artifact_id: str,
        task_id: str,
        session_id: str,
        content: str | None = None,
        version: str | None = None,
        change_description: str | None = None,
        tags: list[str] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    def get_versions(self, artifact_id: str) -> list[dict[str, Any]]: ...

    def get_version(self, artifact_id: str, version: str) -> dict[str, Any] | None: ...

    def compare_versions(
        self, artifact_id: str, from_version: str, to_version: str
    ) -> dict[str, Any] | None: ...

    def list_versions_by_path_v2(
        self, path: str, session_id: str | None = None
    ) -> list[dict[str, Any]]: ...

    def search_for_context(
        self,
        query: str,
        max_tokens: int = 4000,
        artifact_type: str | None = None,
        feature_id: str | None = None,
    ) -> str: ...


# Event / audit store


@runtime_checkable
class EventStore(Protocol):
    """Interface for state transitions and event logging."""

    def record_transition(
        self,
        entity_type: str,
        entity_id: str,
        from_status: str | None,
        to_status: str,
        trigger: str | None = None,
        trigger_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int: ...

    def get_history(
        self,
        entity_type: str,
        entity_id: str,
        limit: int | None = None,
    ) -> list[dict[str, Any]]: ...

    def get_entity_history(self, entity_id: str) -> list[dict[str, Any]]: ...

    def get_transitions_since(
        self,
        since: str,
        entity_type: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def get_status_at(
        self,
        entity_type: str,
        entity_id: str,
        at_time: str,
    ) -> str | None: ...

    def get_duration_in_status(
        self,
        entity_type: str,
        entity_id: str,
        status: str,
    ) -> float: ...

    def emit(
        self,
        event_type: str,
        session_id: str | None = None,
        node_id: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        payload: dict[str, Any] | None = None,
        created_at: str | None = None,
    ) -> int: ...

    def get_events(
        self,
        session_id: str | None = None,
        event_type: str | None = None,
        entity_id: str | None = None,
        since: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]: ...

    def get_session_events(self, session_id: str) -> list[dict[str, Any]]: ...

    def get_recent_events(self, limit: int = 50) -> list[dict[str, Any]]: ...

    def get_event_counts(
        self,
        session_id: str | None = None,
        since: str | None = None,
    ) -> dict[str, int]: ...

    def get_transition_summary(
        self,
        entity_type: str | None = None,
    ) -> list[dict[str, Any]]: ...


# Session store (workflow + SDK sessions)


@runtime_checkable
class SessionStore(Protocol):
    """Interface for workflow and SDK session management."""

    def create_session(
        self,
        feature_id: str,
        snapshot_hash: str,
        baseline_commit: str | None = None,
        workspace_root: str | None = None,
    ) -> dict[str, Any]: ...

    def get_session(self, session_id: str) -> dict[str, Any] | None: ...

    def update_session(self, session_id: str, **fields: Any) -> bool: ...

    def delete_session(self, session_id: str) -> bool: ...

    def list_sessions(
        self,
        feature_id: str | None = None,
        limit: int | None = None,
        status: str | None = None,
        offset: int | None = None,
    ) -> list[dict[str, Any]]: ...

    def touch_session(self, session_id: str) -> bool: ...

    def get_latest_session(self, feature_id: str | None = None) -> dict[str, Any] | None: ...

    def get_active_sessions(self) -> list[dict[str, Any]]: ...

    def enqueue_session_report_job(
        self,
        *,
        session_id: str,
        trigger: str,
        terminal_status: str | None = None,
        requested_by: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]: ...

    def enqueue_or_get_inflight_session_report_job(
        self,
        *,
        session_id: str,
        trigger: str,
        terminal_status: str | None = None,
        requested_by: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]: ...

    def claim_next_session_report_job(self) -> dict[str, Any] | None: ...

    def get_session_report_job(
        self,
        job_id: str,
        *,
        session_id: str | None = None,
    ) -> dict[str, Any] | None: ...

    def list_session_report_jobs(
        self,
        *,
        session_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]: ...

    def get_inflight_session_report_job(
        self,
        *,
        session_id: str,
        trigger: str | None = None,
    ) -> dict[str, Any] | None: ...

    def complete_session_report_job(self, job_id: str, artifact_id: str) -> bool: ...

    def fail_session_report_job(self, job_id: str, error_message: str) -> bool: ...

    def requeue_session_report_job(self, job_id: str) -> bool: ...

    def requeue_stale_session_report_jobs(self, max_running_seconds: int = 900) -> int: ...

    def list_stalled_running_sessions(
        self, stale_after_seconds: int | None = None
    ) -> list[str]: ...

    def upsert_node_instance(
        self,
        session_id: str,
        node_id: str,
        state: str,
        attempt: int = 0,
        blocked_reason: str | None = None,
        output: dict[str, Any] | None = None,
    ) -> None: ...

    def get_node_instance(self, session_id: str, node_id: str) -> dict[str, Any] | None: ...

    def get_nodes_by_state(self, session_id: str, state: str) -> list[dict[str, Any]]: ...

    def find_sessions_with_failed_nodes(self) -> list[str]: ...

    def unblock_tasks_for_resume(self, session_id: str) -> list[str]: ...

    def upsert_loop_state(
        self,
        session_id: str,
        loop_id: str,
        current_iteration: int,
        max_iterations: int,
        history: list[dict[str, Any]] | None = None,
    ) -> None: ...

    def get_loop_state(self, session_id: str, loop_id: str) -> dict[str, Any] | None: ...

    def save_snapshot(self, snapshot_hash: str, snapshot_json: str) -> None: ...

    def get_snapshot(self, snapshot_hash: str) -> str | None: ...

    def snapshot_exists(self, snapshot_hash: str) -> bool: ...

    def cleanup_orphaned_snapshots(self, active_hashes: set[str]) -> int: ...


# Top-level storage backend


@runtime_checkable
class StorageBackend(Protocol):
    """Top-level interface for the entire storage layer.

    This is the single entry point that callers should depend on.
    It provides access to all domain stores through properties.

    To swap backends, implement this protocol and update the factory
    function in storage/__init__.py.
    """

    @property
    def backlog(self) -> BacklogStore: ...

    @property
    def knowledge(self) -> KnowledgeStore: ...

    @property
    def artifacts(self) -> ArtifactStore: ...

    @property
    def events(self) -> EventStore: ...

    @property
    def sessions(self) -> SessionStore: ...

    def initialize(self) -> None: ...

    def close(self) -> None: ...

    def __enter__(self) -> StorageBackend: ...

    def __exit__(self, *args: Any) -> None: ...

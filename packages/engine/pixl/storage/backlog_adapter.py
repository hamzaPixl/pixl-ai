"""Adapter wrapping SQLite storage with Pydantic model API.

Presents a Pydantic-model API (Feature/Epic/Roadmap) while delegating
to the SQLite backend for persistence.

Usage:
    from pixl.storage import BacklogStore
    store = BacklogStore(project_path)

The adapter converts between:
- SQLite dicts (internal) ↔ Pydantic models (caller-facing)
- Enum values (FeatureStatus) ↔ string status values (SQLite)
- datetime objects ↔ ISO string timestamps (SQLite)
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from pixl.models.backlog import Backlog
from pixl.models.epic import Epic, EpicStatus
from pixl.models.feature import Feature, FeatureStatus, FeatureType, Priority
from pixl.models.roadmap import Roadmap, RoadmapStatus
from pixl.paths import get_pixl_dir

logger = logging.getLogger("pixl.storage.backlog_adapter")


def _parse_dt(value: Any) -> datetime | None:
    """Parse an ISO datetime string to datetime, or return None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def _dict_to_feature(d: dict[str, Any]) -> Feature:
    """Convert SQLite feature dict to Pydantic Feature model.

    Falls back to model_construct (bypasses validation) if Pydantic
    validation fails, to prevent silent data loss on read.
    """
    title = d["title"]
    if len(title) > 200:
        title = title[:197] + "..."
    kwargs: dict[str, Any] = {
        "id": d["id"],
        "title": title,
        "description": d.get("description", ""),
        "type": FeatureType(d.get("type", "feature")),
        "priority": Priority(d.get("priority", "P2")),
        "status": FeatureStatus(d.get("status", "backlog")),
        "created_at": _parse_dt(d.get("created_at")) or datetime.now(),
        "updated_at": _parse_dt(d.get("updated_at")),
        "planned_at": _parse_dt(d.get("planned_at")),
        "started_at": _parse_dt(d.get("started_at")),
        "completed_at": _parse_dt(d.get("completed_at")),
        "epic_id": d.get("epic_id"),
        "roadmap_id": d.get("roadmap_id"),
        "depends_on": d.get("depends_on", []),
        "blocked_by": d.get("blocked_by"),
        "blocked_reason": d.get("blocked_reason"),
        "plan_path": d.get("plan_path"),
        "pr_url": d.get("pr_url"),
        "branch_name": d.get("branch_name"),
        "estimated_hours": d.get("estimated_hours"),
        "actual_hours": d.get("actual_hours"),
        "total_cost_usd": d.get("total_cost_usd") or 0.0,
        "total_tokens": d.get("total_tokens") or 0,
        "success_criteria": d.get("success_criteria", []),
        "assumptions": d.get("assumptions", []),
        "notes": d.get("notes", []),
    }
    try:
        return Feature(**kwargs)
    except ValidationError as exc:
        logger.warning(
            "Feature %s failed Pydantic validation on read"
            " — using model_construct to preserve data: %s",
            d.get("id"),
            exc,
        )
        return Feature.model_construct(**kwargs)


def _dict_to_epic(d: dict[str, Any]) -> Epic:
    """Convert SQLite epic dict to Pydantic Epic model.

    Falls back to model_construct (bypasses validation) if Pydantic
    validation fails, to prevent silent data loss on read.
    """
    kwargs: dict[str, Any] = {
        "id": d["id"],
        "title": d["title"],
        "original_prompt": d.get("original_prompt", ""),
        "feature_ids": d.get("feature_ids", []),
        "workflow_id": d.get("workflow_id"),
        "status": EpicStatus(d.get("status", "drafting")),
        "created_at": _parse_dt(d.get("created_at")) or datetime.now(),
        "updated_at": _parse_dt(d.get("updated_at")),
        "completed_at": _parse_dt(d.get("completed_at")),
        "notes": d.get("notes", []),
    }
    try:
        return Epic(**kwargs)
    except ValidationError as exc:
        logger.warning(
            "Epic %s failed Pydantic validation on read"
            " — using model_construct to preserve data: %s",
            d.get("id"),
            exc,
        )
        return Epic.model_construct(**kwargs)


def _dict_to_roadmap(d: dict[str, Any]) -> Roadmap:
    """Convert SQLite roadmap dict to Pydantic Roadmap model.

    Falls back to model_construct (bypasses validation) if Pydantic
    validation fails, to prevent silent data loss on read.
    """
    kwargs: dict[str, Any] = {
        "id": d["id"],
        "title": d["title"],
        "original_prompt": d.get("original_prompt", ""),
        "epic_ids": d.get("epic_ids", []),
        "milestones": d.get("milestones", []),
        "status": RoadmapStatus(d.get("status", "drafting")),
        "created_at": _parse_dt(d.get("created_at")) or datetime.now(),
        "updated_at": _parse_dt(d.get("updated_at")),
        "completed_at": _parse_dt(d.get("completed_at")),
        "notes": d.get("notes", []),
    }
    try:
        return Roadmap(**kwargs)
    except ValidationError as exc:
        logger.warning(
            "Roadmap %s failed Pydantic validation on read"
            " — using model_construct to preserve data: %s",
            d.get("id"),
            exc,
        )
        return Roadmap.model_construct(**kwargs)


def _feature_to_fields(feature: Feature) -> dict[str, Any]:
    """Extract updatable fields from a Feature model for SQLite update.

    Excludes 'notes' (handled separately via the notes table).
    Includes 'depends_on' (BacklogDB.update_feature handles it specially).
    """
    fields: dict[str, Any] = {
        "title": feature.title,
        "description": feature.description,
        "type": feature.type.value,
        "priority": feature.priority.value,
        "status": feature.status.value,
        "epic_id": feature.epic_id,
        "roadmap_id": feature.roadmap_id,
        "blocked_by": feature.blocked_by,
        "blocked_reason": feature.blocked_reason,
        "plan_path": feature.plan_path,
        "pr_url": feature.pr_url,
        "branch_name": feature.branch_name,
        "estimated_hours": feature.estimated_hours,
        "actual_hours": feature.actual_hours,
        "total_cost_usd": feature.total_cost_usd,
        "total_tokens": feature.total_tokens,
        "depends_on": feature.depends_on,
        "success_criteria": feature.success_criteria,
        "assumptions": feature.assumptions,
    }
    # Datetime fields — only include if set
    for dt_field in ("planned_at", "started_at", "completed_at"):
        val = getattr(feature, dt_field)
        fields[dt_field] = val.isoformat() if val is not None else None
    return fields


class BacklogStoreAdapter:
    """Wraps SQLite BacklogDB with a Pydantic model API.

    Same constructor, same methods, same return types (Pydantic models).
    Uses SQLite for persistence.
    """

    def __init__(self, project_path: Path) -> None:
        self.project_path = project_path
        self.pixl_dir = get_pixl_dir(project_path)
        self.backlog_path = self.pixl_dir / "pixl.db"
        self._db = None  # Lazy-initialized PixlDB
        self._engine = None  # Lazy-initialized TransitionEngine

    @property
    def _db_instance(self):
        """Lazy-initialize the PixlDB backend."""
        if self._db is None:
            from pixl.storage.db.db_registry import get_project_db

            self._db = get_project_db(self.project_path)
        return self._db

    @property
    def _store(self):
        """Access the BacklogDB store."""
        return self._db_instance.backlog

    @property
    def engine(self):
        """Access the TransitionEngine (lazy-initialized).

        The engine validates transitions against state machines, runs
        guards, persists changes, and executes effects.
        """
        if self._engine is None:
            from pixl.state import TransitionEngine

            self._engine = TransitionEngine.default(self._store)
        return self._engine

    # Feature operations

    def add_feature(
        self,
        title: str,
        description: str = "",
        feature_type: FeatureType = FeatureType.FEATURE,
        priority: Priority = Priority.P2,
        depends_on: list[str] | None = None,
    ) -> Feature:
        """Add a new feature and persist to SQLite. Returns Feature model."""
        d = self._store.add_feature(
            title=title,
            description=description,
            feature_type=feature_type.value
            if isinstance(feature_type, FeatureType)
            else feature_type,
            priority=priority.value if isinstance(priority, Priority) else priority,
            depends_on=depends_on,
        )
        return _dict_to_feature(d)

    def get_feature(self, feature_id: str) -> Feature | None:
        """Get a feature by ID. Returns Feature model or None."""
        d = self._store.get_feature(feature_id)
        return _dict_to_feature(d) if d else None

    def update_feature(self, feature_or_id: Feature | str, **fields: Any) -> bool:
        """Update a feature. Accepts either a Feature model or (feature_id, **fields).

        Returns True if found.
        """
        if isinstance(feature_or_id, str):
            # Called as update_feature(feature_id, branch_name=..., ...)
            return self._store.update_feature(feature_or_id, **fields)

        # Called as update_feature(Feature(...))
        feature = feature_or_id
        current = self._store.get_feature(feature.id)
        if not current:
            return False

        stored_fields = _feature_to_fields(feature)
        self._store.update_feature(feature.id, **stored_fields)

        # Detect and add new notes (compare list lengths)
        existing_notes_count = len(current.get("notes", []))
        new_notes = feature.notes[existing_notes_count:]
        for note_str in new_notes:
            content = note_str.split("] ", 1)[1] if "] " in note_str else note_str
            self._store.add_note("feature", feature.id, content)

        return True

    def update_status(
        self,
        feature_id: str,
        status: FeatureStatus,
        note: str | None = None,
        **context: Any,
    ) -> Feature | None:
        """Update feature status through the transition engine.

        Validates the transition against the state machine, runs guards,
        persists the change, and executes effects (timestamps, propagation,
        audit trail).

        Args:
            feature_id: Feature ID
            status: Target status
            note: Optional note to attach
            **context: Extra context (trigger, blocked_by, blocked_reason, etc.)

        Returns:
            Updated Feature model, or None if the entity wasn't found
            or a hard guard blocked the transition.
        """
        status_str = status.value if isinstance(status, FeatureStatus) else status
        if note:
            context["note"] = note

        result = self.engine.transition(feature_id, status_str, **context)

        if result.success:
            d = self._store.get_feature(feature_id)
            return _dict_to_feature(d) if d else None

        # Transition was blocked — return None (backward compat)
        return None

    def transition(
        self,
        entity_id: str,
        to_status: str,
        **context: Any,
    ):
        """Full transition API with rich result.

        Works for any entity type (feature, epic, roadmap). Returns
        a TransitionResult with guard results, effect results, and
        error information.

        Args:
            entity_id: Entity ID (feat-001, epic-001, roadmap-001)
            to_status: Target status string
            **context: Extra context (trigger, note, blocked_by, etc.)

        Returns:
            TransitionResult with success/failure details.
        """
        return self.engine.transition(entity_id, to_status, **context)

    def remove_feature(self, feature_id: str) -> bool:
        """Remove a feature. Returns True if found."""
        return self._store.remove_feature(feature_id)

    def list_all(self) -> list[Feature]:
        """List all features as Feature models."""
        return [_dict_to_feature(d) for d in self._store.list_features()]

    def list_by_status(self, status: FeatureStatus) -> list[Feature]:
        """List features by status."""
        status_str = status.value if isinstance(status, FeatureStatus) else status
        return [_dict_to_feature(d) for d in self._store.list_features(status=status_str)]

    def exists(self) -> bool:
        """Check if storage has been initialized."""
        return (self.pixl_dir / "pixl.db").exists()

    # Load / Save (backward compat)

    def load(self) -> Backlog:
        """Load all data as a Backlog model snapshot.

        The returned model is a snapshot — mutations to it are NOT
        automatically persisted. Use the store methods directly for
        mutations.
        """
        features = self.list_all()
        epics = [_dict_to_epic(d) for d in self._store.list_epics()]
        roadmaps = [_dict_to_roadmap(d) for d in self._store.list_roadmaps()]

        return Backlog(
            features=features,
            epics=epics,
            roadmaps=roadmaps,
            next_id=self._get_next_id("feature"),
            next_epic_id=self._get_next_id("epic"),
            next_roadmap_id=self._get_next_id("roadmap"),
        )

    def _get_next_id(self, entity_type: str) -> int:
        """Get next ID value from SQLite sequences."""
        row = self._db_instance.conn.execute(
            "SELECT next_value FROM id_sequences WHERE name = ?",
            (entity_type,),
        ).fetchone()
        return row["next_value"] if row else 1

    # Epic operations

    def add_epic(
        self,
        title: str,
        original_prompt: str = "",
        workflow_id: str | None = None,
    ) -> Epic:
        """Add a new epic. Returns Epic model."""
        d = self._store.add_epic(
            title=title,
            original_prompt=original_prompt,
            workflow_id=workflow_id,
        )
        return _dict_to_epic(d)

    def get_epic(self, epic_id: str) -> Epic | None:
        """Get an epic by ID. Returns Epic model or None."""
        d = self._store.get_epic(epic_id)
        return _dict_to_epic(d) if d else None

    def update_epic(self, epic_or_id: Epic | str, **fields: Any) -> bool:
        """Update an epic. Accepts either an Epic model or (epic_id, **fields).

        When called with an Epic model, handles feature_ids reconciliation:
        if the epic's feature_ids changed, updates the epic_id FK on affected
        features.

        Returns True if found.
        """
        if isinstance(epic_or_id, str):
            return self._store.update_epic(epic_or_id, **fields)

        epic = epic_or_id
        update_fields: dict[str, Any] = {
            "title": epic.title,
            "original_prompt": epic.original_prompt,
            "workflow_id": epic.workflow_id,
            "status": epic.status.value if isinstance(epic.status, EpicStatus) else epic.status,
        }
        self._store.update_epic(epic.id, **update_fields)

        # Reconcile feature_ids: sync epic_id FK on features
        current = self._store.get_epic(epic.id)
        if current:
            current_feature_ids = set(current.get("feature_ids", []))
            new_feature_ids = set(epic.feature_ids)

            # Features added to this epic
            for fid in new_feature_ids - current_feature_ids:
                self._store.update_feature(fid, epic_id=epic.id)

            # Features removed from this epic
            for fid in current_feature_ids - new_feature_ids:
                self._store.update_feature(fid, epic_id=None)

        # Sync new notes
        if current:
            existing_count = len(current.get("notes", []))
            for note_str in epic.notes[existing_count:]:
                content = note_str.split("] ", 1)[1] if "] " in note_str else note_str
                self._store.add_note("epic", epic.id, content)

        return True

    # Roadmap operations

    def add_roadmap(
        self,
        title: str,
        original_prompt: str = "",
    ) -> Roadmap:
        """Add a new roadmap. Returns Roadmap model."""
        d = self._store.add_roadmap(
            title=title,
            original_prompt=original_prompt,
        )
        return _dict_to_roadmap(d)

    def get_roadmap(self, roadmap_id: str) -> Roadmap | None:
        """Get a roadmap by ID. Returns Roadmap model or None."""
        d = self._store.get_roadmap(roadmap_id)
        return _dict_to_roadmap(d) if d else None

    def update_roadmap(self, roadmap_or_id: Roadmap | str, **fields: Any) -> bool:
        """Update a roadmap. Accepts either a Roadmap model or (roadmap_id, **fields).

        When called with a Roadmap model, handles epic_ids reconciliation:
        if the roadmap's epic_ids changed, updates the roadmap_id FK on
        affected epics.

        Returns True if found.
        """
        if isinstance(roadmap_or_id, str):
            return self._store.update_roadmap(roadmap_or_id, **fields)

        roadmap = roadmap_or_id
        update_fields: dict[str, Any] = {
            "title": roadmap.title,
            "original_prompt": roadmap.original_prompt,
            "status": roadmap.status.value
            if isinstance(roadmap.status, RoadmapStatus)
            else roadmap.status,
        }
        self._store.update_roadmap(roadmap.id, **update_fields)

        # Reconcile epic_ids: sync roadmap_id FK on epics
        current = self._store.get_roadmap(roadmap.id)
        if current:
            current_epic_ids = set(current.get("epic_ids", []))
            new_epic_ids = set(roadmap.epic_ids)

            for eid in new_epic_ids - current_epic_ids:
                self._store.update_epic(eid, roadmap_id=roadmap.id)

            for eid in current_epic_ids - new_epic_ids:
                self._store.update_epic(eid, roadmap_id=None)

        # Sync new notes
        if current:
            existing_count = len(current.get("notes", []))
            for note_str in roadmap.notes[existing_count:]:
                content = note_str.split("] ", 1)[1] if "] " in note_str else note_str
                self._store.add_note("roadmap", roadmap.id, content)

        return True

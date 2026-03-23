"""Backlog model for managing feature collection."""

from datetime import datetime

from pydantic import BaseModel, Field

from pixl.models.epic import Epic
from pixl.models.feature import Feature, FeatureStatus, FeatureType, Priority
from pixl.models.roadmap import Roadmap


class Backlog(BaseModel):
    """Collection of features, epics, and roadmaps with management operations."""

    features: list[Feature] = Field(default_factory=list)
    epics: list[Epic] = Field(default_factory=list)
    roadmaps: list[Roadmap] = Field(default_factory=list)
    next_id: int = Field(default=1)
    next_epic_id: int = Field(default=1)
    next_roadmap_id: int = Field(default=1)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime | None = None

    def _generate_id(self) -> str:
        """Generate next feature ID."""
        feature_id = f"feat-{self.next_id:03d}"
        self.next_id += 1
        self.updated_at = datetime.now()
        return feature_id

    def _generate_epic_id(self) -> str:
        """Generate next epic ID."""
        epic_id = f"epic-{self.next_epic_id:03d}"
        self.next_epic_id += 1
        self.updated_at = datetime.now()
        return epic_id

    def _generate_roadmap_id(self) -> str:
        """Generate next roadmap ID."""
        roadmap_id = f"roadmap-{self.next_roadmap_id:03d}"
        self.next_roadmap_id += 1
        self.updated_at = datetime.now()
        return roadmap_id

    def add(
        self,
        title: str,
        description: str = "",
        feature_type: FeatureType = FeatureType.FEATURE,
        priority: Priority = Priority.P2,
        depends_on: list[str] | None = None,
    ) -> Feature:
        """Add a new feature to the backlog."""
        feature = Feature(
            id=self._generate_id(),
            title=title,
            description=description,
            type=feature_type,
            priority=priority,
            depends_on=depends_on or [],
        )
        self.features.append(feature)
        self.updated_at = datetime.now()
        return feature

    def get(self, feature_id: str) -> Feature | None:
        """Get a feature by ID."""
        return next((f for f in self.features if f.id == feature_id), None)

    def update(self, feature: Feature) -> bool:
        """Update a feature in the backlog."""
        for i, f in enumerate(self.features):
            if f.id == feature.id:
                self.features[i] = feature
                self.updated_at = datetime.now()
                return True
        return False

    def remove(self, feature_id: str) -> bool:
        """Remove a feature from the backlog."""
        for i, f in enumerate(self.features):
            if f.id == feature_id:
                self.features.pop(i)
                self.updated_at = datetime.now()
                return True
        return False

    def list_by_status(self, status: FeatureStatus) -> list[Feature]:
        """Get all features with a given status."""
        return [f for f in self.features if f.status == status]

    def list_by_priority(self, priority: Priority) -> list[Feature]:
        """Get all features with a given priority."""
        return [f for f in self.features if f.priority == priority]

    def list_actionable(self) -> list[Feature]:
        """Get all features that can be worked on."""
        return [f for f in self.features if f.is_actionable]

    def list_in_progress(self) -> list[Feature]:
        """Get all features currently being worked on."""
        return self.list_by_status(FeatureStatus.IN_PROGRESS)

    def list_blocked(self) -> list[Feature]:
        """Get all blocked features."""
        return self.list_by_status(FeatureStatus.BLOCKED)

    def get_next_actionable(self) -> Feature | None:
        """Get the highest priority actionable feature."""
        actionable = self.list_actionable()
        if not actionable:
            return None
        priority_order = {Priority.P0: 0, Priority.P1: 1, Priority.P2: 2, Priority.P3: 3}
        actionable.sort(key=lambda f: (priority_order[f.priority], f.created_at))
        return actionable[0]

    def get_dependencies(self, feature_id: str) -> list[Feature]:
        """Get all features that this feature depends on."""
        feature = self.get(feature_id)
        if not feature:
            return []
        deps = []
        for dep_id in feature.depends_on:
            dep = self.get(dep_id)
            if dep is not None:
                deps.append(dep)
        return deps

    def get_dependents(self, feature_id: str) -> list[Feature]:
        """Get all features that depend on this feature."""
        return [f for f in self.features if feature_id in f.depends_on]

    def can_start(self, feature_id: str) -> tuple[bool, str | None]:
        """Check if a feature can be started (all dependencies complete)."""
        feature = self.get(feature_id)
        if not feature:
            return False, "Feature not found"

        if not feature.is_actionable:
            return False, f"Feature status is {feature.status.value}"

        for dep_id in feature.depends_on:
            dep = self.get(dep_id)
            if dep and not dep.is_complete:
                return False, f"Dependency {dep_id} is not complete"

        return True, None

    @property
    def stats(self) -> dict[str, int]:
        """Get statistics about the backlog."""
        stats = {status.value: 0 for status in FeatureStatus}
        for feature in self.features:
            stats[feature.status.value] += 1
        stats["total"] = len(self.features)
        return stats

    # Epic operations

    def add_epic(
        self,
        title: str,
        original_prompt: str = "",
        workflow_id: str | None = None,
    ) -> Epic:
        """Add a new epic to the backlog."""
        epic = Epic(
            id=self._generate_epic_id(),
            title=title,
            original_prompt=original_prompt,
            workflow_id=workflow_id,
        )
        self.epics.append(epic)
        self.updated_at = datetime.now()
        return epic

    def get_epic(self, epic_id: str) -> Epic | None:
        """Get an epic by ID."""
        return next((e for e in self.epics if e.id == epic_id), None)

    def update_epic(self, epic: Epic) -> bool:
        """Update an epic in the backlog."""
        for i, e in enumerate(self.epics):
            if e.id == epic.id:
                self.epics[i] = epic
                self.updated_at = datetime.now()
                return True
        return False

    # Roadmap operations

    def add_roadmap(
        self,
        title: str,
        original_prompt: str = "",
    ) -> Roadmap:
        """Add a new roadmap to the backlog."""
        roadmap = Roadmap(
            id=self._generate_roadmap_id(),
            title=title,
            original_prompt=original_prompt,
        )
        self.roadmaps.append(roadmap)
        self.updated_at = datetime.now()
        return roadmap

    def get_roadmap(self, roadmap_id: str) -> Roadmap | None:
        """Get a roadmap by ID."""
        return next((r for r in self.roadmaps if r.id == roadmap_id), None)

    def update_roadmap(self, roadmap: Roadmap) -> bool:
        """Update a roadmap in the backlog."""
        for i, r in enumerate(self.roadmaps):
            if r.id == roadmap.id:
                self.roadmaps[i] = roadmap
                self.updated_at = datetime.now()
                return True
        return False

    def to_markdown(self) -> str:
        """Generate markdown representation of the backlog."""
        lines = ["# Feature Backlog", ""]

        # Stats
        stats = self.stats
        lines.extend(
            [
                "## Summary",
                f"- **Total:** {stats['total']}",
                f"- **Backlog:** {stats['backlog']}",
                f"- **Planned:** {stats['planned']}",
                f"- **In Progress:** {stats['in_progress']}",
                f"- **Review:** {stats['review']}",
                f"- **Done:** {stats['done']}",
                f"- **Blocked:** {stats['blocked']}",
                "",
            ]
        )

        # Features by status
        for status in FeatureStatus:
            features = self.list_by_status(status)
            if features:
                lines.extend([f"## {status.value.replace('_', ' ').title()}", ""])
                for f in features:
                    priority_emoji = {"P0": "🔴", "P1": "🟠", "P2": "🟡", "P3": "🟢"}
                    emoji = priority_emoji.get(f.priority.value, "⚪")
                    lines.append(f"- [{f.id}] {emoji} **{f.title}** ({f.type.value})")
                lines.append("")

        return "\n".join(lines)

"""Types for Claude Code loaders."""

from typing import Any

from pydantic import BaseModel, Field


class LoadedClaudeMd(BaseModel):
    """Loaded CLAUDE.md content."""

    path: str = Field(..., description="Path to CLAUDE.md")
    content: str = Field(..., description="Raw content")
    project_overview: str | None = Field(default=None)
    commands: list[str] = Field(default_factory=list)
    patterns: list[str] = Field(default_factory=list)

    @property
    def exists(self) -> bool:
        """Check if CLAUDE.md was found."""
        return bool(self.content)


class SkillFrontmatter(BaseModel):
    """Skill frontmatter from SKILL.md file."""

    name: str
    description: str | None = None
    triggers: list[str] = Field(default_factory=list)


class LoadedSkill(BaseModel):
    """Loaded skill definition."""

    name: str
    path: str
    directory: str = Field(..., description="Skill directory path")
    frontmatter: SkillFrontmatter
    content: str = Field(..., description="Skill instructions (body)")

    @property
    def description(self) -> str | None:
        """Get the description from frontmatter."""
        return self.frontmatter.description


class LoadedRule(BaseModel):
    """Loaded rule file."""

    name: str
    path: str
    content: str


class LoadedSettings(BaseModel):
    """Loaded .claude/settings.json."""

    path: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)

    @property
    def exists(self) -> bool:
        """Check if settings file was found."""
        return self.path is not None

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self.data.get(key, default)

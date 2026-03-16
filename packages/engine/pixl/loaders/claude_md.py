"""CLAUDE.md loader."""

from __future__ import annotations

import re
from pathlib import Path

from pixl.loaders.types import LoadedClaudeMd

class ClaudeMdLoader:
    """Loader for CLAUDE.md files."""

    CLAUDE_MD_NAMES = ["CLAUDE.md", "claude.md", "CLAUDE.MD"]

    def __init__(self, project_path: Path):
        """Initialize loader.

        Args:
            project_path: Project root path
        """
        self.project_path = project_path

    def find_claude_md(self) -> Path | None:
        """Find CLAUDE.md in project.

        Checks for CLAUDE.md in:
        1. Project root
        2. .claude directory

        Returns:
            Path to CLAUDE.md or None
        """
        # Check project root
        for name in self.CLAUDE_MD_NAMES:
            path = self.project_path / name
            if path.exists():
                return path

        # Check .claude directory
        claude_dir = self.project_path / ".claude"
        if claude_dir.exists():
            for name in self.CLAUDE_MD_NAMES:
                path = claude_dir / name
                if path.exists():
                    return path

        return None

    def load(self) -> LoadedClaudeMd:
        """Load CLAUDE.md content.

        Returns:
            LoadedClaudeMd with parsed content
        """
        path = self.find_claude_md()

        if not path:
            return LoadedClaudeMd(
                path="",
                content="",
            )

        try:
            content = path.read_text()
        except (OSError, UnicodeDecodeError):
            return LoadedClaudeMd(
                path=str(path),
                content="",
            )

        project_overview = self._extract_section(content, "Project Overview")
        if not project_overview:
            project_overview = self._extract_section(content, "Overview")

        commands = self._extract_commands(content)
        patterns = self._extract_patterns(content)

        return LoadedClaudeMd(
            path=str(path),
            content=content,
            project_overview=project_overview,
            commands=commands,
            patterns=patterns,
        )

    def _extract_section(self, content: str, section_name: str) -> str | None:
        """Extract a section from markdown.

        Args:
            content: Full markdown content
            section_name: Section header name

        Returns:
            Section content or None
        """
        # Match section header (## or ###)
        pattern = rf"^##?\s*{re.escape(section_name)}\s*$"
        match = re.search(pattern, content, re.MULTILINE | re.IGNORECASE)

        if not match:
            return None

        start = match.end()

        next_header = re.search(r"^##", content[start:], re.MULTILINE)
        end = start + next_header.start() if next_header else len(content)

        return content[start:end].strip()

    def _extract_commands(self, content: str) -> list[str]:
        """Extract command definitions from CLAUDE.md.

        Args:
            content: Full markdown content

        Returns:
            List of commands found
        """
        commands = []

        # Look for command patterns in code blocks
        # Pattern: command name followed by description
        code_blocks = re.findall(r"```(?:bash|sh|shell)?\n(.*?)```", content, re.DOTALL)

        for block in code_blocks:
            for line in block.split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    commands.append(line)

        return commands[:20]  # Limit to 20 commands

    def _extract_patterns(self, content: str) -> list[str]:
        """Extract key patterns from CLAUDE.md.

        Args:
            content: Full markdown content

        Returns:
            List of patterns found
        """
        patterns = []

        # Look for "Key Patterns" or "Patterns" section
        section = self._extract_section(content, "Key Patterns")
        if not section:
            section = self._extract_section(content, "Patterns")

        if section:
            items = re.findall(r"^[\-\*]\s+(.+)$", section, re.MULTILINE)
            patterns.extend(items[:10])

        return patterns

def load_claude_md(project_path: Path) -> LoadedClaudeMd | None:
    """Load CLAUDE.md from project.

    Args:
        project_path: Project root path

    Returns:
        LoadedClaudeMd or None if not found
    """
    loader = ClaudeMdLoader(project_path)
    result = loader.load()
    return result if result.exists else None

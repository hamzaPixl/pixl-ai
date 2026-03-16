"""Claude Code project loaders.

Loads project configuration from standard Claude Code locations:
- CLAUDE.md - Project context and guidance
- .claude/rules/*.md - Project rules
- .claude/settings.json - Project settings
"""

from pixl.loaders.claude_md import ClaudeMdLoader, load_claude_md
from pixl.loaders.frontmatter import parse_frontmatter
from pixl.loaders.rules import RulesLoader, load_rules
from pixl.loaders.settings import SettingsLoader, load_settings
from pixl.loaders.types import (
    LoadedClaudeMd,
    LoadedRule,
    LoadedSettings,
)

__all__ = [
    # Types
    "LoadedClaudeMd",
    "LoadedRule",
    "LoadedSettings",
    # Loaders
    "ClaudeMdLoader",
    "RulesLoader",
    "SettingsLoader",
    # Utilities
    "parse_frontmatter",
    # Convenience functions
    "load_claude_md",
    "load_rules",
    "load_settings",
]

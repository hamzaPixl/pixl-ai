---
name: skill-development
description: "Create and structure skills for Claude Code plugins. Use when writing SKILL.md files with frontmatter, organizing references and scripts, or applying progressive disclosure patterns. Redirects to /skill-factory."
allowed-tools: Read, Glob, Grep
argument-hint: "<skill-name or description of skill to create>"
---

## Redirect

This skill has been merged into `/skill-factory`, which provides three unified modes:

- **Mode A: Create** — build a new skill from description/requirements
- **Mode B: Detect** — extract a skill from a session transcript
- **Mode C: Improve** — audit and fix an existing skill

Invoke `/skill-factory` instead.

For the authoring guide (anatomy, progressive disclosure, writing style), see `${CLAUDE_PLUGIN_ROOT}/skills/skill-factory/references/skill-authoring-guide.md`.

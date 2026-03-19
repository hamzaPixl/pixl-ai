---
name: plugin-structure
description: "Scaffold and organize Claude Code plugins. Use when creating plugin.json manifests, setting up directory structure, or configuring auto-discovery for commands, agents, skills, and hooks."
allowed-tools: Read, Glob, Grep, Write, Edit, Bash
argument-hint: "<plugin-name or action e.g. scaffold, audit>"
disable-model-invocation: true
---

# Plugin Structure for Claude Code

## Overview

Claude Code plugins follow a standardized directory structure with automatic component discovery. Understanding this structure enables creating well-organized, maintainable plugins that integrate seamlessly with Claude Code.

**Key concepts:**

- Conventional directory layout for automatic discovery
- Manifest-driven configuration in `.claude-plugin/plugin.json`
- Component-based organization (commands, agents, skills, hooks)
- Portable path references using `${CLAUDE_PLUGIN_ROOT}`

## Directory Structure

```
plugin-name/
├── .claude-plugin/
│   └── plugin.json          # Required: Plugin manifest
├── commands/                 # Slash commands (.md files)
├── agents/                   # Subagent definitions (.md files)
├── skills/                   # Agent skills (subdirectories)
│   └── skill-name/
│       └── SKILL.md         # Required for each skill
├── hooks/
│   └── hooks.json           # Event handler configuration
└── scripts/                 # Helper scripts and utilities
```

**Critical rules:**

1. **Manifest location**: The `plugin.json` manifest MUST be in `.claude-plugin/` directory
2. **Component locations**: All component directories (commands, agents, skills, hooks) MUST be at plugin root level, NOT nested inside `.claude-plugin/`
3. **Optional components**: Only create directories for components the plugin actually uses
4. **Naming convention**: Use kebab-case for all directory and file names

## Plugin Manifest (plugin.json)

Located at `.claude-plugin/plugin.json`.

### Required Fields

```json
{
  "name": "plugin-name"
}
```

Name must be kebab-case, unique across installed plugins, no spaces or special characters.

### Recommended Metadata

```json
{
  "name": "plugin-name",
  "version": "1.0.0",
  "description": "Brief explanation of plugin purpose",
  "author": { "name": "Author Name" },
  "license": "MIT",
  "keywords": ["testing", "automation"]
}
```

Version follows semver (MAJOR.MINOR.PATCH). Keywords aid plugin discovery.

### Component Path Configuration

Custom paths supplement default directories (they don't replace them):

```json
{
  "name": "plugin-name",
  "commands": "./custom-commands",
  "agents": ["./agents", "./specialized-agents"],
  "hooks": "./config/hooks.json"
}
```

All paths must be relative to plugin root and start with `./`. Arrays supported for multiple locations.

## Component Organization

### Commands

**Location**: `commands/` | **Format**: `.md` with YAML frontmatter | **Auto-discovered**
See `/command-development` skill for file format and patterns.

### Agents

**Location**: `agents/` | **Format**: `.md` with YAML frontmatter | **Auto-discovered**
See `/agent-development` skill for file format and triggering.

### Skills

**Location**: `skills/<skill-name>/SKILL.md` | **Format**: `.md` with YAML frontmatter | **Auto-discovered**
Skills can include supporting files (scripts, references, examples) in subdirectories.
See `/skill-factory` skill for file format and activation.

### Hooks

**Location**: `hooks/hooks.json` or inline in `plugin.json` | **Format**: JSON | **Auto-registered**
Available events: PreToolUse, PostToolUse, Stop, SubagentStop, SessionStart, SessionEnd, UserPromptSubmit, PreCompact, Notification.
See `/hook-development` skill for configuration and event handling.

## Portable Path References

### ${CLAUDE_PLUGIN_ROOT}

Use `${CLAUDE_PLUGIN_ROOT}` for all intra-plugin path references. Plugins install in different locations depending on installation method, OS, and user preferences.

**Where to use**: Hook command paths, script execution references, resource file paths.

**Never use**: Hardcoded absolute paths, relative paths from working directory, or home directory shortcuts (`~/`).

The variable is available in manifest JSON fields (hooks), component markdown files, and as an environment variable in executed scripts.

## File Naming Conventions

All files and directories use **kebab-case**:

| Component | Convention                      | Example                                  |
| --------- | ------------------------------- | ---------------------------------------- |
| Commands  | `<name>.md` → becomes `/<name>` | `code-review.md` → `/code-review`        |
| Agents    | `<role>.md`                     | `test-generator.md`                      |
| Skills    | `<topic>/SKILL.md`              | `api-testing/SKILL.md`                   |
| Scripts   | `<action>.<ext>`                | `validate-input.sh`                      |
| Config    | Standard names                  | `hooks.json`, `plugin.json`              |

## Auto-Discovery Mechanism

Claude Code automatically discovers and loads components:

1. **Plugin manifest**: Reads `.claude-plugin/plugin.json` when plugin enables
2. **Commands**: Scans `commands/` directory for `.md` files
3. **Agents**: Scans `agents/` directory for `.md` files
4. **Skills**: Scans `skills/` for subdirectories containing `SKILL.md`
5. **Hooks**: Loads configuration from `hooks/hooks.json` or manifest

Custom paths in `plugin.json` supplement (not replace) default directories. Changes take effect on next Claude Code session — no restart required.

## Best Practices

### Organization

- Group related components together; create subdirectories in `scripts/` for different purposes
- Keep `plugin.json` lean — rely on auto-discovery for standard layouts
- Only specify custom paths when deviating from conventions

### Naming

- Use consistent naming across components (e.g., command `test-runner` pairs with agent `test-runner-agent`)
- Use descriptive names indicating purpose — avoid generic names like `utils/` or `misc.md`
- Balance brevity with clarity: commands 2-3 words, agents describe role, skills are topic-focused

### Portability

- Always use `${CLAUDE_PLUGIN_ROOT}` — never hardcode paths
- Use portable bash/Python constructs; avoid system-specific features
- Document required tool dependencies and versions

## Additional Resources

For detailed component patterns and manifest configuration:

- **`references/manifest-reference.md`** — Complete plugin.json field reference
- **`references/component-patterns.md`** — Advanced component organization and troubleshooting
- **`examples/minimal-plugin.md`** — Minimal plugin example
- **`examples/standard-plugin.md`** — Standard plugin with all components
- **`examples/advanced-plugin.md`** — Advanced multi-component plugin

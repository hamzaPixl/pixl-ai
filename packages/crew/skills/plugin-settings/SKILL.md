---
name: plugin-settings
description: "Configure per-project plugin settings via .claude/plugin-name.local.md files. Use when storing user-configurable state with YAML frontmatter for hooks, commands, and agents."
allowed-tools: Read, Glob, Grep, Write, Edit, Bash
argument-hint: "<plugin-name or setting to configure>"
disable-model-invocation: true
---

# Plugin Settings Pattern for Claude Code Plugins

## Overview

Plugins can store user-configurable settings and state in `.claude/plugin-name.local.md` files within the project directory. This pattern uses YAML frontmatter for structured configuration and markdown content for prompts or additional context.

**Key characteristics:**

- File location: `.claude/plugin-name.local.md` in project root
- Structure: YAML frontmatter + markdown body
- Purpose: Per-project plugin configuration and state
- Usage: Read from hooks, commands, and agents
- Lifecycle: User-managed (not in git, should be in `.gitignore`)

## File Structure

### Basic Template

```markdown
---
enabled: true
setting1: value1
setting2: value2
numeric_setting: 42
list_setting: ["item1", "item2"]
---

# Additional Context

This markdown body can contain:

- Task descriptions
- Additional instructions
- Prompts to feed back to Claude
- Documentation or notes
```

### Example: Plugin State File

**.claude/my-plugin.local.md:**

```markdown
---
enabled: true
strict_mode: false
max_retries: 3
notification_level: info
coordinator_session: team-leader
---

# Plugin Configuration

This plugin is configured for standard validation mode.
Contact @team-lead with questions.
```

## Reading Settings Files

### From Hooks (Bash Scripts)

This is the core pattern for reading settings. The **frontmatter extraction one-liner** shown here is reused everywhere settings are parsed:

```bash
#!/bin/bash
set -euo pipefail

# Define state file path
STATE_FILE=".claude/my-plugin.local.md"

# Quick exit if file doesn't exist
if [[ ! -f "$STATE_FILE" ]]; then
  exit 0  # Plugin not configured, skip
fi

# === FRONTMATTER EXTRACTION (canonical pattern) ===
FRONTMATTER=$(sed -n '/^---$/,/^---$/{ /^---$/d; p; }' "$STATE_FILE")

# Extract individual fields
ENABLED=$(echo "$FRONTMATTER" | grep '^enabled:' | sed 's/enabled: *//' | sed 's/^"\(.*\)"$/\1/')
STRICT_MODE=$(echo "$FRONTMATTER" | grep '^strict_mode:' | sed 's/strict_mode: *//' | sed 's/^"\(.*\)"$/\1/')

# Check if enabled
if [[ "$ENABLED" != "true" ]]; then
  exit 0  # Disabled
fi

# Use configuration in hook logic
if [[ "$STRICT_MODE" == "true" ]]; then
  # Apply strict validation
  # ...
fi
```

See `examples/read-settings-hook.sh` for complete working example.

### From Commands

Commands can read settings via the Read tool. Steps: check if `.claude/my-plugin.local.md` exists, read it, parse YAML frontmatter to extract settings, then apply them to processing logic.

### From Agents

Agents reference settings in their instructions: check for `.claude/my-plugin.local.md`, parse frontmatter, and adapt behavior based on fields like `enabled`, `mode`, etc.

## Parsing Techniques

### Extract Frontmatter

Use the canonical sed one-liner from the hooks section above:

```bash
FRONTMATTER=$(sed -n '/^---$/,/^---$/{ /^---$/d; p; }' "$FILE")
```

### Read Individual Fields

**String fields:**

```bash
VALUE=$(echo "$FRONTMATTER" | grep '^field_name:' | sed 's/field_name: *//' | sed 's/^"\(.*\)"$/\1/')
```

**Boolean fields:**

```bash
ENABLED=$(echo "$FRONTMATTER" | grep '^enabled:' | sed 's/enabled: *//')
# Compare: if [[ "$ENABLED" == "true" ]]; then
```

**Numeric fields:**

```bash
MAX=$(echo "$FRONTMATTER" | grep '^max_value:' | sed 's/max_value: *//')
# Use: if [[ $MAX -gt 100 ]]; then
```

## Creating Settings Files

Steps:

1. Ask user for configuration preferences
2. Create `.claude/my-plugin.local.md` with YAML frontmatter
3. Set appropriate values based on user input
4. Inform user that settings are saved
5. Remind user to restart Claude Code for hooks to recognize changes

## Best Practices

### File Naming

- Use `.claude/plugin-name.local.md` format — match plugin name exactly
- Use `.local.md` suffix for user-local files
- Never use a different directory or `.md` without `.local` (might be committed)

### Gitignore

Always add to `.gitignore`:

```gitignore
.claude/*.local.md
.claude/*.local.json
```

Document this in plugin README.

### Defaults

Provide sensible defaults when settings file doesn't exist:

```bash
if [[ ! -f "$STATE_FILE" ]]; then
  # Use defaults
  ENABLED=true
  MODE=standard
else
  # Parse frontmatter using the canonical sed pattern and extract fields
  # ...
fi
```

## Implementation Workflow

To add settings to a plugin:

1. Design settings schema (which fields, types, defaults)
2. Create template file in plugin documentation
3. Add gitignore entry for `.claude/*.local.md`
4. Implement settings parsing in hooks/commands
5. Use quick-exit pattern (check file exists, check enabled field)
6. Document settings in plugin README with template
7. Remind users that changes require Claude Code restart

Focus on keeping settings simple and providing good defaults when settings file doesn't exist.

## Additional Resources

For detailed parsing techniques and real-world implementations:

- **`references/parsing-techniques.md`** — Complete guide to parsing YAML frontmatter and markdown bodies
- **`references/real-world-examples.md`** — Deep dive: multi-agent-swarm and ralph-loop implementations
- **`examples/read-settings-hook.sh`** — Complete hook that reads and uses settings
- **`examples/create-settings-command.md`** — Command that creates settings file
- **`scripts/validate-settings.sh`** — Validate settings file structure
- **`scripts/parse-frontmatter.sh`** — Extract frontmatter fields utility

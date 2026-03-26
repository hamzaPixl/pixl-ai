---
name: crew-init
description: "Initialize a project for pixl-crew by generating a CLAUDE.md stub, workflow/delegation rules, and scoped permissions. Use when asked to 'init crew', 'set up crew for this project', 'crew-init', 'bootstrap crew', or 'add crew to project'."
allowed-tools: Read, Write, Bash, Glob, Grep
argument-hint: "<project directory (defaults to cwd)>"
disable-model-invocation: true
---

## Overview

Drops lightweight pixl-crew awareness assets into any project so Claude knows about available agents, skills, and conventions without the full plugin source being present.

## What gets created

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Project identity + crew agents/skills reference + operational rules |
| `.claude/rules/crew-workflow.md` | Explore → Plan → Implement → Commit, frequent commits, parallel execution |
| `.claude/rules/crew-delegation.md` | Agent routing table, when to use orchestrator, skill-first rules |
| `.claude/rules/crew-enforcement.md` | Mandatory skill usage and agent delegation enforcement |
| `.claude/settings.local.json` | Scoped permission wildcards (only if file doesn't exist) |

## Step 0: Initialize pixl storage + crew

If `pixl` CLI is available (`command -v pixl`), run `pixl project init` in the target directory.
This creates both the `.pixl/` directory (SQLite storage) AND installs crew templates
(CLAUDE.md, `.claude/rules/`, `settings.local.json`) in a single command.

```bash
if command -v pixl &>/dev/null; then
  pixl --project <target> project init
  # Done — pixl project init handles everything.
  # Skip to Step 6 (summary).
fi
```

Skip silently if pixl is not installed — continue with manual file creation below.

## Step 1: Detect project info

1. Determine the target directory (argument or cwd)
2. Try to detect the project name from (in order):
   - `package.json` → `name` field
   - `pyproject.toml` → `name` field
   - Directory basename
3. Ask the user to confirm or override the project name

## Step 2: Generate CLAUDE.md

1. Read the template from `${CLAUDE_PLUGIN_ROOT}/templates/crew-init/CLAUDE.md.tmpl`
2. Replace `{{PROJECT_NAME}}` with the detected/confirmed project name
3. Write to `<target>/CLAUDE.md`
   - If a `CLAUDE.md` already exists, ask the user whether to append a crew section or skip

## Step 3: Copy rule files

1. Create `<target>/.claude/rules/` if it doesn't exist
2. Copy `${CLAUDE_PLUGIN_ROOT}/templates/crew-init/crew-workflow.md` → `<target>/.claude/rules/crew-workflow.md`
3. Copy `${CLAUDE_PLUGIN_ROOT}/templates/crew-init/crew-delegation.md` → `<target>/.claude/rules/crew-delegation.md`

## Step 4: Copy enforcement rules

1. Copy `${CLAUDE_PLUGIN_ROOT}/templates/crew-init/crew-enforcement.md` → `<target>/.claude/rules/crew-enforcement.md`
   - This file enforces mandatory skill usage before writing to domain/infra/API directories
   - It also enforces agent delegation for multi-file changes

## Step 5: Set up permissions

1. Check if `<target>/.claude/settings.local.json` exists
2. If it does NOT exist:
   - Read `${CLAUDE_PLUGIN_ROOT}/templates/crew-init/settings.local.json.tmpl`
   - Write it to `<target>/.claude/settings.local.json`
3. If it DOES exist:
   - Read the existing file
   - Merge the permission entries from the template into the existing `allowedTools` array (avoid duplicates)
   - Write the merged result back

## Step 6: Summary

Print a summary:

```
✓ Crew initialized for <project-name>

  Created:
    CLAUDE.md              — project identity + crew reference (14 agents, 75 skills)
    .claude/rules/         — crew-workflow.md, crew-delegation.md, crew-enforcement.md
    .claude/settings.local.json — scoped permissions

  Next steps:
    1. Fill in the project description in CLAUDE.md
    2. Start a new Claude session to pick up the new rules
    3. Run /session-wrap at end of sessions to preserve decisions
```

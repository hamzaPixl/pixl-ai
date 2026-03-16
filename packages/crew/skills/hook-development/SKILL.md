---
name: hook-development
description: "Create event-driven hooks for Claude Code plugins. Use when implementing PreToolUse/PostToolUse/Stop/SessionStart hooks, prompt-based validation, or command-based automation."
allowed-tools: Read, Glob, Grep, Write, Edit, Bash
argument-hint: "<hook-event e.g. PreToolUse, PostToolUse, Stop>"
disable-model-invocation: true
---

# Hook Development for Claude Code Plugins

## Overview

Hooks are event-driven automation scripts that execute in response to Claude Code events. Use hooks to validate operations, enforce policies, add context, and integrate external tools into workflows.

**Key capabilities:**

- Validate tool calls before execution (PreToolUse)
- React to tool results (PostToolUse)
- Enforce completion standards (Stop, SubagentStop)
- Load project context (SessionStart)
- Automate workflows across the development lifecycle

## Hook Types

### Prompt-Based Hooks (Recommended)

Use LLM-driven decision making for context-aware validation:

```json
{
  "type": "prompt",
  "prompt": "Evaluate if this tool use is appropriate: $TOOL_INPUT",
  "timeout": 30
}
```

**Supported events:** Stop, SubagentStop, UserPromptSubmit, PreToolUse

### Command Hooks

Execute bash commands for deterministic checks:

```json
{
  "type": "command",
  "command": "bash ${CLAUDE_PLUGIN_ROOT}/scripts/validate.sh",
  "timeout": 60
}
```

**Use for:** fast deterministic validations, file system operations, external tool integrations, performance-critical checks.

## Hook Configuration Formats

### Plugin hooks.json Format

**For plugin hooks** in `hooks/hooks.json`, use wrapper format:

```json
{
  "description": "Brief explanation of hooks (optional)",
  "hooks": {
    "PreToolUse": [...],
    "Stop": [...],
    "SessionStart": [...]
  }
}
```

- `description` field is optional, `hooks` field is required wrapper
- This is the **plugin-specific format**

**Example:**

```json
{
  "description": "Validation hooks for code quality",
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/validate.sh"
          }
        ]
      }
    ]
  }
}
```

### Settings Format (Direct)

**For user settings** in `.claude/settings.json`, use direct format (no wrapper, events at top level):

```json
{
  "PreToolUse": [...],
  "Stop": [...],
  "SessionStart": [...]
}
```

**Important:** The examples below show the hook event structure that goes inside either format. For plugin hooks.json, wrap these in `{"hooks": {...}}`.

## Hook Events

### PreToolUse

Execute before any tool runs. Use to approve, deny, or modify tool calls.

```json
{
  "PreToolUse": [
    {
      "matcher": "Write|Edit",
      "hooks": [
        {
          "type": "prompt",
          "prompt": "Validate file write safety. Check: system paths, credentials, path traversal, sensitive content. Return 'approve' or 'deny'."
        }
      ]
    }
  ]
}
```

**Output:** `hookSpecificOutput.permissionDecision` can be `allow`, `deny`, or `ask`. Use `updatedInput` to modify tool input. `systemMessage` provides explanation to Claude.

### PostToolUse

Execute after tool completes. Use to react to results, provide feedback, or log.

```json
{
  "PostToolUse": [
    {
      "matcher": "Edit",
      "hooks": [
        {
          "type": "prompt",
          "prompt": "Analyze edit result for potential issues: syntax errors, security vulnerabilities, breaking changes."
        }
      ]
    }
  ]
}
```

**Output:** Exit 0 — stdout shown in transcript. Exit 2 — stderr fed back to Claude. `systemMessage` included in context.

### Stop

Execute when main agent considers stopping. Use to validate completeness.

```json
{
  "Stop": [
    {
      "matcher": "*",
      "hooks": [
        {
          "type": "prompt",
          "prompt": "Verify task completion: tests run, build succeeded, questions answered. Return 'approve' to stop or 'block' with reason to continue."
        }
      ]
    }
  ]
}
```

**Output:** `decision` is `approve` or `block`, with `reason` and optional `systemMessage`.

### SubagentStop

Execute when subagent considers stopping. Same structure and output as Stop, but for subagents.

### UserPromptSubmit

Execute when user submits a prompt. Use to add context, validate, or block prompts.

```json
{
  "UserPromptSubmit": [
    {
      "matcher": "*",
      "hooks": [
        {
          "type": "prompt",
          "prompt": "Check if prompt requires security guidance. If discussing auth, permissions, or API security, return relevant warnings."
        }
      ]
    }
  ]
}
```

### SessionStart

Execute when Claude Code session begins. Use to load context and set environment.

```json
{
  "SessionStart": [
    {
      "matcher": "*",
      "hooks": [
        {
          "type": "command",
          "command": "bash ${CLAUDE_PLUGIN_ROOT}/scripts/load-context.sh"
        }
      ]
    }
  ]
}
```

**Special capability:** Persist environment variables using `$CLAUDE_ENV_FILE`:

```bash
echo "export PROJECT_TYPE=nodejs" >> "$CLAUDE_ENV_FILE"
```

### SessionEnd

Execute when session ends. Use for cleanup, logging, and state preservation.

### PreCompact

Execute before context compaction. Use to add critical information to preserve.

### Notification

Execute when Claude sends notifications. Use to react to user notifications.

## Hook Output Format

```json
{
  "continue": true,
  "suppressOutput": false,
  "systemMessage": "Message for Claude"
}
```

- `continue`: If false, halt processing (default true)
- `suppressOutput`: Hide output from transcript (default false)
- `systemMessage`: Message shown to Claude

### Exit Codes

- `0` — Success (stdout shown in transcript)
- `2` — Blocking error (stderr fed back to Claude)
- Other — Non-blocking error

## Hook Input Format

All hooks receive JSON via stdin with common fields:

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.txt",
  "cwd": "/current/working/dir",
  "permission_mode": "ask|allow",
  "hook_event_name": "PreToolUse"
}
```

**Event-specific fields:**

- **PreToolUse/PostToolUse:** `tool_name`, `tool_input`, `tool_result`
- **UserPromptSubmit:** `user_prompt`
- **Stop/SubagentStop:** `reason`

Access fields in prompts using `$TOOL_INPUT`, `$TOOL_RESULT`, `$USER_PROMPT`, etc.

## Environment Variables

Available in all command hooks:

- `$CLAUDE_PROJECT_DIR` — Project root path
- `$CLAUDE_PLUGIN_ROOT` — Plugin directory (use for portable paths)
- `$CLAUDE_ENV_FILE` — SessionStart only: persist env vars here
- `$CLAUDE_CODE_REMOTE` — Set if running in remote context

**Always use `${CLAUDE_PLUGIN_ROOT}` in hook commands for portability.**

## Matchers

**Exact match:** `"matcher": "Write"`

**Multiple tools:** `"matcher": "Read|Write|Edit"`

**Wildcard (all tools):** `"matcher": "*"`

**Common patterns:**

- `"Read|Write|Edit"` — all file operations
- `"Bash"` — bash commands only

Matchers are case-sensitive.

## Parallel Execution

All matching hooks run **in parallel**. Hooks don't see each other's output, ordering is non-deterministic. Design hooks for independence.

**Note:** Hooks load at session start. Changes to hook configuration require restarting Claude Code (`exit` then `claude` again).

## Additional Resources

For detailed patterns and advanced techniques, consult:

- **`references/patterns.md`** — Common hook patterns (8+ proven patterns), security, temporarily active hooks
- **`references/advanced.md`** — Advanced use cases, debugging, lifecycle details
- **`references/migration.md`** — Migrating from basic to advanced hooks
- **`examples/validate-write.sh`** — File write validation example
- **`examples/validate-bash.sh`** — Bash command validation example
- **`examples/load-context.sh`** — SessionStart context loading example
- **`scripts/validate-hook-schema.sh`** — Validate hooks.json structure
- **`scripts/test-hook.sh`** — Test hooks with sample input

## Implementation Workflow

1. Identify events to hook into (PreToolUse, Stop, SessionStart, etc.)
2. Decide between prompt-based (flexible) or command (deterministic) hooks
3. Write hook configuration in `hooks/hooks.json`
4. For command hooks, create hook scripts
5. Use `${CLAUDE_PLUGIN_ROOT}` for all file references
6. Validate configuration with `scripts/validate-hook-schema.sh hooks/hooks.json`
7. Test hooks with `scripts/test-hook.sh` before deployment
8. Test in Claude Code with `claude --debug`
9. Document hooks in plugin README

Focus on prompt-based hooks for most use cases. Reserve command hooks for performance-critical or deterministic checks.

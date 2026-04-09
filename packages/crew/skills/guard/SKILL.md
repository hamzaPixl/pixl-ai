---
name: guard
description: "Declare protected paths and safety boundaries for the current session. Prevents accidental edits to critical files or directories. Use when you want to lock down specific paths, protect production configs, or restrict edits to a specific scope."
allowed-tools: Read, Bash, Glob, Grep, Write
argument-hint: "<protect path1 [path2...] | scope path | status | clear>"
---

## Overview

Safety guardrail that lets users declare protected paths (no edits allowed) or scoped paths (only edits within scope allowed). Integrates with the session to prevent accidental modifications to critical files.

**How this differs from other features**:
- `.claude/rules/` — permanent rules. This skill sets session-scoped guards that can be cleared.
- `permissionMode: plan` — makes an agent read-only. This skill restricts WHICH files can be edited.

## Modes

### Protect Mode

Declare files or directories that should NOT be modified:

```
/guard protect .env prisma/schema.prisma packages/engine/
```

This creates a guard file that Claude checks before editing:

```bash
GUARD_FILE=".context/guard.json"
mkdir -p .context

cat > "$GUARD_FILE" <<EOF
{
  "mode": "protect",
  "protected": [".env", "prisma/schema.prisma", "packages/engine/"],
  "created": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "reason": "User-declared protected paths"
}
EOF
```

Output:
```
Guard active — protected paths:
  - .env
  - prisma/schema.prisma
  - packages/engine/**

These paths will be flagged before any edit. Use /guard clear to remove.
```

### Scope Mode

Restrict edits to ONLY the specified directories:

```
/guard scope src/api/ src/models/
```

```bash
cat > "$GUARD_FILE" <<EOF
{
  "mode": "scope",
  "allowed": ["src/api/", "src/models/"],
  "created": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "reason": "User-declared edit scope"
}
EOF
```

Output:
```
Guard active — edits scoped to:
  - src/api/**
  - src/models/**

Files outside this scope will be flagged before any edit. Use /guard clear to remove.
```

### Status Mode

Show current guard state:

```
/guard status
```

Read `.context/guard.json` and display the current guards.

### Clear Mode

Remove all guards:

```
/guard clear
```

```bash
rm -f ".context/guard.json"
```

## How Guards Are Enforced

After creating the guard file, Claude should check it before every file edit:

1. Before using Edit or Write tools, check if `.context/guard.json` exists
2. If `mode: "protect"` — verify the target file is NOT in the protected list
3. If `mode: "scope"` — verify the target file IS within the allowed directories
4. If a guard would be violated, warn the user and ask for confirmation before proceeding

### Guard Check Logic

```
For each file about to be edited:
  if guard.mode == "protect":
    if file matches any protected pattern → WARN
  if guard.mode == "scope":
    if file does NOT match any allowed pattern → WARN
```

Pattern matching:
- Exact file paths match exactly: `.env` matches only `.env`
- Directory paths match recursively: `src/api/` matches `src/api/anything/nested.ts`
- Glob patterns are supported: `*.sql` matches any SQL file

## Common Use Cases

```
# Protect production configs during development
/guard protect .env .env.production docker-compose.yml

# Focus refactoring to one module
/guard scope packages/billing/

# Protect the database schema during a feature build
/guard protect prisma/schema.prisma migrations/

# Lock down shared contracts while implementing
/guard protect packages/contracts/
```

## Gotchas

- Guards are session-scoped — they don't persist across Claude sessions (by design)
- Guards are advisory, not enforced by the filesystem — they rely on Claude checking the guard file
- The guard file is stored in `.context/` which should be gitignored
- Scope mode with too narrow a scope can be frustrating — make sure to include test files if doing TDD
- Guards don't apply to Bash commands (only Edit/Write) — `sed` or `echo >` would bypass them

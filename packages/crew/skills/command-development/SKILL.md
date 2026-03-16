---
name: command-development
description: "Create slash commands for Claude Code plugins. Use when defining reusable prompts with frontmatter, arguments, file references, or interactive workflows."
allowed-tools: Read, Glob, Grep, Write, Edit, Bash
argument-hint: "<command-name or description of command to create>"
---

# Command Development for Claude Code

## Overview

Slash commands are frequently-used prompts defined as Markdown files that Claude executes during interactive sessions. Understanding command structure, frontmatter options, and dynamic features enables creating powerful, reusable workflows.

## Command Basics

### Critical: Commands are Instructions FOR Claude

**Commands are written for agent consumption, not human consumption.**

When a user invokes `/command-name`, the command content becomes Claude's instructions. Write commands as directives TO Claude about what to do, not as messages TO the user.

**Correct approach (instructions for Claude):**

```markdown
Review this code for security vulnerabilities including:

- SQL injection
- XSS attacks
- Authentication issues

Provide specific line numbers and severity ratings.
```

**Incorrect approach (messages to user):**

```markdown
This command will review your code for security issues.
You'll receive a report with vulnerability details.
```

The first example tells Claude what to do. The second tells the user what will happen but doesn't instruct Claude. Always use the first approach.

### Command Locations

- **Project commands** (`.claude/commands/`): Shared with team, shown as "(project)" in `/help`
- **Personal commands** (`~/.claude/commands/`): Available in all projects, shown as "(user)" in `/help`
- **Plugin commands** (`plugin-name/commands/`): Available when plugin installed, shown as "(plugin-name)" in `/help`

## File Format

Commands are Markdown files with `.md` extension. No frontmatter needed for basic commands:

```markdown
Review this code for security vulnerabilities including:

- SQL injection
- XSS attacks
- Authentication bypass
```

With YAML frontmatter for configuration:

```markdown
---
description: Review code for security issues
allowed-tools: Read, Grep, Bash(git:*)
model: sonnet
---

Review this code for security vulnerabilities...
```

## YAML Frontmatter Fields

### description

Brief description shown in `/help`. String, defaults to first line of command prompt. Keep under 60 characters.

```yaml
description: Review pull request for code quality
```

### allowed-tools

Specify which tools the command can use. String or array, inherits from conversation by default. Patterns: `Read, Write, Edit` (specific tools), `Bash(git:*)` (scoped bash), `*` (all tools).

```yaml
allowed-tools: Read, Write, Edit, Bash(git:*)
```

### model

Model for command execution: `haiku` (fast/simple), `sonnet` (standard), `opus` (complex analysis). Inherits from conversation by default.

```yaml
model: haiku
```

### argument-hint

Document expected arguments for autocomplete. Helps users understand command interface.

```yaml
argument-hint: [pr-number] [priority] [assignee]
```

### disable-model-invocation

Prevent SlashCommand tool from programmatically calling command. Boolean, defaults to false. Use when command should only be manually invoked.

```yaml
disable-model-invocation: true
```

## Dynamic Arguments

### $ARGUMENTS

Capture all arguments as a single string:

```markdown
---
argument-hint: [issue-number]
---

Fix issue #$ARGUMENTS following our coding standards and best practices.
```

Usage: `/fix-issue 123` expands to `Fix issue #123 following our coding standards...`

### Positional Arguments

Capture individual arguments with `$1`, `$2`, `$3`:

```markdown
---
argument-hint: [pr-number] [priority] [assignee]
---

Review pull request #$1 with priority level $2.
After review, assign to $3 for follow-up.
```

Usage: `/review-pr 123 high alice` expands each positional variable.

## File References

Include file contents in commands using `@` syntax:

```markdown
---
argument-hint: [file-path]
---

Review @$1 for:

- Code quality
- Best practices
- Potential bugs
```

Usage: `/review-file src/api/users.ts` — Claude reads the file before processing the command. Use `@path/to/file` for static references and `@$1` for dynamic references from arguments.

## Bash Execution in Commands

Commands can execute bash commands inline to dynamically gather context before Claude processes the command (git status, environment vars, project state, etc.).

For complete syntax, examples, and best practices, see `references/plugin-features-reference.md` section on bash execution.

## Command Organization

**Flat structure** (5-15 commands, no clear categories):

```
.claude/commands/
├── build.md
├── test.md
├── deploy.md
└── review.md
```

**Namespaced structure** (15+ commands, clear categories):

```
.claude/commands/
├── ci/
│   ├── build.md        # /build (project:ci)
│   └── test.md         # /test (project:ci)
├── git/
│   ├── commit.md       # /commit (project:git)
│   └── pr.md           # /pr (project:git)
└── docs/
    └── generate.md     # /generate (project:docs)
```

Subdirectory names become namespace labels shown in `/help`.

## Best Practices

### Command Design

1. **Single responsibility:** One command, one task
2. **Clear descriptions:** Self-explanatory in `/help`
3. **Explicit dependencies:** Use `allowed-tools` when needed
4. **Document arguments:** Always provide `argument-hint`
5. **Consistent naming:** Use verb-noun pattern (review-pr, fix-issue)

### Argument Handling

1. **Validate arguments:** Check for required arguments in prompt
2. **Provide defaults:** Suggest defaults when arguments missing
3. **Document format:** Explain expected argument format
4. **Handle edge cases:** Consider missing or invalid arguments

### File References

1. **Explicit paths:** Use clear file paths
2. **Check existence:** Handle missing files gracefully
3. **Relative paths:** Use project-relative paths

### Bash Commands

1. **Limit scope:** Use `Bash(git:*)` not `Bash(*)`
2. **Safe commands:** Avoid destructive operations
3. **Handle errors:** Consider command failures
4. **Keep fast:** Long-running commands slow invocation

## Additional Resources

For detailed patterns and advanced usage, consult:

- **`references/plugin-features-reference.md`** — Plugin-specific features, `${CLAUDE_PLUGIN_ROOT}`, validation patterns
- **`references/frontmatter-reference.md`** — Complete frontmatter field specifications
- **`references/advanced-workflows.md`** — Multi-component workflows, agent/skill/hook integration
- **`examples/simple-commands.md`** — Basic command examples
- **`examples/plugin-commands.md`** — Plugin-specific command examples

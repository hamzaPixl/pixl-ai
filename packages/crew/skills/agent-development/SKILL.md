---
name: agent-development
description: "Create subagent definitions for Claude Code plugins. Use when writing agent frontmatter, designing triggering descriptions with examples, or defining system prompts and tool access."
allowed-tools: Read, Glob, Grep, Write, Edit, Bash
argument-hint: "<agent-name or description of agent to create>"
disable-model-invocation: true
---

# Agent Development for Claude Code Plugins

## Overview

Agents are autonomous subprocesses that handle complex, multi-step tasks independently. Understanding agent structure, triggering conditions, and system prompt design enables creating powerful autonomous capabilities.

**Key concepts:**

- Agents are FOR autonomous work, commands are FOR user-initiated actions
- Markdown file format with YAML frontmatter
- Triggering via description field with examples
- System prompt defines agent behavior
- Model and color customization

## Agent File Structure

### Complete Format

```markdown
---
name: agent-identifier
description: Use this agent when [triggering conditions]. Examples:

<example>
Context: [Situation description]
user: "[User request]"
assistant: "[How assistant should respond and use this agent]"
<commentary>
[Why this agent should be triggered]
</commentary>
</example>

<example>
[Additional example...]
</example>

model: inherit
color: blue
tools: ["Read", "Write", "Grep"]
---

You are [agent role description]...

**Your Core Responsibilities:**

1. [Responsibility 1]
2. [Responsibility 2]

**Analysis Process:**
[Step-by-step workflow]

**Output Format:**
[What to return]
```

## Frontmatter Fields

### name (required)

Agent identifier used for namespacing and invocation.

**Format:** lowercase, numbers, hyphens only | **Length:** 3-50 characters | **Pattern:** Must start and end with alphanumeric

**Good examples:** `code-reviewer`, `test-generator`, `api-docs-writer`, `security-analyzer`

### description (required)

Defines when Claude should trigger this agent. **This is the most critical field.**

**Must include:**

1. Triggering conditions ("Use this agent when...")
2. Multiple `<example>` blocks showing usage
3. Context, user request, and assistant response in each example
4. `<commentary>` explaining why agent triggers

**Format:**

```
Use this agent when [conditions]. Examples:

<example>
Context: [Scenario description]
user: "[What user says]"
assistant: "[How Claude should respond]"
<commentary>
[Why this agent is appropriate]
</commentary>
</example>
```

**Best practices:** Include 2-4 concrete examples. Show proactive and reactive triggering. Cover different phrasings of same intent. Be specific about when NOT to use the agent.

### model (required)

**Options:** `inherit` (recommended — uses parent model), `sonnet` (balanced), `opus` (most capable, expensive), `haiku` (fast, cheap).
Use `inherit` unless the agent needs specific model capabilities.

### color (required)

**Options:** `blue`, `cyan`, `green`, `yellow`, `magenta`, `red`

Choose distinct colors for different agents in the same plugin. Conventions: blue/cyan for analysis/review, green for success-oriented tasks, yellow for validation, red for security/critical, magenta for creative/generation.

### tools (optional)

Restrict agent to specific tools. If omitted, agent has access to all tools. Limit to minimum needed (principle of least privilege).

**Common tool sets:**

- Read-only analysis: `["Read", "Grep", "Glob"]`
- Code generation: `["Read", "Write", "Grep"]`
- Testing: `["Read", "Bash", "Grep"]`
- Full access: Omit field or use `["*"]`

## System Prompt Design

The markdown body becomes the agent's system prompt. Write in second person, addressing the agent directly.

### Structure

```markdown
You are [role] specializing in [domain].

**Your Core Responsibilities:**

1. [Primary responsibility]
2. [Secondary responsibility]
3. [Additional responsibilities...]

**Analysis Process:**

1. [Step one]
2. [Step two]
3. [Step three]

**Quality Standards:**

- [Standard 1]
- [Standard 2]

**Output Format:**
Provide results in this format:

- [What to include]
- [How to structure]

**Edge Cases:**
Handle these situations:

- [Edge case 1]: [How to handle]
- [Edge case 2]: [How to handle]
```

### Best Practices

**DO:** Write in second person ("You are...", "You will..."). Be specific about responsibilities. Provide step-by-step process. Define output format. Include quality standards. Address edge cases. Keep under 10,000 characters.

**DON'T:** Write in first person. Be vague or generic. Omit process steps. Leave output format undefined. Skip quality guidance. Ignore error cases.

## Creating Agents

### Method 1: AI-Assisted Generation

Use the prompt pattern in `examples/agent-creation-prompt.md` to generate agent configuration via AI, then convert to frontmatter format.

See `references/agent-creation-system-prompt.md` for the exact prompt Claude Code uses internally.

### Method 2: Manual Creation

1. Choose agent identifier (3-50 chars, lowercase, hyphens)
2. Write description with examples
3. Select model (usually `inherit`)
4. Choose color for visual identification
5. Define tools (if restricting access)
6. Write system prompt with structure above
7. Save as `agents/agent-name.md`

## Validation Rules

**Identifier:** 3-50 characters, lowercase letters/numbers/hyphens only, must start and end with alphanumeric. No underscores, spaces, or special characters.

**Description:** 10-5,000 characters. Must include triggering conditions and examples. Best: 200-1,000 characters with 2-4 examples.

**System Prompt:** 20-10,000 characters. Best: 500-3,000 characters. Must have clear responsibilities, process, and output format.

**Testing:** Write agent with specific triggering examples, test with similar phrasing, verify Claude loads the agent and follows the system prompt process.

## Additional Resources

For detailed guidance and templates:

- **`references/system-prompt-design.md`** — Complete system prompt patterns
- **`references/triggering-examples.md`** — Example formats and best practices
- **`references/agent-creation-system-prompt.md`** — The exact prompt from Claude Code
- **`examples/agent-creation-prompt.md`** — AI-assisted agent generation template
- **`examples/complete-agent-examples.md`** — Full agent examples for different use cases
- **`scripts/validate-agent.sh`** — Validate agent file structure

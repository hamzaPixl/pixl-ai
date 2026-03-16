---
paths: agents/**/*.md
---

# Agent Authoring Rules

- YAML frontmatter is required with: `name`, `description`, `color`, `tools`, `maxTurns`
- `color` is mandatory — one of: red, green, yellow, blue, magenta, cyan, white
- `description` must contain at least 3 `<example>` blocks for reliable agent triggering
- Each example must include `user:`, `assistant:`, and `<commentary>` elements
- Agent body should define: Role, Constraints/Checklist, Output Format

## Model Selection

- `model: opus` — agents that make high-stakes decisions or need deep reasoning: `orchestrator`, `architect`, `tech-lead`, `security-engineer`
- `model: sonnet` — pattern-following agents where speed and cost matter over deep reasoning: `product-owner`, `qa-engineer`, `devops-engineer`
- `model: inherit` — implementation agents that follow established patterns but may benefit from parent model capabilities: `frontend-engineer`, `backend-engineer`, `fullstack-engineer`
- `model: haiku` — fast, read-only exploration where speed > depth: `explorer`

Rule of thumb: if the agent reviews, designs, or coordinates → opus. If it implements complex features → inherit. If it follows patterns (planning, testing, DevOps) → sonnet. If it only searches → haiku.

## Memory Strategy

- `memory: project` — agents that accumulate project-specific knowledge across sessions: `orchestrator`, `architect`, `tech-lead`, `security-engineer`
- `memory: user` — agents that learn user preferences across projects: `explorer`
- No memory field — stateless agents that operate on explicit context each time: implementation agents (`frontend-engineer`, `backend-engineer`, etc.)

Rule of thumb: if the agent needs to remember architectural decisions or review patterns → project memory. If it adapts to user habits → user memory. If it just executes → no memory.

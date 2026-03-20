# Model Routing Guide

Cost-optimized model selection for pixl-crew agents. Static assignments — no runtime switching.

## Decision Matrix

| Task Type                                           | Model     | Rationale                          | ~Cost Savings |
| --------------------------------------------------- | --------- | ---------------------------------- | ------------- |
| Architecture decisions, code review, security audit | `opus`    | Deep reasoning, nuanced judgment   | Baseline      |
| Multi-agent coordination                            | `opus`    | Complex orchestration logic        | Baseline      |
| React/Next.js implementation                        | `inherit` | Benefits from parent model depth   | 0%            |
| Backend/fullstack implementation                    | `inherit` | Complex domain logic possible      | 0%            |
| Task planning, sprint breakdown                     | `sonnet`  | Decomposition is pattern-following | ~40%          |
| Test writing, QA review                             | `sonnet`  | Test patterns are well-established | ~40%          |
| Docker, CI/CD, Makefile                             | `sonnet`  | Infrastructure is template-driven  | ~40%          |
| Codebase exploration                                | `haiku`   | Speed > depth for search tasks     | ~80%          |

## Agent Assignments

```
opus:    orchestrator, architect, tech-lead, security-engineer
sonnet:  product-owner, qa-engineer, devops-engineer
inherit: frontend-engineer, backend-engineer, fullstack-engineer
haiku:   explorer
```

## When to Override

Override the default model when:

1. **Upgrade to opus**: The agent faces an unusually complex decision (e.g., QA engineer reviewing a novel concurrency pattern)
2. **Downgrade to sonnet**: The implementation agent is doing repetitive scaffolding, not creative design
3. **Never downgrade opus agents**: Architecture and security decisions always warrant deep reasoning

## Thinking & Effort Levels

Claude Code supports adaptive reasoning via extended thinking. Control it with `/effort` or the `ultrathink` keyword.

| Level | Trigger | Best For |
|-------|---------|----------|
| **Low** (`/effort low`) | Simple file edits, formatting, renaming | Minimal reasoning overhead |
| **Medium** (default) | Standard implementation, test writing | Balanced speed and depth |
| **High** (`/effort high`) | Complex architecture, multi-file refactors | Deep reasoning chains |
| **Ultra** (`ultrathink` keyword) | Security audits, novel algorithm design, subtle bugs | Maximum reasoning depth |

### When to Use Deep Thinking

- **Architecture decisions**: Bounded context mapping, service decomposition, API contract design
- **Security audits**: OWASP analysis, RBAC review, threat modeling
- **Subtle bugs**: Race conditions, edge cases, data consistency issues
- **Complex refactors**: Multi-module restructuring, migration planning

### When to Use Low Effort

- **Formatting and style**: Code formatting, import sorting, renaming
- **Simple scaffolding**: Adding a new file from a known pattern
- **Repetitive edits**: Applying the same change across multiple files
- **Quick lookups**: Finding a function definition, checking a type

### Configuration

- **Per-session**: `/effort low|medium|high` or `Option+T` to toggle thinking visibility
- **Per-prompt**: Include `ultrathink` in your message for maximum depth on that request
- **Environment**: `MAX_THINKING_TOKENS` env var caps reasoning budget
- **Verbose mode**: `Ctrl+O` to see the reasoning process

### Agent Implications

Opus agents (orchestrator, architect, tech-lead, security-engineer) benefit most from extended thinking. Haiku agents (explorer) have minimal thinking overhead by design. For inherit-model agents, thinking depth follows the parent session's effort level.

## Cost Impact

Moving 3 agents from inherit→sonnet saves ~40% on those specific agent calls. For a typical session with mixed agent usage, expect 15-25% overall cost reduction.

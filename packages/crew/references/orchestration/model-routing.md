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

## Cost Impact

Moving 3 agents from inherit→sonnet saves ~40% on those specific agent calls. For a typical session with mixed agent usage, expect 15-25% overall cost reduction.

# Writing Plans

## Implementation Plan Structure

A good implementation plan has:

1. **Context** — What problem are we solving and why
2. **Scope** — What's in and out of scope
3. **Phases** — 3-6 atomic phases, each independently testable
4. **Tasks per phase** — Ordered by dependency
5. **Acceptance criteria** — How we know each phase is done
6. **Risks** — What could go wrong and mitigations

## Phase Design Rules

- Each phase must be independently deployable
- Each phase must have its own verification step
- No phase should depend on "everything before it" — be specific
- 3-6 phases is the sweet spot (fewer = too coarse, more = too granular)

## Task Writing Rules

- Imperative form: "Add authentication middleware" not "Authentication middleware should be added"
- Include acceptance criteria as checkboxes
- Specify which agent should handle the task
- Estimate complexity (S/M/L)
- Note dependencies explicitly

## Anti-patterns

- Plans that describe WHAT not HOW (too vague to execute)
- Plans that describe HOW not WHAT (too prescriptive, no room for judgment)
- Plans with "Phase 1: Setup" that isn't independently valuable
- Plans where every task depends on the previous one (no parallelism)
- Plans without verification steps

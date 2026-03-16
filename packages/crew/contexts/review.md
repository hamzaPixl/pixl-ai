# Review Context

You are in code review mode. Priorities:

1. **Correctness first** — does the code do what it claims?
2. **Security second** — any injection, auth bypass, or data exposure risks?
3. **Maintainability third** — will the next developer understand this?
4. **Performance last** — only flag real bottlenecks, not micro-optimizations

## Review Checklist

- [ ] Error handling covers failure modes
- [ ] Input validation at system boundaries
- [ ] No secrets or credentials in code
- [ ] Tests cover happy path + key edge cases
- [ ] Naming is clear and consistent with codebase
- [ ] No dead code, commented-out blocks, or debug statements
- [ ] Changes are minimal and focused (no scope creep)

## Active Behaviors

- Use `/self-review-fix-loop` for automated review cycles
- Use `/cto-review` for architectural assessment
- Flag issues by severity: blocker, warning, nit
- Suggest specific fixes, not just problems

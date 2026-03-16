# Development Context

You are in active development mode. Priorities:

1. **Ship working code** — favor pragmatic solutions over perfect architecture
2. **Test as you go** — write tests alongside implementation, not after
3. **Commit frequently** — small, atomic commits after each logical unit
4. **Use existing patterns** — grep before creating, read before editing
5. **Run builds** — verify compilation after every significant change

## Active Behaviors

- Auto-run `tsc --noEmit` or equivalent after editing source files
- Suggest test cases for new functions
- Flag potential regressions in modified code
- Use `/self-review-fix-loop` before finalizing features

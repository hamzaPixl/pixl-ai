# Crew Workflow Rules

## Explore → Plan → Implement → Commit

1. **Explore** — understand the codebase before making changes (use `explorer` agent or Glob/Grep)
2. **Plan** — enter plan mode for multi-file changes; get user approval before writing code
3. **Implement** — write code using the appropriate specialist agent or skill
4. **Commit** — commit after each logical unit; don't accumulate large diffs

## Skills Over Ad-Hoc Prompts

Before building anything manually, check if a skill handles it:

- Building a website? → `/website`
- New backend service? → `/saas-microservice` or `/fastapi-api`
- Need a full-stack app? → `/fullstack-app`
- Adding DDD patterns? → `/ddd-pattern`
- Code quality issues? → `/self-review-fix-loop` or `/code-reduction`
- Reviewing a PR? → `/code-review`
- Planning tasks? → `/task-plan` then `/sprint-planning`
- Security audit? → `/security-scan`
- Wrapping up a session? → `/session-wrap`

See `skills/ROUTING.md` for the full decision tree.

## Frequent Commits

- Commit after completing each logical unit of work (feature, fix, refactor step)
- Commit before switching to a different area of the codebase
- Commit before running risky operations (large refactors, dependency updates)
- Use conventional commit messages: `feat:`, `fix:`, `refactor:`, `chore:`, `docs:`

## Background Tasks

- Run dev servers, builds, and watchers as background tasks (`run_in_background: true`)
- Do NOT sleep-poll — you get notified when background tasks complete

## Parallel Execution

- Launch multiple agents concurrently when tasks are independent
- Run independent file reads, searches, and tool calls in a single message
- Use `isolation: "worktree"` for agents that modify files independently

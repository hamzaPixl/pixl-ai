---
description: Workflow patterns — background tasks, parallel execution, frequent commits
globs: "**/*"
---

# Workflow Rules

## Background Tasks

Run long-running processes (dev servers, builds, watchers) as background tasks:

- Use `run_in_background: true` for dev servers, test suites, build processes
- Do NOT sleep-poll — you get notified when background tasks complete
- Run independent commands in parallel (separate Bash calls in one message)

## Parallel Execution

Maximize parallelism for independent work:

- Launch multiple subagents concurrently when tasks don't depend on each other
- Run independent file reads, glob searches, and grep calls in a single message
- Split test suites across parallel background tasks when possible
- Use `isolation: "worktree"` for agents that modify files independently

## Frequent Commits

Commit early and often — don't accumulate large changesets:

- Commit after completing each logical unit of work (feature, fix, refactor step)
- Commit before switching to a different area of the codebase
- Commit before running risky operations (large refactors, dependency updates)
- Use conventional commit messages: `feat:`, `fix:`, `refactor:`, `chore:`, `docs:`
- Each commit should be atomic — one logical change, passes tests on its own

## Back-Pressure: Silent Success, Verbose Failure

Verification output should only surface errors — never flood context with success:

- **Tests**: use `--quiet` / `--tb=short` by default. Only show failing test names + error messages
- **Linters/typecheckers**: hooks already emit to stderr on failure and stay silent on success
- **Build output**: suppress success banners. Only show errors and warnings
- **Full test suites**: run in background or via `make test` (RTK-compressed). Subset tests during development; full suite before commit
- Never pipe 200 lines of "PASSED" into context — it costs tokens and causes drift

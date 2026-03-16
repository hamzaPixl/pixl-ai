# Git Workflow

> See also: `references/standards/commit-conventions.md` for extended commit message examples and `references/standards/pr-best-practices.md` for PR description templates.

## Conventional Commits

Use the format: `type(scope): description`

| Type         | When                                       |
| ------------ | ------------------------------------------ |
| `feat`       | New feature or capability                  |
| `fix`        | Bug fix                                    |
| `refactor`   | Code change that neither fixes nor adds    |
| `chore`      | Build, tooling, dependency updates         |
| `docs`       | Documentation only                         |
| `test`       | Adding or fixing tests                     |
| `perf`       | Performance improvement                    |
| `ci`         | CI/CD pipeline changes                     |
| `style`      | Formatting, whitespace (no logic change)   |

## Branch Naming

- `feat/short-description` — new features
- `fix/issue-number-or-description` — bug fixes
- `refactor/what-is-changing` — refactoring
- `chore/task-description` — maintenance

## PR Hygiene

- Keep PRs under 400 lines when possible — split large changes
- One logical change per PR — don't bundle unrelated fixes
- Write a description that explains WHY, not just WHAT
- Link to issues/tickets in the PR body
- Request review from domain owners

## Commit Practices

- Each commit should compile and pass tests on its own
- Don't commit commented-out code — delete it (git has history)
- Don't commit TODO/FIXME without a linked issue
- Squash fixup commits before merging

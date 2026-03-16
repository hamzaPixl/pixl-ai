# Commit Conventions

## Format

```
type(scope): description

[optional body]

[optional footer]
```

## Types

| Type | Purpose | Changelog |
|------|---------|-----------|
| `feat` | New feature | Yes |
| `fix` | Bug fix | Yes |
| `docs` | Documentation only | No |
| `style` | Formatting, whitespace | No |
| `refactor` | Code change (no feature/fix) | No |
| `perf` | Performance improvement | Yes |
| `test` | Adding/fixing tests | No |
| `chore` | Build, tooling, deps | No |
| `ci` | CI/CD changes | No |
| `build` | Build system changes | No |
| `revert` | Reverts a previous commit | Yes |

## Description Rules

- Imperative mood: "add" not "added" or "adds"
- Lowercase first letter
- No period at end
- Max 50 characters

## Five Core Rules

1. **One logical change per commit** — not bug fix + feature + refactor in one
2. **Each commit must be deployable** — tests pass, build succeeds, no regressions
3. **Run tests before committing**
4. **Messages explain WHY not WHAT** — the diff shows what changed
5. **Review `git diff --staged` before committing**

## Breaking Changes

Use `BREAKING CHANGE:` footer or `!` after type:

```
feat(api)!: remove deprecated /v1 endpoints

BREAKING CHANGE: /v1 endpoints removed, use /v2
```

## Multi-Line Commits

For complex changes, add a body:

```
fix(auth): prevent session fixation on login

The session ID was not regenerated after successful
authentication, allowing an attacker who set the
session cookie to hijack the authenticated session.
```

## Amending

- Only amend unpushed commits
- Only amend the last commit
- Never amend pushed commits

## Common Mistakes

| Mistake | Problem | Fix |
|---------|---------|-----|
| "misc changes" | No useful information | Separate into logical commits |
| Repeated "fix typo" | Hard to track real changes | Squash typo fixes together |
| WIP commits | Not deployable | Squash before pushing |
| Mixing unrelated changes | Can't revert independently | One change per commit |
| Amending after push | Rewrites shared history | New commit instead |

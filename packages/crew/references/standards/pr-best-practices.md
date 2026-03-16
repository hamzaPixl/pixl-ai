# PR Best Practices

## Before Creating a PR

1. **Rebase on latest main**
   ```bash
   git fetch origin main && git rebase origin/main
   ```
2. **Run all checks** — tests, lint, type-check, build must all pass
3. **Self-review the diff** — `git diff origin/main` checking for debug code, TODOs, commented-out code, unclear names
4. **Clean up commits** — squash/reword via interactive rebase if history is messy

## PR Title

Follow conventional commit format: `type(scope): description`

## PR Body Template

```markdown
## Summary
[1-2 sentences: what and why]

## Changes
- [Bullet list of what changed]

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing done

## Screenshots
| Before | After |
|--------|-------|
| (if UI changes) | |

## Checklist
- [ ] Tests pass
- [ ] No debug code
- [ ] Documentation updated
```

## Size Guidelines

| Size | Lines Changed | Risk | Action |
|------|--------------|------|--------|
| XS | <50 | Low | Quick review |
| S | 50-200 | Low | Normal review |
| M | 200-500 | Medium | Thorough review |
| L | 500-1000 | High | Consider splitting |
| XL | >1000 | Very High | Must split |

**Ideal:** 200-400 lines.

### Splitting Strategies

- Feature flags: merge infrastructure first, then feature
- Refactor vs feature: separate structural changes from behavior changes
- Backend vs frontend: split by layer
- Migration vs logic: database changes separate from application logic

## Creating with `gh`

```bash
gh pr create --title "type(scope): description" --body "$(cat <<'EOF'
## Summary
...

## Changes
...

## Testing
...
EOF
)"
```

## Handling Review Feedback

1. Address every comment
2. Commit fixes: `fix: address review feedback`
3. Push changes
4. Reply to resolved threads
5. Re-request review

## Merge Strategies

| Strategy | When |
|----------|------|
| Squash merge | Multiple small commits (default) |
| Rebase merge | Meaningful, clean commit history |
| Regular merge | Branch protection requires it |

## Pre-Merge Checklist

- [ ] All review comments addressed
- [ ] CI passing
- [ ] Branch up to date with main
- [ ] No merge conflicts

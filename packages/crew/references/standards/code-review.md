# Code Review

## Review Process

1. **Understand context** — Read PR description, linked issues, acceptance criteria
2. **First pass** — High-level structure and approach
3. **Second pass** — Detailed implementation review
4. **Third pass** — Quality and standards

## Checklist

### Correctness
- Solves the stated problem
- Edge cases handled
- Error handling present and appropriate
- No off-by-one errors
- Null/undefined cases handled
- Concurrency safe (if applicable)

### Code Quality
- Readable without extensive comments
- Clear, descriptive names
- No unnecessary complexity
- Follows project conventions
- No dead code
- No duplication

### Security
- Inputs validated and sanitized
- No injection vulnerabilities (SQL, XSS, command)
- Sensitive data protected (not logged, not exposed)
- Authentication checked where required
- Authorization enforced
- No hardcoded secrets

### Performance
- No N+1 queries
- Resources properly managed (connections, handles closed)
- No unnecessary work in loops
- Appropriate data structures
- Caching considered where beneficial

### Testing
- Happy path covered
- Edge cases tested
- Error cases tested
- Tests are readable and maintainable
- Tests verify behavior, not implementation
- Mocks used appropriately (not excessively)

### Documentation
- Public APIs documented
- Complex logic explained
- README updated if needed
- Breaking changes documented

## Issue Severity

| Level | Meaning | Action |
|-------|---------|--------|
| **Critical** | Security, data corruption, breaking changes, test failures, logic errors | Block merge |
| **Important** | Performance issues, missing error handling, insufficient coverage | Should fix |
| **Minor** | Style improvements, documentation gaps, naming suggestions | Nice to have |
| **Nitpick** | Personal preference, optional polish | Optional |

## Feedback Format

- Be specific — quote code, reference line numbers
- Explain why — not just "don't do this" but why it matters
- Suggest alternatives with rationale
- Use severity prefixes: `[Critical]`, `[Important]`, `[Minor]`, `[Nit]`

## Review Output

```markdown
## Review Summary
[1-2 sentence overview]

## Critical Issues
[Must fix before merge]

## Important Issues
[Should fix]

## Minor Issues
[Nice to have]

## Positive Notes
[What was done well]

## Verdict
[Approve | Approve with comments | Request changes]
```

## Self-Review Checklist

Before requesting review, ask yourself:

1. Would I understand this code in 6 months?
2. Are edge cases tested?
3. Any security concerns?
4. Is this the simplest solution?
5. Is all debug code removed?
6. Are tests passing?
7. Would I approve this PR?

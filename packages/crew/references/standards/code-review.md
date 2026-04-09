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

## Confidence Scoring Standard

Every finding across all audit and review skills must include a confidence score (1-100).

| Score | Level | Behavior |
|-------|-------|----------|
| 90-100 | **Near certain** | Always surface. Evidence is concrete (stack trace, test failure, provable logic error). |
| 80-89 | **High confidence** | Surface by default. Strong evidence but not provable without execution. |
| 60-79 | **Moderate** | Filtered by default. Add caveat: "likely" or "potential". Surface with `--threshold 60`. |
| 40-59 | **Low confidence** | Suppress to appendix. Only flag if P0-severity (security, data loss). |
| 1-39 | **Speculative** | Never surface unless explicitly asked. Speculation wastes reviewer attention. |

**Confidence boosters** (add to base score):
- Multiple reviewers flag same issue: +10
- Issue matches known anti-pattern from this checklist: +5
- Issue is in a critical path (auth, payments, data integrity): +5
- Code pattern has caused bugs before (from instincts/memory): +5

**Confidence penalties** (subtract from base score):
- Finding is based on naming alone (no logic analysis): -10
- Code context is incomplete (can't see full function): -15
- Issue depends on runtime behavior not visible in static review: -10

**Fix classification** (applies to `/code-review`, `/self-review-fix-loop`, `/cto-review`):

| Class | Criteria | Examples |
|-------|----------|----------|
| **AUTO-FIX** | Mechanical, unambiguous, no design decisions | Unused imports, missing `await`, formatting, type annotations |
| **ASK** | Requires judgment, multiple valid approaches | Architecture changes, new abstractions, performance trade-offs |

This standard applies to: `/code-review`, `/cto-review`, `/security-scan`, `/api-audit`, `/schema-audit`, `/dependency-review`.

## Feedback Format

- Be specific — quote code, reference line numbers
- Explain why — not just "don't do this" but why it matters
- Suggest alternatives with rationale
- Use severity prefixes: `[Critical]`, `[Important]`, `[Minor]`, `[Nit]`
- Include confidence score: `[95%]` or `[High]`

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

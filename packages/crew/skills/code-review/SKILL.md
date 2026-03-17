---
name: code-review
description: "Multi-agent PR review with confidence scoring. Runs 3 parallel reviewers on a PR diff (bugs, security, conventions), deduplicates findings, posts high-confidence comments. Use when reviewing a PR, auditing changes before merge, or running automated review on a branch."
allowed-tools: Read, Bash, Glob, Grep
argument-hint: "[PR number or branch name]"
---

## Overview

Structured multi-agent code review for pull requests. Three parallel reviewers analyze the diff through specialized lenses (correctness, security, conventions), findings are deduplicated and scored for confidence, and only high-confidence issues surface to the user or get posted as PR comments.

**How this differs from other review skills**:
- `/self-review-fix-loop` — reviews AND fixes working tree changes. This skill is read-only.
- `/cto-review` — architectural critique of the full branch state. This skill focuses on the PR diff.
- Tech-lead agent — general quality gate. This skill runs specialized parallel reviewers with confidence scoring.

## Step 1: Get the Diff

Determine the review target and extract the diff:

- **PR number provided**: `gh pr diff <number>` to get the diff, `gh pr view <number> --json title,body,baseRefName,headRefName` for context
- **Branch name provided**: `git diff main...<branch>` (or the appropriate base branch)
- **Nothing provided**: `git diff main...HEAD` for the current branch against main

Also gather:
- List of changed files: `gh pr diff <number> --name-only` or `git diff --name-only main...HEAD`
- PR description (if available) for intent context

## Step 2: Review (Parallel — 3 Agents)

Spawn **3 reviewer agents** (Explore type, read-only) in parallel. Each reviewer receives the full diff and the list of changed files.

### Reviewer A: Correctness

Focus: bugs, logic errors, edge cases, error handling, data integrity.

Checklist:
- Off-by-one errors, null/undefined access, unhandled promise rejections
- Missing error handling on I/O operations
- Race conditions in async code
- State mutations that could cause unexpected side effects
- Incomplete migrations (schema changed but queries not updated)

### Reviewer B: Security

Focus: OWASP Top 10, auth gaps, injection, secrets, data exposure.

Checklist (from `references/standards/code-review.md`):
- SQL/NoSQL injection via string concatenation
- Missing auth/authorization checks on new endpoints
- Hardcoded secrets, API keys, or credentials
- XSS vectors in rendered output
- SSRF via unvalidated URLs
- Mass assignment (accepting unvalidated fields)
- Sensitive data in logs or error messages

### Reviewer C: Conventions

Focus: project standards, naming, patterns, CLAUDE.md compliance.

Checklist:
- Naming conventions (files, variables, functions, types)
- Import organization and grouping
- Error handling patterns match existing codebase
- Test coverage for new logic
- Consistent API response shapes
- No unnecessary complexity or over-engineering

Each reviewer returns findings in this format:

```json
{
  "reviewer": "A|B|C",
  "findings": [
    {
      "file": "src/api/users.ts",
      "line": 42,
      "severity": "Critical|Important|Minor",
      "category": "correctness|security|convention",
      "description": "Missing null check on user lookup result",
      "confidence": 95,
      "suggestion": "Add early return if user is null before accessing properties"
    }
  ]
}
```

## Step 3: Consolidate

Merge all findings and deduplicate:

1. **Deduplicate**: Same file + same line + similar description = one finding. Keep the highest confidence score.
2. **Cross-validate**: If multiple reviewers flag the same issue, boost confidence by 10 (cap at 100).
3. **Filter**: Remove findings with confidence < 80 (configurable threshold).
4. **Sort**: Critical first, then Important, then Minor. Within severity, sort by confidence descending.

## Step 4: Output

Present the review as a structured report:

```
Code Review: PR #123 — "Add user profile endpoints"
=====================================================
Reviewers: 3 | Findings: 7 (3 filtered below threshold)

CRITICAL (1)
  [95%] src/api/users.ts:42 — Missing auth check on DELETE /users/:id
  Suggestion: Add requirePermission('users:delete') guard before handler

IMPORTANT (2)
  [88%] src/models/user.ts:15 — Password field included in toJSON() output
  Suggestion: Add explicit field exclusion or use a DTO

  [82%] src/api/users.ts:67 — Unbounded query without pagination
  Suggestion: Add limit/offset with defaults (limit=20, max=100)

MINOR (1)
  [80%] src/api/users.ts:3 — Import order doesn't match project convention
  Suggestion: Group external → internal → relative → types

Summary: 1 critical, 2 important, 1 minor (3 low-confidence filtered)
```

## Step 5: Post to PR (Optional)

Ask the user: "Post these findings as PR review comments?"

If yes:
- Use `gh pr review <number> --comment --body "<review summary>"` for the overall review
- For inline comments on specific files/lines, use `gh api` to post review comments

If no:
- The review report is the final output

## Confidence Scoring

| Score | Meaning | Action |
|-------|---------|--------|
| 90-100 | Near certain | Always surface |
| 80-89 | High confidence | Surface by default |
| 60-79 | Moderate | Filtered out (use `--threshold 60` to include) |
| < 60 | Speculative | Never surface |

Confidence boosters:
- Multiple reviewers flag same issue: +10
- Issue matches a known anti-pattern from `references/standards/code-review.md`: +5
- Issue is in a critical path (auth, payments, data integrity): +5

## Gotchas

- Large PRs (>500 lines) degrade review quality — recommend splitting before reviewing. Reviewers lose track of cross-file interactions in large diffs.
- Confidence scores below 70% should be flagged as "needs human verification" — don't auto-post low-confidence findings as definitive issues.
- Security findings should never be posted as public PR comments — use private channels or draft comments to avoid disclosing vulnerabilities in the open.
- The 3-reviewer pattern consumes significant tokens — for small PRs (<100 lines), a single reviewer pass is sufficient. Only use full 3-reviewer mode for substantial changes.
- Review diff context is limited — if a finding references code outside the diff, verify it exists before reporting. Stale references cause false positives.

## Data Logging

After completing a review, persist metadata for trend tracking:

```bash
DATA_DIR="${CLAUDE_PLUGIN_DATA:-${HOME}/.pixl/plugin-data}/code-review"
mkdir -p "$DATA_DIR"
cat >> "$DATA_DIR/review-history.jsonl" <<EOF
{"date":"$(date -u +%Y-%m-%dT%H:%M:%SZ)","pr":"$(gh pr view --json number -q .number 2>/dev/null || echo 'unknown')","findings_high":0,"findings_medium":0,"findings_low":0,"confidence_avg":0}
EOF
```

Replace the `0` values with actual counts. Run `cat $DATA_DIR/review-history.jsonl | jq -s` to view trends.

## Related Skills

- **`/self-review-fix-loop`** — Review AND fix. Pair with `/code-review` → `/self-review-fix-loop` for a find-then-fix workflow.
- **`/cto-review`** — Architectural critique of the full branch (not just the diff).
- **`/pr-creation`** — Create the PR first, then run `/code-review` on it.

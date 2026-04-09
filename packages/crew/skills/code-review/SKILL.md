---
name: code-review
description: "Multi-agent PR review with confidence scoring and AUTO-FIX/ASK classification. Quick mode (3 reviewers) or full mode (8 specialists including red team). Use when reviewing a PR, auditing changes before merge, or running automated review on a branch."
allowed-tools: Read, Bash, Glob, Grep, Agent
argument-hint: "[PR number or branch name] [--full | --quick] [--post] [--auto-fix]"
---

## Setup

Read `config.json` in this skill directory (if it exists):
- `confidence_threshold` — minimum confidence to include a finding; default 70
- `post_comments` — auto-post findings as PR comments; default false
- `reviewers` — review dimensions to run; default ["correctness", "security", "conventions"]
- `auto_fix` — automatically apply low-risk fixes; default false
- `review_mode` — "quick" (3 core reviewers) or "full" (8 specialists); default "quick"

If `post_comments` is false (default), output findings as a report only — do not call `gh pr review`.
Argument-level flags override config defaults (e.g. `--post` forces comment posting, `--full` forces 8 reviewers, `--auto-fix` enables fix-first mode).

## Overview

Structured multi-agent code review for pull requests. Up to 8 parallel specialist reviewers analyze the diff through specialized lenses, findings are deduplicated, scored for confidence, and classified as AUTO-FIX (safe to apply immediately) or ASK (requires user decision).

**Review modes**:
- **Quick** (default, `--quick`): 3 core reviewers (correctness, security, conventions) — for routine PRs <200 lines
- **Full** (`--full`): 8 specialist reviewers — for critical changes, large PRs, or changes touching auth/payments/data

**How this differs from other review skills**:
- `/self-review-fix-loop` — reviews AND fixes working tree changes. This skill is read-only (unless `--auto-fix`).
- `/cto-review` — architectural critique of the full branch state. This skill focuses on the PR diff.
- `/cross-review` — runs two different LLM models independently. This skill uses multiple specialist lenses on the same model.
- Tech-lead agent — general quality gate. This skill runs specialized parallel reviewers with confidence scoring.

## Step 1: Get the Diff

Determine the review target and extract the diff:

- **PR number provided**: `gh pr diff <number>` to get the diff, `gh pr view <number> --json title,body,baseRefName,headRefName` for context
- **Branch name provided**: `git diff main...<branch>` (or the appropriate base branch)
- **Nothing provided**: `git diff main...HEAD` for the current branch against main

Also gather:
- List of changed files: `gh pr diff <number> --name-only` or `git diff --name-only main...HEAD`
- PR description (if available) for intent context

## Step 2: Review (Parallel Agents)

Spawn reviewer agents (Explore type, read-only) in parallel. Each reviewer receives the full diff and the list of changed files.

**Quick mode** (default): Spawn reviewers A, B, C (3 agents).
**Full mode** (`--full`): Spawn all 8 reviewers A–H (8 agents).

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

### Reviewer D: Performance (full mode only)

Focus: runtime performance, database queries, bundle size impact.

Checklist:
- N+1 queries introduced or unresolved
- Missing database indexes for new WHERE/JOIN clauses
- Unnecessary computation in hot paths or loops
- Large objects copied instead of referenced
- Missing pagination on list endpoints
- Bundle size impact (new heavy dependencies, unshaken imports)
- Memory leaks (event listeners not cleaned up, subscriptions not unsubscribed)

### Reviewer E: API Contracts (full mode only)

Focus: API shape consistency, backwards compatibility, contract safety.

Checklist:
- Breaking changes to existing API response shapes
- Missing or inconsistent error response formats
- New endpoints that don't follow existing naming conventions
- Missing request validation (Zod/Pydantic schemas)
- Version compatibility (does this break existing clients?)
- Missing or inaccurate OpenAPI/type annotations

### Reviewer F: Data Migration Safety (full mode only)

Focus: database changes, migration safety, data integrity.

Checklist:
- Schema changes without corresponding migration
- Destructive migrations (column drops, type changes) without backfill
- Missing NOT NULL defaults on existing tables
- Foreign key changes that could orphan data
- Index changes that could cause lock contention on large tables
- Missing rollback strategy for the migration

### Reviewer G: Maintainability (full mode only)

Focus: code clarity, complexity, long-term maintenance cost.

Checklist:
- Cyclomatic complexity too high (deeply nested conditionals)
- Functions doing too many things (>50 lines, multiple responsibilities)
- Magic numbers or strings without named constants
- Tight coupling between modules that should be independent
- Missing abstractions that will force duplication later
- Dead code or commented-out code left behind

### Reviewer H: Red Team (full mode only)

Focus: adversarial review — try to break the code, find abuse vectors.

Checklist:
- What happens with malicious input? (SQL injection, XSS, path traversal)
- What happens under load? (race conditions, resource exhaustion, thundering herd)
- What happens with unexpected state? (null user, expired token, deleted resource)
- Can authorization be bypassed? (IDOR, privilege escalation, missing tenant isolation)
- Can rate limits be circumvented?
- What happens if an external dependency is down? (no timeout, no circuit breaker)

Each reviewer returns findings in this format:

```json
{
  "reviewer": "A|B|C|D|E|F|G|H",
  "findings": [
    {
      "file": "src/api/users.ts",
      "line": 42,
      "severity": "Critical|Important|Minor",
      "category": "correctness|security|convention|performance|api-contract|data-migration|maintainability|adversarial",
      "description": "Missing null check on user lookup result",
      "confidence": 95,
      "suggestion": "Add early return if user is null before accessing properties",
      "fix_class": "AUTO-FIX|ASK"
    }
  ]
}
```

### Fix Classification (fix_class)

Each finding must be classified:

| Class | Criteria | Examples |
|-------|----------|----------|
| **AUTO-FIX** | Low risk, mechanical, no design decisions | Unused imports, missing types, formatting, consistent error shapes, missing `await` |
| **ASK** | Requires judgment, architectural impact, multiple valid approaches | API design changes, new abstractions, security model decisions, performance trade-offs |

Default to **ASK** when uncertain. Only classify as AUTO-FIX when the fix is unambiguous and low-risk.

## Step 3: Consolidate

Merge all findings and deduplicate:

1. **Deduplicate**: Same file + same line + similar description = one finding. Keep the highest confidence score.
2. **Cross-validate**: If multiple reviewers flag the same issue, boost confidence by 10 (cap at 100).
3. **Filter**: Remove findings with confidence < threshold (default 70, configurable).
4. **Sort**: Critical first, then Important, then Minor. Within severity, sort by confidence descending.
5. **Classify**: Group findings into AUTO-FIX and ASK buckets.

## Step 4: Auto-Fix (if enabled)

If `--auto-fix` flag is set or `auto_fix: true` in config:

1. Collect all AUTO-FIX findings
2. Apply each fix (edit the file directly)
3. Re-run relevant checks (lint, typecheck) to verify fixes don't break anything
4. Report what was auto-fixed

If auto-fix is NOT enabled, present AUTO-FIX findings as suggestions with a note: "These can be auto-applied with `--auto-fix`."

## Step 5: Output

Present the review as a structured report:

```
Code Review: PR #123 — "Add user profile endpoints"
=====================================================
Reviewers: 8 (full mode) | Findings: 12 (4 filtered below threshold)

AUTO-FIX (applied automatically):
  [92%] src/api/users.ts:3 — Import order doesn't match project convention → FIXED
  [88%] src/models/user.ts:45 — Missing `await` on async call → FIXED

CRITICAL — ASK (1)
  [95%] src/api/users.ts:42 — Missing auth check on DELETE /users/:id
  Reviewer: B (Security), H (Red Team) — consensus
  Suggestion: Add requirePermission('users:delete') guard before handler

IMPORTANT — ASK (3)
  [88%] src/models/user.ts:15 — Password field included in toJSON() output
  Reviewer: B (Security)
  Suggestion: Add explicit field exclusion or use a DTO

  [85%] src/api/users.ts:67 — Unbounded query without pagination
  Reviewer: D (Performance)
  Suggestion: Add limit/offset with defaults (limit=20, max=100)

  [82%] prisma/migrations/0043.sql:12 — Adding NOT NULL without default to populated table
  Reviewer: F (Data Migration)
  Suggestion: Add DEFAULT value or use expand-migrate-contract pattern

MINOR — ASK (2)
  [80%] src/api/users.ts:30 — Function exceeds 50 lines — consider extracting
  Reviewer: G (Maintainability)

  [78%] src/api/users.ts:90 — No timeout on external API call
  Reviewer: H (Red Team)

Summary: 2 auto-fixed, 1 critical, 3 important, 2 minor (4 filtered)
```

## Step 6: Post to PR (Optional)

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
| 60-79 | Moderate | Filtered by default (use `--threshold 60` to include) |
| 40-59 | Low confidence | Suppress to appendix. Only flag if P0-severity (security, data loss) |
| 1-39 | Speculative | Never surface unless explicitly asked |

See `references/standards/code-review.md` for the full confidence scoring standard including boosters and penalties.

Confidence boosters:
- Multiple reviewers flag same issue: +10
- Issue matches a known anti-pattern from `references/standards/code-review.md`: +5
- Issue is in a critical path (auth, payments, data integrity): +5

## Gotchas

- Large PRs (>500 lines) degrade review quality — recommend splitting before reviewing. Reviewers lose track of cross-file interactions in large diffs.
- Confidence scores below 70% should be flagged as "needs human verification" — don't auto-post low-confidence findings as definitive issues.
- Security findings should never be posted as public PR comments — use private channels or draft comments to avoid disclosing vulnerabilities in the open.
- **Quick mode** (3 reviewers) is sufficient for most PRs. Only use **full mode** (8 reviewers) for critical changes or PRs >200 lines. The 8-reviewer pattern consumes significant tokens.
- For small PRs (<50 lines), even quick mode may be overkill — a single review pass is sufficient.
- Review diff context is limited — if a finding references code outside the diff, verify it exists before reporting. Stale references cause false positives.
- AUTO-FIX findings should still be reviewed in the report — auto-fix reduces friction but doesn't replace oversight.
- Data migration reviewer (F) requires schema/migration files in the diff — skip if no database changes are present.

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
- **`/cross-review`** — Multi-model review (Claude + secondary model) for higher-confidence validation on critical changes.
- **`/pr-creation`** — Create the PR first, then run `/code-review` on it.
- **`/deploy-verify`** — Post-merge verification. Run after the PR is merged and deployed.

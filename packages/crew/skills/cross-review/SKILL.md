---
name: cross-review
description: "Multi-tier code review: runs two Claude model tiers (Sonnet + Haiku) independently on the same diff, produces a consensus table, and flags disagreements. Use when you want a second opinion, cross-model validation, or higher-confidence review on critical changes."
allowed-tools: Read, Bash, Glob, Grep, Agent
argument-hint: "[PR number or branch name]"
---

## Overview

Independent review by two different Claude model tiers on the same diff. Produces a consensus table highlighting agreements, disagreements, and "taste decisions" where models diverge on subjective issues. Uses Sonnet (primary) + Haiku (secondary) by default — different model tiers catch different things due to reasoning depth differences.

**How this differs from other review skills**:
- `/code-review` — single-model, multi-reviewer (same model, different lenses). This skill uses different models for independent validation.
- `/cto-review` — architectural critique. This skill is diff-level review with cross-model consensus.

**Cost note**: This skill runs two full review passes. Reserve for critical changes (auth, payments, data integrity, public API contracts), not routine PRs.

## Step 1: Get the Diff

Same as `/code-review` Step 1:

- **PR number**: `gh pr diff <number>`, `gh pr view <number> --json title,body,baseRefName`
- **Branch name**: `git diff main...<branch>`
- **No argument**: `git diff main...HEAD`

Capture: full diff, list of changed files, PR description (if available).

## Step 2: Parallel Independent Review

Spawn **2 agents in parallel**, each with a different model. Both receive the identical diff and file list.

### Agent A: Primary Model (Claude — Sonnet)

```
Agent(
  subagent_type="Explore",
  model="sonnet",
  prompt="Review this code diff independently. For each finding, report: file, line, severity (Critical/Important/Minor), category (correctness/security/performance/convention), description, and confidence (1-100). Be thorough but only report findings you're confident about (>70%). Do not speculate.

  Diff:
  <full diff>

  Changed files: <file list>
  PR context: <description>

  Return findings as a JSON array."
)
```

### Agent B: Secondary Model (Haiku — fast, different perspective)

```
Agent(
  subagent_type="Explore",
  model="haiku",
  prompt="<same prompt as Agent A with identical diff>"
)
```

Both agents run independently with no knowledge of each other's findings.

## Step 3: Build Consensus Table

Compare findings from both models:

### Matching Algorithm

Two findings "match" if:
- Same file (exact match)
- Same line or within 5 lines of each other
- Same category or overlapping description keywords

### Classification

| Outcome | Criteria | Action |
|---------|----------|--------|
| **Consensus** | Both models flag the same issue | High confidence — always surface |
| **Primary Only** | Only Claude found it | Surface if confidence > 80 |
| **Secondary Only** | Only secondary found it | Surface if confidence > 80, flag as "second opinion" |
| **Disagreement** | Models contradict on severity or recommendation | Flag as "taste decision" — present both perspectives |

### Confidence Adjustment

- Consensus findings: boost confidence by +15 (cap 100)
- Single-model findings: keep original confidence
- Disagreements: show both confidence scores, let user decide

## Step 4: Output

```markdown
# Cross-Model Review: PR #123

## Models: Claude Sonnet + Claude Haiku
## Findings: 8 total (5 consensus, 2 primary-only, 1 disagreement)

### Consensus (Both Models Agree)
| # | File | Line | Severity | Issue | Confidence |
|---|------|------|----------|-------|------------|
| 1 | src/api/auth.ts | 42 | Critical | Missing rate limit on login endpoint | 98% |
| 2 | src/models/user.ts | 15 | Important | Password in toJSON output | 95% |
| 3 | src/api/users.ts | 67 | Important | Unbounded query without pagination | 90% |
| 4 | src/api/users.ts | 23 | Minor | Inconsistent error response shape | 85% |
| 5 | src/utils/hash.ts | 8 | Minor | bcrypt cost factor too low (8, recommend 12) | 82% |

### Primary Only (Claude Sonnet)
| # | File | Line | Severity | Issue | Confidence |
|---|------|------|----------|-------|------------|
| 6 | src/middleware/cors.ts | 12 | Important | Wildcard CORS origin in production | 88% |
| 7 | src/api/users.ts | 45 | Minor | Missing input sanitization on name field | 82% |

### Disagreements (Taste Decisions)
| # | File | Line | Claude Says | Haiku Says | Recommendation |
|---|------|------|-------------|------------|----------------|
| 8 | src/api/users.ts | 30 | Important: should use DTO pattern | Minor: current approach is fine | User decides — architectural preference |

## Verdict
- 1 Critical (consensus) — must fix before merge
- 3 Important (2 consensus, 1 primary) — should fix
- 3 Minor — nice to have
- 1 Taste decision — user call
```

## Gotchas

- This skill costs ~2x tokens of a normal review — reserve for critical paths
- Model availability: if OpenAI/Gemini keys aren't configured, fall back to Claude Opus + Claude Haiku (still valuable — different model tiers catch different things)
- Disagreements are often about style/architecture, not correctness — present both, don't auto-resolve
- Large diffs (>500 lines) should be split before cross-review — both models degrade on large inputs
- Don't use this for trivial PRs (<50 lines) — single-model `/code-review` is sufficient

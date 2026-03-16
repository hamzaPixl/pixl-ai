---
name: self-review-fix-loop
description: "Multi-agent self-review and remediation workflow for open changes/features. Use when asked to self-review, critique, find gaps/issues, improve quality, or run review-and-fix loops. Spawns reviewer agents in parallel, consolidates findings, then spawns fixer agents in parallel. Iterates until no meaningful gaps remain (max 10 iterations)."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
argument-hint: "<scope: git diff, feature name, or file list>"
context: fork
---

## Overview

This skill runs an iterative review-and-fix loop over code changes. Each iteration has two waves of parallel agents: **3 reviewers** that find issues, then **3 fixers** that resolve them. The coordinator consolidates findings between waves and partitions work across fixers to avoid conflicts.

The loop continues until reviewers find no meaningful issues or the iteration cap (10) is reached.

**Why self-review works**: Automated self-review catches 80%+ of issues before human review because it applies multiple specialized lenses (correctness, security, maintainability) in parallel — something a single reviewer rarely does consistently. This reduces review cycles and unblocks PRs faster.

## Step 1: Scope

Determine the review scope:

- If there is a `git diff` (staged + unstaged), that is the default scope
- Otherwise, use the provided feature scope or file list
- Identify the changed files, their purpose, and the intent of the changes

## Step 2: Review (Parallel — 3 Agents)

Spawn **3 reviewer agents** (Explore type, read-only) in parallel:

- **Reviewer A**: Requirement coverage and behavioral correctness
- **Reviewer B**: Regressions, edge cases, error handling, security/privacy, performance
- **Reviewer C**: Tests, maintainability, instruction/policy compliance

Each reviewer returns findings with severity (P0-P3), evidence, and fix direction.

## Step 3: Consolidate

The coordinator merges, deduplicates, and normalizes severity across all reviewer outputs:

1. Merge findings from all reviewers
2. Deduplicate (same file + same issue = one finding)
3. Normalize severity across reviewers
4. Produce a single prioritized backlog
5. **If the backlog is empty, the loop ends**

### Findings Packet Format

Write consolidated findings to `.context/review-findings.json` using the context packet standard (see `references/orchestration/context-packet.md`):

```json
{
  "type": "review",
  "version": "1.0",
  "metadata": {
    "skill": "self-review-fix-loop",
    "project": "PROJECT",
    "created_at": "TIMESTAMP"
  },
  "payload": {
    "findings": [
      {
        "severity": "P0",
        "file": "src/api/users.ts",
        "description": "Missing auth check on DELETE endpoint",
        "fix_direction": "Add requirePermission guard before handler",
        "evidence": "Line 42: router.delete('/users/:id', handler) has no guard"
      }
    ]
  }
}
```

## Step 4: Fix (Parallel — 3 Agents)

Read the consolidated findings from `.context/review-findings.json`. Partition the backlog into **3 non-overlapping packets** by file ownership. Spawn **3 fixer agents** (general-purpose) in parallel. Each fixer:

1. Implements fixes only within its assigned file scope
2. Runs relevant tests after each fix
3. Reports results (fixed, skipped, blocked)

## Step 5: Verify

Archive the findings to `.context/review-findings-final.json` for audit trail.

Integrate fixer outcomes, resolve conflicts, and run final verification:

- Run full test suite
- Run typecheck and linter
- If verification fails, create new P0/P1 findings and continue the loop
- If all passes, the loop ends

## Iteration Control

| Parameter          | Default | Description                                            |
| ------------------ | ------- | ------------------------------------------------------ |
| `max_iterations`   | 10      | Hard cap on review-fix cycles                          |
| `stop_at_severity` | P2      | Stop when no findings at this severity or above remain |

## Severity Levels

| Level | Meaning                              | Action                             |
| ----- | ------------------------------------ | ---------------------------------- |
| P0    | Blocking correctness or safety issue | Always fix                         |
| P1    | High-impact bug or regression risk   | Always fix                         |
| P2    | Moderate issue                       | Fix unless explicitly out of scope |
| P3    | Low-impact polish                    | Fix when low-cost and safe         |

## Related Skills

- **`/cto-review`** — Run after the review-fix loop stabilizes to get an architectural assessment of remaining complexity
- **`/cartographer`** — Run on the final diff to decompose changes into semantic feature clusters for PR review

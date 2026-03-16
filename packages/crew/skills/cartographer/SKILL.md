---
name: cartographer
description: "Analyze a pull request diff and group changes into semantic feature clusters. Use when breaking down a PR into reviewable components, quantifying churn, or explaining change boundaries."
allowed-tools: Read, Bash, Glob, Grep, Write, Agent
argument-hint: "<target-branch: e.g. main>"
context: fork
---

# Cartographer

## Overview

Produce an intent-first decomposition of a PR plus local working tree changes. Treat "major features" as behaviorally coherent change components, not just folders or file types, and explain why each component exists, how it is implemented, and what it changes.

Always include:

- Committed branch diff churn.
- Uncommitted local churn (staged, unstaged, and untracked files).
- A persisted markdown report written to `CARTOGRAPH.MD` at the repository root.

## Workflow

### Step 1: Establish Analysis Scope

Resolve the base/head context first and use merge-base as the committed diff base.

```bash
TARGET_BRANCH="${1:-main}"
HEAD_REF=HEAD
BASE_REF=$(git merge-base "$TARGET_BRANCH" "$HEAD_REF")
```

**Hitchhiker commit detection (CRITICAL)**: Before proceeding, check whether the branch contains commits from other PRs that were separately merged to the target branch.

```bash
ALL_COMMITS=$(git log --oneline "$TARGET_BRANCH..HEAD" | wc -l)
BRANCH_NAME=$(git branch --show-current)
PR_SHAS=$(gh pr list --head "$BRANCH_NAME" --json commits --jq '.[0].commits[].oid' 2>/dev/null)
PR_COMMIT_COUNT=$(echo "$PR_SHAS" | grep -c . 2>/dev/null || echo 0)

if [ -n "$PR_SHAS" ] && [ "$PR_COMMIT_COUNT" -lt "$ALL_COMMITS" ]; then
  echo "HITCHHIKER COMMITS DETECTED: $ALL_COMMITS on branch, $PR_COMMIT_COUNT in PR"
  PR_FILES=$(for sha in $PR_SHAS; do git diff-tree --no-commit-id --name-only -r "$sha"; done | sort -u)
fi
```

When hitchhiker commits are detected, scope the diff to PR files only. Otherwise use full `BASE_REF..HEAD_REF`.

Pull full file-level and hunk-level data:

```bash
# Committed branch range
git diff --numstat "$BASE_REF..$HEAD_REF"
git diff --name-status "$BASE_REF..$HEAD_REF"
git diff "$BASE_REF..$HEAD_REF"

# Local changes
git diff --numstat --cached
git diff --numstat
git diff --cached
git diff

# Untracked files
git ls-files --others --exclude-standard
```

Build one combined churn dataset: committed + staged + unstaged + untracked.

### Step 2: Infer Intent and Implementation Signals

Map each changed area to probable intent using:

- Domain language in identifiers and comments
- Implementation shape (algorithms, data flow, control-flow changes)
- Data model/schema changes
- Test additions/updates that reveal expected behavior
- Migration or config updates indicating rollout/infrastructure intent

Separate mechanical churn (renames, formatting, generated files) from behavioral churn.

### Step 3: Build Feature Clusters

- Start from behavior themes, then attach files/hunks
- Split a single file across multiple features when hunks represent different intents
- Merge clusters only when they ship one coherent behavior/outcome
- Keep explicitly cross-cutting work separate unless tightly bound to one feature

### Step 4: Quantify Churn Per Cluster

- Compute per-feature churn from combined `--numstat` totals
- If a file is split across features, estimate hunk-level allocation and state assumption
- Ensure: Sum(feature totals) + sum(cross-cutting/unassigned) = total combined churn

### Step 5: Explain Each Major Feature

For each component, provide:

- **Motivation**: Why this component exists
- **Implementation**: How the change works technically
- **Impact**: What behavior, architecture, or user flow changes

Cite concrete evidence from the diff, not speculation.

### Step 6: Declare Boundaries and Dependencies

- Define in-scope vs out-of-scope for each feature cluster
- Identify dependencies between features and sequencing risk

### Step 7: Persist Output

Write the full final analysis to `CARTOGRAPH.MD` in the repository root.

## Grouping Rules

- Group by intent over file location
- Prefer fewer major components (typically 2-7)
- Avoid collapsing unrelated refactors into feature work
- Keep a dedicated bucket for "supporting/enablement" changes
- Mark uncertain mappings explicitly

## Output Contract

Always return the following structure:

### 1. PR Summary

One paragraph explaining the high-level intent.

### 2. Churn Totals

- `Total additions`, `Total deletions`, `Total changed lines`
- `Files changed` count
- `Scope`: state whether totals include uncommitted local changes

### 3. Major Feature Components

For each:

- Component name
- Intent boundary
- Line count: additions, deletions, total
- Motivation
- Implementation
- Impact

### 4. Cross-Cutting or Non-Feature Churn

- Refactors, renames, formatting, generated files, test harness work
- Include line counts and rationale

### 5. Dependency Map

- Component-to-component dependencies and coupling risk

### 6. Ambiguities and Assumptions

- Uncertain mappings and line-count allocation assumptions

### 7. Verification Check

- `Component totals + cross-cutting + unassigned = combined total`
- Status: balanced | not balanced

### 8. Artifact

- Confirm `CARTOGRAPH.MD` was written

## Quality Bar

- Use evidence from actual diff content, not path-name guesswork
- Explain motivation, implementation, and impact for every major component
- Include line counts for every component and every non-feature bucket
- Preserve uncertainty explicitly when intent is mixed or unclear

## Related Skills

- **`/self-review-fix-loop`** — Run before cartography to fix quality issues, producing a cleaner diff to decompose
- **`/cto-review`** — Run on the same branch for an architectural simplification plan that complements the cartograph's feature decomposition

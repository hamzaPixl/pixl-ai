---
name: retro
description: "Engineering retrospective from git history: commit analysis, code churn, shipping velocity, hotspot detection, and per-contributor breakdown. Time-windowed (24h/7d/14d/30d). Use when asked for a retro, sprint review, work summary, or shipping metrics."
allowed-tools: Read, Bash, Glob, Grep
argument-hint: "[7d | 24h | 14d | 30d | compare]"
---

## Overview

Analyzes git history and project data to produce a structured engineering retrospective. Focuses on what shipped, code quality trends, hotspots, and shipping velocity.

## Step 1: Determine Time Window

Parse the argument for the time window:

| Argument | Window | `git log --since` |
|----------|--------|--------------------|
| `24h` | Last 24 hours | `--since="24 hours ago"` |
| `7d` (default) | Last 7 days | `--since="7 days ago"` |
| `14d` | Last 14 days | `--since="14 days ago"` |
| `30d` | Last 30 days | `--since="30 days ago"` |
| `compare` | Compare current vs previous period | Two `git log` ranges |

## Step 2: Gather Data

Run these commands in parallel:

### Commit Analysis
```bash
# Commit count and authors
git log --since="7 days ago" --oneline | wc -l
git log --since="7 days ago" --format="%an" | sort | uniq -c | sort -rn

# Commit types (conventional commits — macOS-compatible)
git log --since="7 days ago" --oneline | sed -E 's/^[a-f0-9]+ //' | grep -oE '^(feat|fix|refactor|chore|docs|test|perf|ci|style)' | sort | uniq -c | sort -rn

# Files changed
git log --since="7 days ago" --name-only --format="" | sort | uniq -c | sort -rn | head -20
```

### Code Churn
```bash
# Lines added/removed
git log --since="7 days ago" --numstat --format="" | awk '{add+=$1; del+=$2} END {print "+"add, "-"del}'

# Churn by directory
git log --since="7 days ago" --numstat --format="" | awk '{split($3,a,"/"); dir=a[1]"/"a[2]; add[dir]+=$1; del[dir]+=$2} END {for(d in add) print add[d]+del[d], d}' | sort -rn | head -10
```

### Hotspots (High Churn Files)
```bash
# Files changed most frequently (potential complexity hotspots)
git log --since="7 days ago" --name-only --format="" | sort | uniq -c | sort -rn | head -10
```

### PR Activity (if GitHub)
```bash
# Merged PRs
gh pr list --state merged --search "merged:>=$(date -v-7d +%Y-%m-%d 2>/dev/null || date -d '7 days ago' +%Y-%m-%d)" --json number,title,author,mergedAt --limit 50

# Open PRs
gh pr list --state open --json number,title,author,createdAt --limit 20
```

### Cost Data (if pixl available)
```bash
pixl cost summary --since "7 days ago" --json 2>/dev/null
```

## Step 3: Analyze

### Shipping Velocity
- Commits per day (average)
- PRs merged per day
- Commit type distribution (feat vs fix vs chore tells the story — heavy on fixes = tech debt, heavy on feat = shipping, heavy on chore = maintenance mode)

### Code Hotspots
- Files changed >3 times in the window are hotspots
- Hotspots with high churn (added+deleted >100 lines) are complexity risks
- Flag files that are both hotspots AND have no test coverage

### Contributor Breakdown
For each contributor:
- Commit count and type distribution
- Primary areas worked on (top 3 directories)
- Lines added vs removed (net positive = building, net negative = cleaning)

### Quality Signals
- Ratio of `fix:` to `feat:` commits (>1:1 suggests quality debt)
- Presence of `revert:` commits (instability signal)
- Test commits as % of total (healthy: >15%)

## Step 4: Output Report

```markdown
# Engineering Retrospective: Apr 2-9, 2026

## Summary
- **Commits**: 47 (6.7/day)
- **PRs Merged**: 8
- **Lines**: +2,340 / -890 (net +1,450)
- **Contributors**: 3

## What Shipped
- feat: User profile endpoints (#42, #45)
- feat: Webhook retry logic (#48)
- fix: Race condition in session manager (#43)
- refactor: Billing module to DDD (#44, #46, #47)

## Commit Distribution
  feat:     ████████████ 38%
  fix:      ██████ 19%
  refactor: ████████ 26%
  chore:    ████ 13%
  test:     ██ 6%

## Hotspots (High Churn)
1. src/api/billing.ts — 8 changes, +340/-120 lines
2. src/models/user.ts — 5 changes, +90/-45 lines
3. prisma/schema.prisma — 4 changes

## Contributors
| Author | Commits | Focus Areas | Net Lines |
|--------|---------|-------------|-----------|
| Alice | 22 | billing/, api/ | +1,200 |
| Bob | 18 | models/, tests/ | +180 |
| Carol | 7 | infra/, ci/ | +70 |

## Quality Signals
- Fix:Feat ratio: 0.5:1 (healthy — more building than fixing)
- Test coverage: 6% of commits (⚠ below 15% target)
- No reverts this period

## Observations
- Billing module is a hotspot — 8 changes suggest active refactoring or instability
- Test commit percentage is low — consider pairing features with tests
- Strong shipping velocity at 6.7 commits/day
```

## Compare Mode

When `compare` is passed, run two periods and diff:

```
Current (Apr 2-9):  47 commits, 8 PRs, +2340/-890
Previous (Mar 26-1): 32 commits, 5 PRs, +1800/-600

Δ Commits: +47% ↑
Δ PRs: +60% ↑
Δ Net Lines: +52% ↑
Δ Fix:Feat: 0.5:1 → 0.3:1 (improving)
```

## Gotchas

- Shallow clones (`--depth 1`) have no history — check `git log --oneline | wc -l` first
- Monorepos: scope to a package directory if the retro should focus on one service
- `gh` commands require GitHub authentication — degrade gracefully to git-only analysis
- AI-assisted commits may inflate per-contributor lines — note this in the report
- Merge commits can double-count changes — use `--no-merges` flag

---
name: code-reduction
description: "Dead code elimination, dependency cleanup, deduplication, and consolidation. Two modes: (1) Quick scan — runs knip/depcheck/vulture for fast tool-driven analysis, (2) Deep analysis — parallel Explore agents for structural redundancy and gap detection. Use when asked to reduce codebase size, find unused code, clean up dead code, audit dependencies, eliminate redundancy, or consolidate duplicate implementations."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
argument-hint: "<scope: directory, module, or feature area> [mode: quick|deep|all]"
---

## Overview

Systematic code reduction: discovers redundancy, removes dead code, identifies duplicates, finds gaps, and consolidates. Two modes available:

- **Quick scan** (default for targeted cleanup) — runs knip, depcheck, or vulture for fast tool-driven dead code detection
- **Deep analysis** (default for broad scope) — spawns parallel Explore agents for structural analysis, deduplication, and gap detection
- **All** — runs quick scan first, then escalates to deep analysis for anything the tools missed

## Required References

Before starting, read `references/methodology/refactor-planning.md` for safe refactoring strategies and dependency analysis patterns.

## Step 0: Quick Scan (Tool-Driven)

Detect project type and run the appropriate static analysis tools:

| Signal | Tools available |
|---|---|
| `package.json` with TypeScript | knip, ts-prune, depcheck |
| `package.json` without TypeScript | depcheck |
| `pyproject.toml` | vulture, pip-extra-reqs |
| `go.mod` | `go vet`, `staticcheck` |

```bash
# TypeScript/Node.js — knip is the best all-in-one tool
npx knip --reporter compact    # Finds unused files, exports, deps, types

# Fallbacks if knip is not available:
npx depcheck                   # Unused deps only

# Python
pip install vulture && vulture src/

# Go
go vet ./...
staticcheck ./...
```

### Triage quick scan results

| Category | Action |
|---|---|
| **Truly unused** — no references anywhere | Delete |
| **Dynamically used** — referenced via string, reflection, or config | Keep, add to knip ignore |
| **Test-only export** — only used in tests | Keep (but check if test is dead too) |
| **Plugin/framework magic** — used by framework convention | Keep, add to knip ignore |

If mode is `quick`, apply deletions (Step 4) and report (Step 5). If mode is `deep` or `all`, continue to Step 1.

## Step 1: Discovery (Parallel — 3 Agents)

Spawn 3 Explore agents to scan in parallel:

1. **Agent A**: Map exports, imports, and dependency graph
2. **Agent B**: Identify code patterns and potential duplicates
3. **Agent C**: Catalog test coverage and unused test helpers

## Step 2: Dead Code Detection

Analyze the dependency graph to find:

1. Unused exports (exported but never imported)
2. Unreachable branches (conditions that are always true/false)
3. Unused variables and parameters
4. Orphaned files (not imported by anything)
5. Commented-out code blocks

> **Tooling:** Consider using `ts-prune` (`npx ts-prune`) to detect unused TypeScript exports automatically.

## Step 3: Duplicate Detection

Find code that appears in multiple places:

1. Exact duplicates (copy-paste)
2. Near-duplicates (same structure, different names)
3. Pattern duplicates (same logic, different data types)
4. Suggest consolidation into shared utilities

## Step 4: Gap Analysis

Identify what's missing:

1. Missing tests for critical paths
2. Missing error handling
3. Inconsistent patterns (some modules follow a pattern, others don't)
4. Missing type definitions

## Step 5: Remediate

Apply fixes with safety:

1. Remove confirmed dead code
2. Extract duplicates into shared utilities
3. Run tests after each change to ensure no regressions
4. Report remaining items that need manual review

## Step 6: Verify

```bash
# TypeScript
npx tsc --noEmit               # Still compiles
npm test                        # Tests still pass

# Python
python -m pytest tests/         # Tests still pass

# Re-run analysis to confirm reduction
npx knip                        # Count decreased
```

## Step 7: Report

```markdown
## Cleanup Summary
- Dead files removed: N
- Dead exports removed: N
- Unused deps removed: N (saved ~X MB)
- Dead code lines removed: N
- Duplicates consolidated: N
- Remaining items (kept with justification): N
```

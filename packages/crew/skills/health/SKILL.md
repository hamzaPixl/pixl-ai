---
name: health
description: "Code quality dashboard: discovers project toolchain, runs checks (types, lint, tests, dead code), computes a composite 0-10 score, and tracks trends across runs. Use when asked to check project health, code quality, run a health check, or see quality trends."
allowed-tools: Read, Bash, Glob, Grep, Write
argument-hint: "[--trend | --fix | --ci]"
---

## Overview

Unified code quality dashboard that wraps existing toolchain into a composite 0-10 score with trend tracking. Replaces ad-hoc "run lint, run tests, run typecheck" with a single command that scores and tracks over time.

**How this differs from other skills**:
- `/test-runner` — runs tests only. This skill scores the full quality picture.
- `/code-review` — reviews a PR diff. This skill audits the whole project state.
- `/cto-review` — architectural critique. This skill is a quantitative health metric.

## Step 1: Discover Toolchain

Detect available quality tools by checking config files:

| Tool | Detection | Category |
|------|-----------|----------|
| **TypeScript** | `tsconfig.json` | Type safety |
| **Pyright/mypy** | `pyrightconfig.json`, `mypy.ini`, `pyproject.toml [tool.pyright]` | Type safety |
| **ESLint** | `.eslintrc*`, `eslint.config.*` | Lint |
| **Biome** | `biome.json` | Lint + format |
| **Ruff** | `ruff.toml`, `pyproject.toml [tool.ruff]` | Lint |
| **pytest** | `pytest.ini`, `pyproject.toml [tool.pytest]` | Tests |
| **vitest/jest** | `vitest.config.*`, `jest.config.*` | Tests |
| **knip** | `knip.json`, `knip.ts` | Dead code |
| **vulture** | `pyproject.toml [tool.vulture]` | Dead code (Python) |
| **shellcheck** | `*.sh` files present | Shell quality |

Report which tools were found and which are missing.

## Step 2: Run Checks

Run each discovered tool and capture pass/fail + metrics. Use `--quiet` flags and suppress success output.

### Type Safety (weight: 30%)

```bash
# TypeScript
npx tsc --noEmit 2>&1 | tail -5
# Count errors
npx tsc --noEmit 2>&1 | grep -c "error TS" || echo 0

# Python
pyright --outputjson 2>/dev/null | jq '.generalDiagnostics | length' || echo "pyright not available"
```

Score: `10 - min(10, error_count * 0.5)` (0 errors = 10, 20+ errors = 0)

### Lint (weight: 25%)

```bash
# ESLint
npx eslint . --format json 2>/dev/null | jq '[.[].errorCount] | add // 0'

# Biome
npx biome check . --reporter=json 2>/dev/null | jq '.diagnostics | length'

# Ruff
ruff check . --output-format json 2>/dev/null | jq 'length'
```

Score: `10 - min(10, error_count * 0.3)` (0 errors = 10, 33+ errors = 0)

### Tests (weight: 30%)

```bash
# pytest
uv run python -m pytest --tb=no -q 2>&1 | tail -1
# Parse "X passed, Y failed"

# vitest
npx vitest run --reporter=json 2>/dev/null | jq '{passed: .numPassedTests, failed: .numFailedTests}'
```

Score: `10 * (passed / total)` — all pass = 10, any fail reduces proportionally

### Dead Code (weight: 15%)

```bash
# knip
npx knip --reporter json 2>/dev/null | jq '{unused_files: .files | length, unused_exports: .exports | length}'

# vulture
vulture . --min-confidence 80 2>/dev/null | wc -l
```

Score: `10 - min(10, (unused_files + unused_exports) * 0.2)` — clean = 10, 50+ issues = 0

### Shell Quality (bonus, no weight — advisory only)

```bash
shellcheck scripts/*.sh 2>/dev/null | grep -c "error" || echo 0
```

## Step 3: Compute Score

Calculate weighted composite score:

```
HEALTH = (type_score * 0.30) + (lint_score * 0.25) + (test_score * 0.30) + (dead_code_score * 0.15)
```

Round to one decimal place.

### Score Interpretation

| Score | Grade | Meaning |
|-------|-------|---------|
| 9.0-10.0 | A | Excellent — ship with confidence |
| 7.0-8.9 | B | Good — minor issues, safe to ship |
| 5.0-6.9 | C | Fair — address before major releases |
| 3.0-4.9 | D | Poor — significant quality debt |
| 0.0-2.9 | F | Critical — stop and fix before continuing |

## Step 4: Output Report

```
Health Check: <project-name>
==============================
Date: <today's date>
Score: 7.8/10 (B)

  Type Safety:  8.5/10  (3 errors)      [████████░░] 30%
  Lint:         9.0/10  (2 warnings)     [█████████░] 25%
  Tests:        6.7/10  (4/12 failing)   [██████░░░░] 30%
  Dead Code:    7.0/10  (15 unused)      [███████░░░] 15%

Top Issues:
  1. [Tests] 4 failing tests in src/api/ — run /test-runner to diagnose
  2. [Types] 3 type errors in src/models/ — missing null checks
  3. [Dead Code] 15 unused exports — run /code-reduction to clean up

Trend: ↑ 0.3 from last run (7.5 → 7.8)
```

## Step 5: Persist History

Store the score for trend tracking:

Replace all placeholder values below with actual computed scores from Steps 2-3:

```bash
DATA_DIR="${CLAUDE_PLUGIN_DATA:-${HOME}/.pixl/plugin-data}/health"
mkdir -p "$DATA_DIR"
# Substitute actual values for SCORE, TYPE_SCORE, LINT_SCORE, TEST_SCORE, DEAD_SCORE, and detail counts
cat >> "$DATA_DIR/health-history.jsonl" <<EOF
{"date":"$(date -u +%Y-%m-%dT%H:%M:%SZ)","score":${SCORE},"type_safety":${TYPE_SCORE},"lint":${LINT_SCORE},"tests":${TEST_SCORE},"dead_code":${DEAD_SCORE},"details":{"type_errors":${TYPE_ERRORS},"lint_errors":${LINT_ERRORS},"test_pass":${TEST_PASS},"test_fail":${TEST_FAIL},"unused_exports":${UNUSED_EXPORTS}}}
EOF
```

## Modes

### `--trend`

Show score history and trend chart:

```bash
DATA_DIR="${CLAUDE_PLUGIN_DATA:-${HOME}/.pixl/plugin-data}/health"
cat "$DATA_DIR/health-history.jsonl" | jq -s 'sort_by(.date) | .[-10:]'
```

Display as ASCII trend line.

### `--fix`

After computing score, auto-fix what's possible:
- Run `eslint --fix` or `biome check --apply`
- Run `ruff check --fix`
- Remove unused imports flagged by knip/vulture
- Re-score after fixes to show improvement

### `--ci`

Output machine-readable JSON for CI integration:

```json
{"score": 7.8, "grade": "B", "pass": true, "threshold": 6.0}
```

Exit with code 1 if score < threshold (default 6.0).

## Gotchas

- First run has no trend data — establish baseline silently
- Large monorepos: scope to a specific package with argument (e.g., `/health packages/api`)
- Tools that aren't installed score as N/A and their weight redistributes to others
- Test score can be misleading if test suite is tiny — flag if <10 tests exist
- `--fix` mode may introduce changes — review diff before committing

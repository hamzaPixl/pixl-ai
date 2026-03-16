---
name: test-runner
description: "Smart test runner for Python and TypeScript codebases. Discovers test tiers (smoke/unit/integration/e2e), runs targeted subsets with timeouts, and avoids session hangs. Use when asked to run tests, fix failing tests, or set up test infrastructure. Supports pytest, vitest, and jest."
allowed-tools: Read, Bash, Glob, Grep, Edit, Write, Agent
argument-hint: "<scope: smoke|unit|fast|full|file-path>"
---

# Test Runner

Smart, tiered test runner for Python and TypeScript codebases. Never runs all tests blindly — discovers, categorizes, then runs targeted subsets.

## Step 0: Detect Language

Determine the project language and test framework:

| Signal                                                             | Framework  | Runner command                        |
| ------------------------------------------------------------------ | ---------- | ------------------------------------- |
| `pyproject.toml`, `pytest.ini`, `setup.cfg` with pytest config     | **pytest** | `uv run python -m pytest` or `pytest` |
| `vitest.config.ts` / `vitest.config.js` / `vitest` in package.json | **vitest** | `npx vitest` or `bun vitest`          |
| `jest.config.ts` / `jest.config.js` / `jest` in package.json       | **jest**   | `npx jest` or `bun jest`              |

If both Python and TypeScript tests exist, ask the user which to run. If unclear, default to whichever has a config file in the project root.

---

## Python (pytest)

### Step 1: Discover

1. Locate pytest config (`pyproject.toml` → `[tool.pytest.ini_options]`, `pytest.ini`, `setup.cfg`)
2. Find test directories (`tests/`, `test/`, `**/tests/`)
3. Count tests per directory: `uv run python -m pytest <dir> --co -q 2>&1 | tail -1`
4. List registered markers: `uv run python -m pytest --markers 2>&1 | head -20`
5. Check for conftest.py files and fixtures

Report discovery summary before proceeding.

### Step 2: Categorize

Classify tests into tiers by markers and file naming patterns:

| Tier              | Markers / Patterns                                            | Typical count |
| ----------------- | ------------------------------------------------------------- | ------------- |
| **smoke**         | `test_version.py`, `test_health.py`, `test_sandbox_routes.py` | 5-20          |
| **unit/fast**     | No `slow`/`comprehensive`/`e2e` marker                        | Bulk of suite |
| **slow**          | `@pytest.mark.slow`, `test_performance.py`, ThreadPool usage  | 10-50         |
| **comprehensive** | `@pytest.mark.comprehensive`, artifact generation             | 5-20          |
| **e2e**           | `@pytest.mark.e2e`, workflow execution, multi-step flows      | 5-30          |

### Step 3: Run Targeted

| Scope           | Command                                                                              |
| --------------- | ------------------------------------------------------------------------------------ |
| `smoke`         | `pytest <smoke-files> -v --tb=short -x`                                              |
| `unit` / `fast` | `pytest <test-dir> -v -m "not slow and not comprehensive and not e2e" --tb=short -x` |
| `full`          | `pytest <test-dir> -v --tb=short` (run in background)                                |
| `<file-path>`   | `pytest <file-path> -v --tb=long`                                                    |
| _(no arg)_      | Default to `fast`                                                                    |

**Execution rules:**

- Always use `--tb=short` for large suites, `--tb=long` for single files
- Use `-x` (fail fast) for dev runs, omit for CI/full
- Run `full` scope in background with `run_in_background: true`
- If pytest-xdist is available, add `-n auto` for suites with >100 tests
- If pytest-timeout is available, add `--timeout=30` for unit tests

### Step 4: Diagnose Failures

| Category              | Signal                               | Auto-fixable?                                    |
| --------------------- | ------------------------------------ | ------------------------------------------------ |
| **Missing import**    | `ModuleNotFoundError`, `ImportError` | Yes — check if module exists elsewhere, fix path |
| **Missing fixture**   | `fixture 'X' not found`              | Maybe — check conftest.py files                  |
| **Assertion failure** | `AssertionError`                     | No — report with context                         |
| **Timeout**           | Test hangs >30s                      | Yes — mark as `@pytest.mark.slow`                |
| **Config error**      | `PytestUnknownMarkWarning`, bad ini  | Yes — register marker in config                  |

### Step 5: Fix or Report

**Auto-fix** (do immediately):

- Missing imports → add the import or install the package
- Unregistered markers → add to `pyproject.toml` `[tool.pytest.ini_options].markers`
- Missing `__init__.py` → create empty file
- Wrong import paths → update to match actual module location

**Report** (present to user):

- Assertion failures with expected vs actual values
- Fixture issues requiring design decisions
- Tests that need real services (DB, API keys, network)

After fixes, re-run the same scope to verify.

---

## TypeScript (vitest / jest)

### Step 1: Discover

1. Locate test config (`vitest.config.ts`, `jest.config.ts`, `package.json` scripts)
2. Find test directories (`__tests__/`, `tests/`, `src/**/*.test.ts`, `src/**/*.spec.ts`)
3. Count test files: `find . -name "*.test.ts" -o -name "*.spec.ts" | wc -l`
4. Check for setup files (`setupTests.ts`, `vitest.setup.ts`, `jest.setup.ts`)
5. Check test utilities (`test-utils.ts`, mock helpers, custom render wrappers)

Report discovery summary before proceeding.

### Step 2: Categorize

Classify tests into tiers by file patterns and directory structure:

| Tier            | Patterns                                                                         | Typical count |
| --------------- | -------------------------------------------------------------------------------- | ------------- |
| **smoke**       | `health.test.ts`, `version.test.ts`, `sanity.test.ts`                            | 5-15          |
| **unit/fast**   | `*.test.ts` / `*.spec.ts` without network/DB — pure functions, components, hooks | Bulk of suite |
| **integration** | `*.integration.test.ts`, tests using `supertest`, DB clients, or test containers | 10-50         |
| **e2e**         | `*.e2e.test.ts`, Playwright/Cypress tests, `e2e/` directory                      | 5-30          |

### Step 3: Run Targeted

**Vitest:**

| Scope           | Command                                                            |
| --------------- | ------------------------------------------------------------------ |
| `smoke`         | `vitest run <smoke-files> --reporter=verbose`                      |
| `unit` / `fast` | `vitest run --exclude='**/*.e2e.*' --exclude='**/*.integration.*'` |
| `full`          | `vitest run --reporter=verbose` (run in background)                |
| `<file-path>`   | `vitest run <file-path> --reporter=verbose`                        |
| _(no arg)_      | Default to `fast`                                                  |

**Jest:**

| Scope           | Command                                                      |
| --------------- | ------------------------------------------------------------ |
| `smoke`         | `jest <smoke-files> --verbose`                               |
| `unit` / `fast` | `jest --testPathIgnorePatterns='e2e\|integration' --verbose` |
| `full`          | `jest --verbose` (run in background)                         |
| `<file-path>`   | `jest <file-path> --verbose`                                 |
| _(no arg)_      | Default to `fast`                                            |

**Execution rules:**

- Use `--bail` / `--bail 1` (fail fast) for dev runs
- Run `full` scope in background with `run_in_background: true`
- For vitest: use `--pool=threads` for CPU-bound, `--pool=forks` for memory-heavy
- For jest: use `--maxWorkers=50%` for large suites

### Step 4: Diagnose Failures

| Category              | Signal                                                | Auto-fixable?                               |
| --------------------- | ----------------------------------------------------- | ------------------------------------------- |
| **Missing module**    | `Cannot find module`, `Module not found`              | Yes — check tsconfig paths, install package |
| **Type error**        | `TS2xxx` errors in test files                         | Maybe — check type imports                  |
| **Assertion failure** | `expect(received).toBe(expected)`                     | No — report with context                    |
| **Timeout**           | `Exceeded timeout of 5000 ms`                         | Yes — increase timeout or mark as slow      |
| **Mock issue**        | `jest.fn()` / `vi.fn()` not called, wrong mock return | Maybe — check mock setup                    |
| **ESM/CJS mismatch**  | `SyntaxError: Cannot use import`, `ERR_REQUIRE_ESM`   | Yes — update config                         |

### Step 5: Fix or Report

**Auto-fix** (do immediately):

- Missing modules → install package or fix tsconfig `paths` / `moduleNameMapper`
- ESM/CJS issues → update vitest/jest config for proper module resolution
- Timeout → increase test timeout or add `.skip` with TODO comment
- Missing test utilities → create setup file and configure in test config

**Report** (present to user):

- Assertion failures with expected vs actual snapshots
- Mock design issues requiring architectural decisions
- Tests requiring running services (DB, API, Redis)

After fixes, re-run the same scope to verify.

---

## TDD Workflow (Red-Green-Refactor)

When writing new features with TDD:

### Red Phase
1. Write a failing test that describes the expected behavior
2. Run the test — confirm it fails for the RIGHT reason (not import errors)
3. If it fails for the wrong reason, fix the test setup first

### Green Phase
1. Write the MINIMUM code to make the test pass
2. No refactoring, no cleanup, no extra features
3. Run the test — confirm it passes
4. Run adjacent tests — confirm nothing broke

### Refactor Phase
1. Clean up the implementation while keeping all tests green
2. Extract helpers, rename variables, remove duplication
3. Run the full relevant test tier after each refactor step
4. Commit when tests are green

### TDD Rules
- One test at a time — don't write a batch of tests upfront
- Test behavior, not implementation — tests should survive refactoring
- If you can't write a test, clarify the requirement first
- Each test should have exactly ONE reason to fail

---

## Anti-patterns to Avoid

- **Never** run the full test suite with no scope in a large repo — always tier first
- **Never** let a test suite run >5 minutes without background mode
- **Never** retry a hanging test — mark it as slow and skip it
- **Never** fix assertion failures by changing expected values without understanding intent
- **Never** install packages globally to fix test issues — use project-local installs
- **Never** skip the Red phase — always see the test fail first

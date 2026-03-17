---
name: test-writer
description: "Generate test suites from source code. Reads function signatures, infers behavior, writes failing tests (TDD red phase). Supports pytest, vitest, and jest. Use when asked to generate tests, write test suites, add test coverage, scaffold tests for a module, or create missing tests."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
argument-hint: "<file, module, or directory to generate tests for> [framework: pytest|vitest|jest]"
---

## Setup

Read `config.json` in this skill directory (if it exists) to load user defaults:
- `framework` — test framework to use; if null, auto-detect from project files
- `coverage_threshold` — target coverage %; default 80
- `style` — test style preference; default describe-it

If `framework` is null and auto-detection is ambiguous, use AskUserQuestion:
"Which test framework does this project use? (vitest / jest / pytest)"
Store the answer back to config.json for future invocations.

## Overview

Generates comprehensive test suites from existing source code. Reads public function signatures, infers expected behavior from names, types, and usage patterns, and writes failing tests (TDD red phase). The tests execute but may not pass — that's intentional, as the developer then makes them green.

## Step 0: Detect Project and Framework

| Signal | Framework | Test location |
|---|---|---|
| `vitest.config.*` or `vitest` in package.json | vitest | `__tests__/` or `*.test.ts` colocated |
| `jest.config.*` or `jest` in package.json | jest | `__tests__/` or `*.test.ts` colocated |
| `pytest.ini`, `pyproject.toml` with `[tool.pytest]`, or `conftest.py` | pytest | `tests/` mirror |
| User specifies framework | Use specified | Follow project convention |

Follow the project's existing test file placement convention. If no tests exist yet, use the framework's default layout.

## Step 1: Scan Source Code

For the target file(s) or directory:

1. **Identify public functions/methods** — exported functions, class methods, API handlers
2. **Read type signatures** — parameter types, return types, generics
3. **Read docstrings/comments** — expected behavior hints
4. **Find usage examples** — how the function is called elsewhere in the codebase
5. **Identify edge cases** — nullable params, empty arrays, boundary values, error conditions

Skip: private helpers, generated code, framework glue, getters/setters without logic.

## Step 2: Generate Test Plan

Before writing tests, output a plan:

```
## Test Plan for [module/file]

| Function | Test cases | Priority |
|----------|-----------|----------|
| createUser | happy path, duplicate email, missing fields, password hashing | high |
| findUserById | exists, not found, invalid ID format | medium |
| ...
```

Ask the user to confirm or adjust before proceeding.

## Step 3: Write Test Files

### Naming

- **vitest/jest**: `[source-name].test.ts` — colocated or in `__tests__/`
- **pytest**: `test_[source_name].py` — in `tests/` mirroring source structure

### Structure

Each test file follows Arrange-Act-Assert:

```typescript
// vitest/jest example
describe('createUser', () => {
  it('should create a user with hashed password', () => {
    // Arrange
    const input = { email: 'test@example.com', password: 'secret123' };

    // Act
    const result = createUser(input);

    // Assert
    expect(result.email).toBe('test@example.com');
    expect(result.password).not.toBe('secret123');
  });

  it('should throw when email already exists', () => {
    // ...
  });
});
```

```python
# pytest example
class TestCreateUser:
    def test_creates_user_with_hashed_password(self):
        # Arrange
        input_data = {"email": "test@example.com", "password": "secret123"}

        # Act
        result = create_user(input_data)

        # Assert
        assert result.email == "test@example.com"
        assert result.password != "secret123"

    def test_raises_when_email_exists(self):
        # ...
```

### Test categories to generate

| Category | When to write |
|---|---|
| **Happy path** | Always — the primary success case |
| **Validation** | When the function validates input |
| **Edge cases** | Empty input, boundary values, None/null |
| **Error handling** | When the function can throw/raise |
| **Integration** | For API routes and DB operations (mark with appropriate markers) |

### Mocking strategy

- Mock at integration boundaries only (DB, external APIs, file system)
- Use the project's existing mock patterns (check for `__mocks__/`, `conftest.py`, test utilities)
- Don't mock the unit under test or its direct dependencies

## Step 4: Run Tests

```bash
# Verify tests execute (they may fail — that's expected for TDD red phase)
# vitest
npx vitest run --reporter=verbose [test-file]

# jest
npx jest --verbose [test-file]

# pytest
python -m pytest -v [test-file]
```

If tests fail to EXECUTE (import errors, syntax errors), fix those issues. Tests that execute but have assertion failures are expected and correct — they represent the TDD "red" phase.

## Step 5: Coverage Report

```bash
# vitest
npx vitest run --coverage [test-file]

# jest
npx jest --coverage [test-file]

# pytest
python -m pytest --cov=[module] --cov-report=term-missing [test-file]
```

## Step 6: Summary

```markdown
## Test Generation Summary

| File | Tests written | Executing | Coverage delta |
|------|--------------|-----------|----------------|
| `user.test.ts` | 12 | 12/12 | +24% → 67% |
| `auth.test.ts` | 8 | 8/8 | +18% → 45% |

### Next steps
- [ ] Make failing assertions pass (TDD green phase)
- [ ] Add integration tests for [specific areas]
- [ ] Consider property-based tests for [pure functions]
```

## Gotchas

- Don't mock what you don't own — wrapping third-party APIs in your own adapter and mocking that adapter is safer than mocking the library directly, which breaks when the library changes
- Snapshot tests are brittle and create maintenance burden — prefer explicit assertions over `.toMatchSnapshot()` because snapshots get blindly updated and hide regressions
- Test file placement must match the project's existing convention (co-located `*.test.ts` vs `__tests__/` directory vs `tests/` mirror) — check existing tests first before creating new ones in the wrong location
- Async tests need proper `await` or `return` on promises — a missing `await` causes the test to pass vacuously because the assertion never executes
- Coverage numbers lie — 100% line coverage does not mean all edge cases are tested; focus on behavioral coverage (error paths, boundary values, concurrent access) over line metrics

## Anti-Patterns

- Don't test implementation details (private methods, internal state)
- Don't write tests that depend on execution order
- Don't generate tests for generated code (Prisma client, GraphQL codegen)
- Don't over-mock — if everything is mocked, the test proves nothing
- Don't write trivial tests (getter returns value, constructor sets field)

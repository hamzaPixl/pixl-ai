# Testing

> See also: `references/methodology/tdd.md` for extended TDD patterns and test architecture guidance.

## TDD Workflow

Follow red-green-refactor:

1. **Red** — Write a failing test that describes the expected behavior
2. **Green** — Write the minimum code to make the test pass
3. **Refactor** — Clean up while keeping tests green

## Coverage

- Aim for 80%+ coverage on business logic
- Don't test framework glue, getters/setters, or generated code
- 100% coverage on critical paths (auth, payments, data integrity)

## Test Types

| Type            | Scope                                  | Speed    | When to write                        |
| --------------- | -------------------------------------- | -------- | ------------------------------------ |
| **Unit**        | Single function/class, mocked deps     | < 100ms  | Every public function with logic     |
| **Integration** | Multiple modules, real deps (DB, etc.) | < 5s     | API routes, database operations      |
| **E2E**         | Full user flow through the UI          | < 30s    | Critical paths (signup, checkout)    |
| **Smoke**       | App starts, health check passes        | < 1s     | Every deployable service             |

## Test Naming

Use descriptive names that read as specifications:

```
"should return 404 when user does not exist"
"should hash password before storing"
"should reject expired tokens"
```

## Test Structure

Follow Arrange-Act-Assert:

```
// Arrange — set up test data and dependencies
// Act — call the function under test
// Assert — verify the result
```

## Anti-Patterns

- Don't test implementation details (private methods, internal state)
- Don't write tests that depend on execution order
- Don't mock what you don't own — use integration tests instead
- Don't use `any` in test types — it hides real bugs
- Don't skip flaky tests — fix the root cause or delete them

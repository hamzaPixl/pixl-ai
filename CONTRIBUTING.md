# Contributing to Pixl

Thank you for contributing! This guide covers setup, development workflow, code style, testing, and release procedures.

## Prerequisites

- **Python 3.12+** — engine and CLI are Python-based
- **uv** — package manager and workspace manager (`pip install uv`)
- **Node.js 18+** — for sandbox development (TypeScript/Cloudflare Workers)
- **Git** — version control

## Development Setup

### Full Setup (Recommended)

```bash
make setup
```

This installs all workspace packages (engine + CLI) and registers the crew plugin with Claude Code.

### Install Only (No Crew Registration)

```bash
make install
```

This syncs the uv workspace without registering the Claude Code plugin.

### Workspace Structure

- **`packages/engine`** — Pixl orchestration engine (Python)
- **`packages/cli`** — Pixl CLI (Python, Click-based)
- **`packages/crew`** — Claude Code crew plugin (bash/markdown, NOT a Python package)
- **`packages/sandbox`** — Cloudflare Workers sandbox (TypeScript)

Dependencies are managed via the root `pyproject.toml` workspace. See [CLAUDE.md](./CLAUDE.md) for the full structure.

## Code Style & Conventions

### Python

Follow PEP 8 with these extensions:

#### Naming
- Files: `snake_case.py`
- Classes/Types: `PascalCase`
- Functions/Variables: `camelCase`
- Constants: `UPPER_SNAKE_CASE` for true constants, `camelCase` for derived values
- Booleans: prefix with `is`, `has`, `can`, `should` (e.g., `is_valid`, `has_permission`)

#### Immutability
- Prefer immutable data structures where possible
- Use `frozen=True` for dataclasses that shouldn't change
- Avoid mutation in utility functions

#### Imports
- Group: external packages → internal modules → relative imports → types
- Use `from __future__ import annotations` for forward references
- One class/module per file (exceptions: closely related utilities)

#### Error Handling
- Use typed exceptions, not string messages
- Catch exceptions at boundaries (API routes, CLI commands), not in utilities
- Log errors — never swallow them silently
- Use `Result<T, E>` patterns when error handling is part of the contract

#### File Size
- Keep source files under 300 lines — split larger modules
- Keep functions under 50 lines — extract helpers as they grow

### TypeScript (Sandbox)

- Files: `kebab-case.ts`
- Use `const` over `let` — only use `let` when reassignment is necessary
- Use `readonly` for class properties that shouldn't change
- Group imports: external → internal → relative → types
- Use named exports over default exports

### Formatting & Linting

Automatic formatting is enforced:

```bash
make format          # Auto-format all code
make check           # Lint + type check (ruff + pyright)
make typecheck       # Type check only
```

These tools are configured in `pyproject.toml` and run on every commit (if pre-commit hooks are installed).

## Testing

### TDD Workflow

Follow red-green-refactor:

1. **Red** — Write a failing test that describes the expected behavior
2. **Green** — Write the minimum code to make the test pass
3. **Refactor** — Clean up while keeping tests green

### Coverage Requirements

- CI enforces **50% minimum** coverage (`fail_under = 50` in pyproject.toml)
- Aim for **80%+ coverage** on critical paths (auth, state transitions, cost calculations)
- Avoid testing framework glue, getters/setters, or generated code

### Test Types

| Type | Scope | Speed | When to write |
|------|-------|-------|---------------|
| Unit | Single function/class, mocked deps | < 100ms | Every public function with logic |
| Integration | Multiple modules, real DB | < 5s | API routes, database operations |
| E2E | Full workflow through CLI | < 30s | Critical paths (project init, workflow run) |

### Running Tests

```bash
make test             # Run all tests (engine + CLI)
make test-engine      # Engine tests only
make test-cli         # CLI tests only
make test-cov         # Run with coverage report
```

### Test Naming

Write test names as specifications:

```python
def test_should_reject_invalid_workflow_template():
    ...

def test_should_return_404_when_session_not_found():
    ...
```

### Test Structure

Follow Arrange-Act-Assert:

```python
def test_should_execute_workflow():
    # Arrange — set up test data and dependencies
    template = create_test_template()

    # Act — call the function under test
    session = execute_workflow(template)

    # Assert — verify the result
    assert session.status == "completed"
```

### Anti-Patterns

- Don't test private methods or implementation details
- Don't write tests that depend on execution order
- Don't mock what you don't own — use integration tests instead
- Don't skip flaky tests — fix the root cause
- Don't use `any` in type hints — it hides bugs

## Git Workflow

### Branch Naming

- `feat/short-description` — new features
- `fix/issue-number-or-description` — bug fixes
- `refactor/what-is-changing` — refactoring
- `chore/task-description` — maintenance, deps, tooling

### Conventional Commits

Use the format: `type(scope): description`

| Type | When |
|------|------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `refactor` | Code change that neither fixes nor adds |
| `chore` | Build, tooling, dependency updates |
| `docs` | Documentation only |
| `test` | Adding or fixing tests |
| `perf` | Performance improvement |
| `ci` | CI/CD pipeline changes |
| `style` | Formatting, whitespace (no logic change) |

Examples:

```
feat(cli): add --quiet flag to workflow run
fix(engine): resolve session state race condition
refactor(storage): extract database connection logic
chore(deps): bump pixl-engine to 9.0.2
docs: update README installation section
test(executor): add tests for graph execution with cycles
```

### Commit Practices

- Each commit should compile and pass tests on its own
- Don't commit commented-out code — use git history instead
- Don't commit TODO/FIXME without a linked issue
- Squash fixup commits before merging
- Write clear commit messages that explain WHY, not just WHAT

### PR Hygiene

- Keep PRs under 400 lines when possible — split large changes
- One logical change per PR — don't bundle unrelated fixes
- Write a description that explains the problem and solution
- Link to issues/tickets in the PR body
- Request review from domain experts (engine, CLI, crew, sandbox)

## Release Process

Releases use semantic versioning (MAJOR.MINOR.PATCH).

### Create a Release

```bash
# Bump patch version (9.0.2 → 9.0.3)
make release

# Bump minor version (9.0.2 → 9.1.0)
make release BUMP=minor

# Bump major version (9.0.2 → 10.0.0)
make release BUMP=major
```

The release script:
1. Updates version in all `pyproject.toml` files
2. Creates a git tag (`v9.0.3`)
3. Pushes to remote

## Common Tasks

### Install Pre-Commit Hooks

```bash
make pre-commit
```

Hooks enforce formatting and catch common issues before commit.

### Add a Dependency

```bash
# Python (engine or CLI)
cd packages/engine  # or packages/cli
uv add <package>
```

Dependencies are specified in each package's `pyproject.toml`.

### Add a Test

```bash
# Engine test
packages/engine/tests/test_*.py

# CLI test
packages/cli/tests/test_*.py
```

Use pytest fixtures from `conftest.py` for setup/teardown.

### Rebuild Documentation

Most docs are in the codebase:
- `CLAUDE.md` — architecture, CLI reference, skills, agents
- `CONTRIBUTING.md` — development guide (this file)
- `packages/*/README.md` — package-specific docs
- `.claude/rules/` — coding standards and workflows

## Project Rules

See `.claude/rules/` for detailed guidelines:

- `coding-style.md` — immutability, naming, file size, error handling
- `testing.md` — TDD workflow, coverage targets, test types
- `git-workflow.md` — commits, PRs, branch naming
- `security.md` — input validation, auth, secrets, OWASP
- `patterns.md` — search-first, read-before-write
- `workflow.md` — background tasks, parallelism, frequent commits
- `performance.md` — profiling, database, frontend, API patterns
- `context-management.md` — context budgets, delegation, routing
- `permissions.md` — permission wildcards over blanket access

## Getting Help

- **Architecture questions** → See [CLAUDE.md](./CLAUDE.md)
- **Engine internals** → See [packages/engine/README.md](./packages/engine/README.md)
- **CLI commands** → See [packages/cli/README.md](./packages/cli/README.md)
- **Crew plugin** → See [packages/crew/CLAUDE.md](./packages/crew/CLAUDE.md)
- **Code style** → See [.claude/rules/coding-style.md](./.claude/rules/coding-style.md)

## Troubleshooting

### Tests fail after pulling

```bash
make install        # Re-sync workspace
make clean          # Clear __pycache__
make test           # Re-run
```

### Type checker fails

```bash
make typecheck      # See detailed errors
# Fix issues (usually imports or type hints)
```

### Pre-commit hook fails

```bash
make format         # Auto-fix formatting
git add .           # Re-stage
git commit ...      # Try again
```

### Import errors

```bash
# Ensure you're in the uv virtual environment
uv run python -c "import pixl"  # Should work without error
```

## Questions?

Please open an issue or discussion. We're happy to help!

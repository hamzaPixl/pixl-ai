---
name: makefile
description: "Create a Makefile with central commands for a project — build, test, lint, deploy, docker, and dev workflow commands. Use when asked to add a Makefile, standardize project commands, or create dev tooling."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
argument-hint: "<project to add Makefile for>"
disable-model-invocation: true
---

## Overview

Creates a Makefile following pixl-crew conventions. The focus is on non-obvious patterns — self-documenting help targets, monorepo-aware workspace targets, and correct integration with uv/bun/Docker Compose.

## Step 1: Discovery

1. Detect project language, build system, and package manager
2. Identify existing scripts in `package.json`, `pyproject.toml`, etc.
3. Check for Docker/Docker Compose, CI/CD, and deployment tools
4. Determine if this is a monorepo (multiple `package.json`/`pyproject.toml` files, workspace config)
5. Check for `.env` files that need loading

## Step 2: Generate Makefile

### Structure

Follow this ordering convention:

```makefile
# 1. .PHONY declaration — ALL non-file targets, one line
.PHONY: setup install dev build test lint format typecheck clean deploy docker-build docker-up help

# 2. Environment loading
ifneq (,$(wildcard .env))
  include .env
  export
endif

# 3. Variables with ?= defaults (overridable from CLI)
PORT ?= 3000
ENV ?= development
BUMP ?= patch

# 4. Composite targets first (setup, ci)
# 5. Dev targets (dev, build, clean)
# 6. Quality targets (test, lint, format, typecheck)
# 7. Deploy targets (deploy, docker-*)
# 8. help target LAST
```

### Self-Documenting Help Target

Every target MUST have a `## Comment` suffix. The `help` target auto-generates docs from these:

```makefile
setup: install  ## Full setup: install deps + configure
	@echo "Ready."

help:  ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' Makefile | awk 'BEGIN {FS=":.*?## "};{printf "  %-18s %s\n",$$1,$$2}'
```

### Package Manager Targets

**uv (Python)**:
```makefile
PYTEST := uv run python -m pytest --import-mode=importlib

install:  ## Install workspace packages
	uv sync --all-extras

test:  ## Run all tests
	$(PYTEST)

lint:  ## Lint check
	uv run ruff check .

format:  ## Auto-format
	uv run ruff check --fix .
	uv run ruff format .
```

**bun (TypeScript)**:
```makefile
install:  ## Install dependencies
	bun install

dev:  ## Start dev server
	bun run dev

build:  ## Production build
	bun run build

test:  ## Run tests
	bun test
```

**npm/pnpm**: Same pattern, substitute `npm run` / `pnpm run`.

### Monorepo / Workspace Targets

For monorepos, add per-package targets using a consistent naming pattern:

```makefile
# Per-package targets
test-engine:  ## Engine tests only
	$(PYTEST) packages/engine/tests/

test-cli:  ## CLI tests only
	$(PYTEST) packages/cli/tests/

lint-web:  ## Lint web package
	cd packages/web && bun run lint
```

### Docker Compose Integration

```makefile
docker-up:  ## Start all services
	docker compose up -d

docker-down:  ## Stop all services
	docker compose down

docker-build:  ## Build images
	docker compose build

docker-logs:  ## Tail service logs
	docker compose logs -f

docker-reset:  ## Full reset: down + remove volumes + rebuild
	docker compose down -v
	docker compose build --no-cache
	docker compose up -d
```

### CI Composite Target

Chain quality checks into a single CI target:

```makefile
ci: lint typecheck test build  ## Run full CI pipeline locally
```

## Step 3: Integrate

1. Add convenience targets that chain commands (e.g., `make ci` = lint + typecheck + test + build)
2. Add environment-specific targets if deployment config exists (dev, staging, production)
3. Add a `release` target if a release script exists
4. Verify every target has a `## Comment` for the help target

## Step 4: Verify

- [ ] `make help` lists all available targets with descriptions
- [ ] All targets execute without errors
- [ ] `.PHONY` includes every non-file target
- [ ] No conflicts with existing build tools
- [ ] Variables use `?=` so they can be overridden from the CLI

## Gotchas

1. **Always use tabs, not spaces** — Make requires literal tab characters for recipe indentation. Spaces cause `*** missing separator` errors.
2. **Use `.PHONY` for ALL non-file targets** — Without it, if a directory named `test` or `build` exists, `make test` silently does nothing because the "file" is already up to date.
3. **Use `$(MAKE)` for recursive make calls** — Never use bare `make` inside a recipe. `$(MAKE)` preserves flags like `-j` (parallel) and `--dry-run`.
4. **Set `SHELL := /bin/bash` if using bash-isms** — Make defaults to `/bin/sh`. Features like `{a,b}` brace expansion, `[[ ]]` tests, and `<()` process substitution require bash.
5. **Double `$$` for shell variables** — Make interprets `$` as a Make variable. To pass `$HOME` to the shell, write `$$HOME`. This is the #1 source of silent Makefile bugs.

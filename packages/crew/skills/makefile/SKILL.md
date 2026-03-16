---
name: makefile
description: "Create a Makefile with central commands for a project — build, test, lint, deploy, docker, and dev workflow commands. Use when asked to add a Makefile, standardize project commands, or create dev tooling."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
argument-hint: "<project to add Makefile for>"
disable-model-invocation: true
---

## Overview

Creates a comprehensive Makefile with standardized commands for building, testing, linting, deploying, and running development workflows.

## Step 1: Discovery

1. Detect project language, build system, and package manager
2. Identify existing scripts in package.json, pyproject.toml, etc.
3. Check for Docker, CI/CD, and deployment tools
4. Determine which commands are most frequently used

## Step 2: Generate Makefile

1. Create `Makefile` with standard targets
2. Include `.PHONY` declarations
3. Add variables for configurable values (port, environment)
4. Group targets by category (dev, build, test, deploy, docker)

Standard targets:

- `make dev` — Start development environment
- `make build` — Build the project
- `make test` — Run all tests
- `make lint` — Run linter
- `make format` — Format code
- `make typecheck` — Run type checker
- `make clean` — Remove build artifacts
- `make deploy` — Deploy to production
- `make docker-build` — Build Docker image
- `make docker-run` — Run Docker container
- `make help` — Show available targets

## Step 3: Integrate

1. Add convenience targets that chain commands (e.g., `make ci` = lint + typecheck + test + build)
2. Add environment-specific targets (dev, staging, production)
3. Document each target with comments

## Step 4: Verify

- [ ] All targets execute without errors
- [ ] `make help` lists all available targets
- [ ] No conflicts with existing build tools

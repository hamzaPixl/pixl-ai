.PHONY: setup install crew-setup test test-engine test-cli check format release clean help

# Load .env file if present
ifneq (,$(wildcard .env))
  include .env
  export
endif

PYTEST := uv run python -m pytest --import-mode=importlib

setup: install crew-setup  ## Full setup: install + register crew
	@echo "Done. Run 'pixl --version' to verify."

install:  ## Install workspace packages
	uv sync --all-extras

crew-setup:  ## Register crew plugin with Claude Code
	uv run pixl setup

test:  ## Run all tests
	$(PYTEST)

test-engine:  ## Engine tests only
	$(PYTEST) packages/engine/tests/

test-cli:  ## CLI tests only
	$(PYTEST) packages/cli/tests/

check:  ## Lint check
	uv run ruff check packages/engine/ packages/cli/
	uv run ruff format --check packages/engine/ packages/cli/

format:  ## Auto-format
	uv run ruff check --fix packages/engine/ packages/cli/
	uv run ruff format packages/engine/ packages/cli/

BUMP ?= patch
release:  ## Bump version, tag, push
	@bash scripts/release.sh $(BUMP)

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

help:  ## Show targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' Makefile | awk 'BEGIN {FS=":.*?## "};{printf "  %-18s %s\n",$$1,$$2}'

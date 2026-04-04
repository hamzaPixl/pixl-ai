# pixl — Codex Instructions

This repo is a monorepo for the Pixl AI platform (engine + CLI + API + console + crew + sandbox).
Use these instructions when working with Codex in this repo.

## Project Layout

- `packages/engine/` — Python orchestration engine (core workflows, providers, storage)
- `packages/cli/` — Python CLI (`pixl`)
- `packages/api/` — FastAPI service
- `packages/console/` — React SPA (Vite)
- `packages/crew/` — Claude Code crew plugin (agents/skills/hooks)
- `packages/sandbox/` — Cloudflare Workers sandbox

## Build & Test

- `make setup` — full setup (uv sync + pixl setup)
- `make test` — run all tests
- `make test-cli` — CLI tests
- `make test-api` — API tests
- `make dev-platform` — API + Console dev servers
- `make check` — lint/typecheck
- `make format` — auto-format

Python is 3.12+. The Python workspace is `uv`-managed. The console is `pnpm`-managed.

## Codex Integration

- Codex config: `.codex/config.toml`
- Codex hooks: `.codex/hooks.json`
- Codex rules: `.codex/rules/*.rules`
- Codex custom agents: `.codex/agents/*.toml`
- Codex skills: `.agents/skills/*/SKILL.md` (symlinked from `packages/crew/skills`)

Prefer using skills when a matching skill exists. Keep changes minimal and aligned to existing patterns.

## Claude Compatibility

Claude Code assets still live under `packages/crew/` and `.claude/`. Do not delete them.
Codex support is additive (parallel structure), not a replacement.

# pixl-engine

> Core AI engine for Pixl Platform — workflow orchestration, DAG execution, state management, knowledge indexing, and multi-provider AI integration.

## Overview

pixl-engine is the brain of the Pixl Platform. It handles everything from prompt classification and workflow selection to DAG-based execution, PM supervision, and recovery. Originally extracted from the **synq** project, it includes 1340+ passing tests.

## Features

| Module | Description |
|---|---|
| **Models** | 20+ Pydantic v2 models for workflows, features, epics, sessions, boulders |
| **Execution** | `GraphExecutor` (DAG engine), `ChainRunner` (epic orchestration), `DaytonaBackend` (sandbox execution) |
| **State** | `TransitionEngine` + `StateMachine` with typed guards and effects |
| **Storage** | SQLite WAL + FTS5 full-text search, per-project database isolation |
| **Providers** | Anthropic, OpenAI, Gemini — behind a common `ProviderRegistry` |
| **Knowledge** | tree-sitter AST chunker + FTS5-powered RAG search |
| **Context** | `UnifiedContextCompiler` — assembles rich prompts from multiple sources |
| **Routing** | `PromptClassifier` — LLM-powered workflow selection from user prompts |
| **Recovery** | `RecoveryEngine` with incident store and automatic repair policies |
| **Config** | YAML-based workflow definitions (11 built-in workflows) |
| **Session** | `SessionManager` for lifecycle management |
| **Git** | PR automation via `gh` CLI |

## Workflows

11 built-in YAML workflow definitions:

`simple` · `tdd` · `decompose` · `consolidate` · `roadmap` · `debug` · `blocks` · `knowledge-build` · `project-setup` · `detect-context` · `detect-context-epic`

## Architecture Patterns

- **DAG Execution** — Directed acyclic graph orchestration via `GraphExecutor`
- **Baton Pattern** — Inter-stage context relay, accumulating results across workflow stages
- **Supervisor Pattern** — `PMSupervisor` monitors for loops, pathological behavior
- **Contract Validation** — Output quality gates via `ContractValidator`
- **Protocol Pattern** — `ExecutionBackend` protocol with Daytona sandbox implementation

## Installation

```bash
# As part of the monorepo
make install

# Or standalone
cd packages/engine
uv pip install -e ".[dev]"
```

## Testing

```bash
make test-engine        # All 1340 tests
make test-execution     # Execution layer only
make test-backends      # Backend tests
make test-state         # State machine tests
make test-session       # Session tests
```

## Package Structure

```
pixl/
├── models/        # Pydantic data models
├── execution/     # GraphExecutor, ChainRunner, PMSupervisor
├── state/         # TransitionEngine, StateMachine, guards, effects
├── storage/       # SQLite WAL + FTS5, schema migrations
├── providers/     # AI provider registry (Anthropic, OpenAI, Gemini)
├── routing/       # PromptClassifier
├── knowledge/     # AST chunker, knowledge search
├── context/       # UnifiedContextCompiler
├── session/       # SessionManager
├── recovery/      # RecoveryEngine, incident store
├── config/        # Workflow/agent YAML loaders
├── agents/        # SDK options builder, hooks
├── foundation/    # CORS, auth middleware, pagination
├── git/           # PR automation
├── assets/        # Workflow YAMLs, prompts, JSON schemas
└── observability/ # Logging, metrics
```

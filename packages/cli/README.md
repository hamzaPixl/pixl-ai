# pixl-cli

> Pixl CLI — local bridge to the pixl-engine. Orchestrate workflows, manage sessions, inspect execution events, and configure projects from the command line.

## Overview

`pixl-cli` is a Click-based command-line interface that provides local access to the Pixl Platform. It manages workflow execution, project configuration, session history, cost analytics, and integration with the Claude Code crew plugin.

## Installation

### From PyPI

```bash
uv tool install pixl
```

### From Source

```bash
# Full monorepo setup (includes engine + CLI)
make setup

# Or just CLI
cd packages/cli
uv pip install -e .
```

### Verify Installation

```bash
pixl --version
pixl --help
```

## Quick Start

### Initialize a Project

```bash
# Create a new .pixl/ project directory
pixl project init

# Or use pixl setup to register with Claude Code
pixl setup
```

### Run a Workflow

```bash
# Execute a workflow template
pixl workflow run <workflow-id>

# Auto-approve gates
pixl workflow run <workflow-id> --yes
```

### View Results

```bash
# List sessions
pixl session list

# View session details
pixl session show <session-id>

# List artifacts from a session
pixl artifact list --session <session-id>
```

## Commands

| Command | Subcommand | Description |
|---------|-----------|-------------|
| **artifact** | list | List build artifacts |
| **config** | get | Get project configuration |
| **config** | set | Update project configuration |
| **cost** | summary | Cost analytics: total, by-model, by-session |
| **events** | list | List execution events |
| **event-stats** | show | Show event statistics |
| **knowledge** | build | Build AST-indexed knowledge base from codebase |
| **knowledge** | search | Search knowledge base |
| **project** | init | Initialize a `.pixl/` project directory |
| **project** | list | List all registered projects |
| **project** | get | Get project info by ID |
| **sandbox** | create | Create a sandbox project |
| **sandbox** | workflow | Run a workflow in sandbox (with `--stream` for SSE) |
| **sandbox** | sync | Sync sandbox data (events, sessions, artifacts) |
| **session** | list | List workflow sessions |
| **session** | show | Show session details |
| **setup** | (no subcommand) | Register crew plugin with Claude Code |
| **state** | show | Show entity state and transitions |
| **template** | list | List workflow templates |
| **template** | get | Get template details |
| **template** | create | Create a new workflow template |
| **template** | delete | Delete a workflow template |
| **workflow** | list | List available workflows |
| **workflow** | run | Execute a workflow template |

## Global Options

All commands support these global options:

| Option | Default | Description |
|--------|---------|-------------|
| `--json` | false | Output JSON instead of human-readable text (useful for scripts/automation) |
| `--project <path>` | cwd | Project root path (where `.pixl/` is stored) |
| `--version` | — | Show version |
| `--help` | — | Show help |

## Configuration

Projects are configured in `.pixl/pixl.db` (SQLite) when the CLI is installed, or in `.claude/memory/` (file-based) when the CLI is absent.

### Project Structure

```
.pixl/
├── pixl.db          # SQLite database (sessions, artifacts, events, knowledge)
├── workflows/       # Custom workflow definitions
└── .pixlignore      # Files to exclude from knowledge indexing
```

### Setting Configuration

```bash
pixl config set <key> <value> --project <path>
```

Common configuration keys:
- `model` — LLM provider model
- `temperature` — LLM temperature (0-1)
- `max_tokens` — Max completion tokens

## Examples

### Run a workflow with auto-approval

```bash
pixl workflow run simple --yes
```

### Export workflow sessions to JSON

```bash
pixl session list --json > sessions.json
```

### Build and search a codebase knowledge base

```bash
pixl knowledge build
pixl knowledge search "authentication handler"
```

### View cost breakdown

```bash
pixl cost summary
pixl cost summary --json | jq '.by_model'
```

### Create a sandbox and run a workflow remotely

```bash
pixl sandbox create --fork-from <session-id>
pixl sandbox workflow tdd --stream
```

## Development

### Setup for Contributors

```bash
make install          # Install dependencies
make test-cli         # Run CLI tests
make check            # Lint + type check
make format           # Auto-format code
```

### Project Structure

```
pixl_cli/
├── main.py           # Click group + CLI entry point
├── crew.py           # Crew plugin resolver
├── context.py        # CLIContext (shared state)
├── sandbox_client.py # HTTP client for sandbox API
├── _output.py        # Output formatting (JSON, tables, etc)
├── _lazy.py          # LazyGroup for lazy command loading
└── commands/         # Command modules (artifact, config, cost, etc)
```

### Adding a New Command

1. Create a file in `pixl_cli/commands/` (e.g., `mycommand.py`)
2. Define Click command group and subcommands:

```python
import click
from pixl_cli.main import get_ctx

@click.group()
def mycommand():
    """My command group."""

@mycommand.command()
@click.pass_context
def mysubcommand(ctx):
    cli = get_ctx(ctx)
    # Use cli.project_path and cli.is_json
```

3. Register in `main.py` COMMAND_MODULES dict:

```python
COMMAND_MODULES = {
    "mycommand": "pixl_cli.commands.mycommand",
    ...
}
```

## Testing

```bash
# Run all CLI tests
make test-cli

# Run with coverage
make test-cov
```

Tests use pytest with fixtures for temporary projects and mock databases.

## Related

- [pixl-engine](../engine/README.md) — Core orchestration engine
- [pixl-crew](../crew/) — Claude Code crew plugin
- [pixl-sandbox](../sandbox/) — Cloudflare Workers sandbox runtime
- [CONTRIBUTING.md](../../CONTRIBUTING.md) — Development guide for the whole project

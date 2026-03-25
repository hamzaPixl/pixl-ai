# pixl Project Workflow

Complete guide for creating, developing, and validating projects with pixl.

## 1. Create a Project

```bash
# Full setup (creates dir + git + crew + runs project-setup workflow)
pixl project new my-app

# Quick scaffold (skip the setup workflow)
pixl project new my-app --no-setup

# Custom parent directory
pixl project new my-api --path ~/code --description "REST API for widgets"
```

**What gets created:**

```
~/projects/my-app/              # your code
├── .pixl/
│   ├── project.json            # marker {project_id, project_name}
│   ├── workflows/              # project-specific workflow overrides
│   └── sessions/               # session working dirs
├── .claude/
│   ├── rules/                  # crew rules (workflow, delegation, enforcement)
│   └── settings.local.json     # project permissions
├── CLAUDE.md                   # project instructions for Claude
├── README.md
└── .git/

~/.pixl/                        # centralized storage
├── projects.json               # lightweight index
└── projects/<id>/
    ├── pixl.db                 # THE database (created on first access)
    └── config.json             # project metadata
```

## 2. Develop

### Interactive (Claude Code session)

```bash
cd ~/projects/my-app && claude
```

Inside the session, crew agents and skills are available. The SessionStart hook injects project context automatically.

### Workflow run (automated pipeline)

```bash
# Auto-selects workflow from prompt intent:
pixl --project ~/projects/my-app workflow run \
  --prompt "Build a user authentication system" --yes

# Specify workflow explicitly:
pixl --project ~/projects/my-app workflow run \
  --prompt "Fix the login validation bug" --workflow debug --yes
```

### Workflow auto-selection

When `--workflow` is omitted, pixl classifies the prompt and picks the right workflow:

| Prompt intent | Keywords | Workflow |
|---|---|---|
| Build / create / implement | *(default)* | `simple` |
| Fix bug / error / broken | fix, bug, error, broken, crash, debug | `debug` |
| Test-first development | tdd, test-driven, test first, write tests | `tdd` |
| Break down epic | decompose, break down, epic, multi-feature | `decompose` |
| Strategic planning | roadmap, milestone, strategic plan | `roadmap` |

### Available workflows

| Workflow | Stages | Use case |
|---|---|---|
| `simple` | plan → approve → implement → finalize | General feature development |
| `tdd` | design → approve → implement (TDD) → finalize | Test-driven development |
| `debug` | RED → FIX → PROVE | Bug fixing |
| `decompose` | analyze → break down → create backlog | Epic decomposition |
| `roadmap` | research → plan milestones → epics | Strategic planning |
| `project-setup` | detect stack → registry → docs → knowledge → verify | New project initialization |
| `knowledge-build` | scan → index → verify | Build code search index |

## 3. Monitor

```bash
# Session tracking
pixl --project . session list              # list all sessions
pixl --project . events list               # execution events

# Cost analytics
pixl --project . cost summary              # total cost, by model, by session

# Code search (AST-indexed)
pixl --project . knowledge build           # build/rebuild index
pixl --project . knowledge search "auth"   # search indexed code

# Project state
pixl --project . state show                # entity state machine
pixl --project . artifact list             # build artifacts
```

## 4. Sandbox Validation

Sandboxes run workflows in isolated Cloudflare containers. Use them to validate before merging to production.

### Setup

Requires `PIXL_SANDBOX_URL` and `PIXL_SANDBOX_TOKEN` environment variables pointing to your sandbox API deployment.

### Lifecycle

```bash
# Create a sandbox from a git repo
pixl sandbox create my-sandbox \
  --repo-url https://github.com/user/repo \
  --branch main \
  --env "DATABASE_URL=postgres://..." \
  --env "API_KEY=sk-..."

# Fork from an existing sandbox session (carry over state)
pixl sandbox create my-fork \
  --repo-url https://github.com/user/repo \
  --fork-from my-sandbox:sess-abc123

# Check sandbox status
pixl sandbox status my-sandbox

# List all sandboxes
pixl sandbox list
pixl sandbox list --status running
```

### Run workflows in sandbox

```bash
# Run with live streaming (default)
pixl sandbox workflow my-sandbox \
  --prompt "Add rate limiting to the API" \
  --yes

# Specify workflow
pixl sandbox workflow my-sandbox \
  --prompt "Fix the auth bug" \
  --workflow-id debug \
  --yes

# JSON output (for CI/CD pipelines)
pixl --json sandbox workflow my-sandbox \
  --prompt "Build the search feature" \
  --no-stream
```

### Monitor sandbox execution

```bash
# View events from sandbox
pixl sandbox events my-sandbox --limit 100

# View sessions
pixl sandbox sessions my-sandbox

# Execute commands directly in sandbox
pixl sandbox exec my-sandbox -- ls -la
pixl sandbox exec my-sandbox -- python -m pytest
pixl sandbox exec my-sandbox -- git log --oneline -5
```

### Sync & export

```bash
# Sync sandbox data (events, sessions, artifacts) to local DB
pixl sandbox sync my-sandbox

# Export a session as portable JSON bundle
pixl sandbox export-session my-sandbox sess-abc123 > session.json

# Import a session bundle into another sandbox
pixl sandbox import-session other-sandbox < session.json

# Git operations on sandbox
pixl sandbox git my-sandbox -- status
pixl sandbox git my-sandbox -- push origin main
```

### Cleanup

```bash
# Cancel running workflow
pixl sandbox cancel my-sandbox

# Destroy sandbox (removes container)
pixl sandbox destroy my-sandbox
```

### CI/CD integration

```yaml
# .github/workflows/pixl-validate.yml
name: Pixl Sandbox Validation
on: [pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install pixl
        run: uv tool install pixl && pixl setup

      - name: Create sandbox
        env:
          PIXL_SANDBOX_URL: ${{ secrets.PIXL_SANDBOX_URL }}
          PIXL_SANDBOX_TOKEN: ${{ secrets.PIXL_SANDBOX_TOKEN }}
        run: |
          pixl sandbox create pr-${{ github.event.number }} \
            --repo-url ${{ github.event.pull_request.head.repo.clone_url }} \
            --branch ${{ github.head_ref }}

      - name: Run validation workflow
        run: |
          pixl --json sandbox workflow pr-${{ github.event.number }} \
            --prompt "Validate the changes in this PR" \
            --workflow-id simple \
            --yes --no-stream

      - name: Cleanup
        if: always()
        run: pixl sandbox destroy pr-${{ github.event.number }}
```

## 5. Manage Projects

```bash
# List all projects
pixl project list

# Get project details
pixl project get <project-id>

# Initialize pixl in an existing directory
cd ~/existing-project && pixl project init

# Delete project (removes DB + context + index entry)
pixl project delete <project-id> --yes
```

## Storage Architecture

```
~/.pixl/                                    # global (centralized)
├── projects.json                           # index: {id: {name, root}}
├── projects/
│   └── <project-id>/
│       ├── pixl.db                         # SQLite DB (sessions, events, artifacts, backlog)
│       └── config.json                     # project metadata
├── workflows/                              # user-level workflow overrides
└── providers.yaml                          # LLM provider config

~/projects/<name>/                          # project root
└── .pixl/
    ├── project.json                        # marker: {project_id}
    ├── workflows/                          # project-specific workflow overrides
    ├── sessions/                           # session working dirs (baton, artifacts)
    └── providers.yaml                      # project-level provider overrides
```

**Key principle:** DB is centralized at `~/.pixl/`. Project's `.pixl/` is just context. Delete removes both.

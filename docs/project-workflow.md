# pixl Project Workflow

Complete guide for creating, developing, and validating projects with pixl.

## 1. Create a Project

### New project (from scratch)

```bash
pixl project new my-app                          # ~/projects/my-app
pixl project new my-app --path ~/code            # ~/code/my-app
pixl project new my-app --no-setup               # skip project-setup workflow
pixl project new my-api --description "REST API"
```

### Existing project

```bash
cd ~/existing-project
pixl project init                    # creates .pixl/ + .claude/ + CLAUDE.md
pixl project init --name "My App"    # override project name
pixl project init --no-crew          # pixl infrastructure only, no crew files
pixl project init --setup            # also run project-setup workflow
```

### What gets created

```
my-app/
├── .pixl/
│   ├── project.json            # {project_id, project_name}
│   ├── sdk-stderr.log          # SDK subprocess debug log
│   ├── sessions/               # per-session working dirs
│   └── workflows/              # project-specific workflow overrides
├── .claude/
│   ├── rules/                  # crew-workflow.md, crew-delegation.md, crew-enforcement.md, crew-context.md
│   ├── settings.local.json     # scoped permissions (22 Bash patterns)
│   └── memory/
│       ├── sessions/           # session summaries (auto-bridged from engine)
│       ├── costs.jsonl         # per-session cost log
│       └── decisions.jsonl     # decision log (from /session-wrap)
├── CLAUDE.md                   # project instructions (14 agents, 75 skills)
├── README.md
└── .git/

~/.pixl/                        # centralized storage (shared across projects)
├── projects.json               # lightweight index
└── projects/<id>/
    ├── pixl.db                 # SQLite DB (created on first access)
    └── config.json             # project metadata
```

## 2. Run Workflows

### Interactive (Claude Code session)

```bash
cd my-app && claude
# Crew agents and skills are available. SessionStart hook injects context.
```

### Automated (pixl workflow run)

```bash
# Auto-selects workflow from prompt intent
pixl workflow run --prompt "Build user auth" --yes

# Specify workflow explicitly
pixl workflow run --prompt "Fix login bug" --workflow debug --yes

# JSON output (NDJSON event stream)
pixl --json workflow run --prompt "Add health check" --yes

# Target a specific project
pixl --project ~/code/my-app workflow run --prompt "..." --yes
```

### Workflow auto-selection

When `--workflow` is omitted, pixl classifies the prompt:

| Prompt intent | Workflow |
|---|---|
| Build / create / implement *(default)* | `simple` |
| Fix bug / error / broken | `debug` |
| Test-first development | `tdd` |
| Break down epic | `decompose` |
| Strategic planning / roadmap | `roadmap` |

### Available workflows

| Workflow | Stages | Use case |
|---|---|---|
| `simple` | plan → approve-gate → implement → finalize | General feature development |
| `tdd` | design → approve → implement (TDD) → finalize | Test-driven development |
| `debug` | RED → FIX → PROVE | Bug fixing |
| `decompose` | analyze → break down → create backlog | Epic decomposition |
| `roadmap` | refine-roadmap → plan-milestones → create epics | Strategic planning |
| `detect-context` | detect-context | Analyze project stack and gaps |
| `project-setup` | detect stack → registry → docs → knowledge → verify | New project initialization |
| `knowledge-build` | scan → analyze → index → verify | Build code search index |
| `consolidate` | merge feature branches | Branch consolidation |

### Multi-stage execution

Workflows execute as DAGs. Each stage:
1. Spawns an SDK subprocess (`claude --permission-mode bypassPermissions`)
2. Agent executes with crew skills available (dynamic system prompt)
3. Returns structured output (`StageOutput` JSON envelope)
4. Passes artifacts to the next stage via the **Baton** (inter-stage context)

Gates pause execution for approval. Use `--yes` to auto-approve all gates.

## 3. Session Management

```bash
# List sessions
pixl session list
pixl session list --status running
pixl session list --feature feat-003

# Get session details
pixl session get <session-id>

# Cancel a session
pixl session cancel <session-id>

# Resume a stalled or paused session from its saved cursor
pixl session resume <session-id> --yes

# Retry a failed session (resets failed nodes, re-executes)
pixl session retry <session-id> --yes

# Auto-cancel sessions stuck >5 minutes
pixl session cleanup
pixl session cleanup --stale-minutes 10
```

## 4. Monitor & Analytics

### Events

```bash
pixl events                          # all events
pixl events <session-id>             # events for a session
pixl events --type task_completed    # filter by type
pixl event-stats                     # counts by event type
```

### Cost tracking

```bash
pixl cost summary                    # total cost, tokens, top model
pixl cost by-model                   # cost per model
pixl cost by-session                 # cost per session
```

Costs are computed from `pricing.yaml` rates:
- `claude-sonnet-4-6`: $3/$15 per 1M tokens (input/output)
- `claude-opus-4-6`: $15/$75 per 1M tokens
- `claude-haiku-4-5`: $0.80/$4 per 1M tokens

### Knowledge index

```bash
pixl knowledge build                 # index docs
pixl knowledge build --code          # index docs + source code
pixl knowledge build --full          # force full rebuild
pixl knowledge search "auth flow"    # BM25-ranked search
pixl knowledge context "auth" --max-tokens 4000   # build context window
pixl knowledge status                # index stats
```

### Artifacts

```bash
pixl artifact put --name "spec.md" --content "..." --type plan --tags "spec,api"
pixl artifact get --name "spec.md"
pixl artifact list
pixl artifact list --session <session-id>
pixl artifact search --query "auth"
pixl artifact versions <session-id> <path>
```

### State machine

```bash
pixl state show feat-003             # current status + transitions
pixl state graph epic-1              # dependency DAG
pixl state deps feat-003             # check if dependencies met
```

### Workflow templates

```bash
pixl template list                   # all templates
pixl template get <id>               # template details
pixl template create my-wf --file workflow.yaml
pixl template update <id> --file workflow.yaml   # bumps version
pixl template delete <id> --yes
```

## 5. Sandbox Validation

Sandboxes run workflows in isolated Cloudflare containers.

```bash
# Setup
export PIXL_SANDBOX_URL=https://...
export PIXL_SANDBOX_API_KEY=sk-...

# Create
pixl sandbox create my-sandbox --repo-url https://github.com/... --branch main

# Run workflow
pixl sandbox workflow my-sandbox --prompt "Add rate limiting" --yes

# Execute commands
pixl sandbox exec my-sandbox "python -m pytest"

# Sync data back to local DB
pixl sandbox sync my-sandbox

# Export/import sessions
pixl sandbox export-session my-sandbox sess-abc123 > bundle.json
pixl sandbox import-session other-sandbox < bundle.json

# Cleanup
pixl sandbox destroy my-sandbox
```

## 6. Manage Projects

```bash
pixl project list                    # all registered projects
pixl project get <id>                # project details
pixl project delete <id> --yes       # unregister + delete data
```

## 7. Configuration

```bash
pixl config set sandbox_url "https://..."
pixl config get sandbox_url
pixl setup                           # register crew + install companion plugins
pixl setup --skip-plugins            # crew only
```

## Global Flags

```bash
pixl --json <command>                # JSON output (all commands)
pixl --project /path <command>       # target a specific project
```

## Storage Architecture

```
~/.pixl/                            # centralized (all project data)
├── projects.json                   # index: {id → {name, root}}
└── projects/<id>/
    ├── pixl.db                     # SQLite (WAL, FTS5, 40+ tables)
    └── config.json                 # project metadata

~/projects/<name>/                  # project root
├── .pixl/
│   ├── project.json               # marker
│   ├── sdk-stderr.log             # SDK subprocess errors
│   ├── sessions/<id>/             # per-session artifacts + summaries
│   └── workflows/                 # project workflow overrides
└── .claude/
    ├── rules/                     # crew rules: workflow, delegation, enforcement, context (auto-updated by pixl project init)
    ├── settings.local.json        # scoped permissions
    └── memory/                    # cross-session memory (bridged from engine)
        ├── sessions/              # session summaries
        ├── costs.jsonl            # token costs
        └── decisions.jsonl        # decision log
```

**Key principle:** DB is centralized at `~/.pixl/`. Project's `.pixl/` is just context and session working dirs. Crew memory (`.claude/memory/`) is bridged from engine data for hook consumption.

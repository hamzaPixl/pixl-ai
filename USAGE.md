# pixl — Usage Guide (v9.1.0)

How to use pixl for a new project, from install to workflow execution.

---

## 1. Install

```bash
# From source (recommended for development)
git clone <repo> && cd pixl
make setup          # uv sync + register crew plugin with Claude Code

# From PyPI
uv tool install pixl && pixl setup
```

Verify:

```bash
pixl --version      # 9.1.0
pixl --help         # lists all commands
```

---

## 2. Initialize a Project

```bash
cd /path/to/your-project
pixl project init
```

This creates `.pixl/` with a SQLite database (`pixl.db`) that stores features, epics, sessions, artifacts, events, and configuration.

Check it worked:

```bash
pixl project list          # shows your project
pixl --json project list   # JSON output (global --json flag works on any command)
```

---

## 3. Available Workflows

```bash
pixl workflow list
```

Built-in workflows:

| Workflow | Description | Use Case |
|----------|-------------|----------|
| `simple` | Plan → Approve → Implement → Finalize | Single features |
| `tdd` | Design → Approve → TDD Implement → Finalize | Test-driven features |
| `roadmap` | Refine → Plan Milestones → Approve → Materialize | Strategic planning with epics |
| `decompose` | Break epics into features | After roadmap planning |
| `debug` | Diagnose and fix a bug | Bug fixes |

---

## 4. Run a Workflow

### Interactive mode (default — pauses at gates for approval)

```bash
pixl workflow run --workflow simple --prompt "Add user authentication with JWT"
```

The workflow will:
1. Create a feature in the backlog
2. Execute the **plan** stage (LLM generates `plan.md`)
3. Pause at the **approve-plan** gate — you review and approve
4. Execute the **implement** stage
5. Execute the **finalize** stage (self-review + PR creation)

### Autonomous mode (`--yes` — auto-approves all gates)

```bash
pixl workflow run --workflow simple --yes --prompt "Add user authentication with JWT"
```

Gates are approved automatically. Useful for CI, demos, or when you trust the plan stage.

### Simulation mode (no LLM calls — dry run)

```bash
PIXL_ALLOW_SIMULATED_EXECUTION=1 pixl workflow run --workflow simple --yes --prompt "test run"
```

Simulated nodes return stub outputs with `"simulated": true` in the event payload. Useful for testing workflow DAG structure without spending tokens.

### JSON output

```bash
pixl --json workflow run --workflow simple --yes --prompt "Add auth"
```

Returns:

```json
{
  "session_id": "sess-001",
  "feature_id": "feat-001",
  "workflow_id": "simple",
  "status": "completed",
  "steps": 5
}
```

---

## 5. Monitor Execution

### Sessions

```bash
pixl session list                       # all sessions
pixl session list --status running      # active only
pixl session get <session-id>           # full details
```

### Events

```bash
pixl events list                        # all events
pixl events list --session <session-id> # events for a session
pixl event-stats                        # counts by type
```

### Artifacts

```bash
pixl artifact list                              # all artifacts
pixl artifact list --session <session-id>       # per-session
pixl artifact get --name plan.md                # read artifact content
pixl artifact search --query "authentication"   # full-text search
```

### State & Transitions

```bash
pixl state show feat-001       # current state + valid transitions
pixl state show epic-001       # works for any entity type
pixl state deps feat-002       # check if dependencies are met
pixl state graph epic-001      # dependency graph for an epic's features
```

---

## 6. Backlog Management (Python API)

The backlog adapter supports dual-signature updates — pass either a Pydantic model or `(id, **fields)`:

```python
from pixl.storage.backlog_adapter import BacklogStoreAdapter

store = BacklogStoreAdapter(project_path)

# Create
feature = store.add_feature(title="Add auth", description="JWT-based auth")
epic = store.add_epic(title="Auth Epic", original_prompt="Build auth system")
roadmap = store.add_roadmap(title="Q1 Roadmap", original_prompt="Q1 plan")

# Update by ID + fields (lightweight, no model loading required)
store.update_feature("feat-001", branch_name="feat/auth", status="in_progress")
store.update_epic("epic-001", title="Auth & Permissions Epic")
store.update_roadmap("roadmap-001", status="in_progress")

# Update by model (full reconciliation — syncs FKs, notes, feature_ids)
epic.title = "Updated Epic"
epic.feature_ids = ["feat-001", "feat-002"]
store.update_epic(epic)       # reconciles epic_id FK on features

# Status transitions (validates against state machine)
store.update_status("feat-001", FeatureStatus.IN_PROGRESS, note="Starting work")

# Query
features = store.list_all()
features = store.list_by_status(FeatureStatus.IN_PROGRESS)
backlog = store.load()         # full snapshot (features + epics + roadmaps)
```

---

## 7. Configuration

```bash
pixl config get autonomy:feat-001              # check autonomy mode
pixl config set autonomy:feat-001 autopilot    # enable auto-approval ladder
```

Autonomy modes:
- **assist** (default) — always pause at gates for human approval
- **autopilot** — auto-approve gates when confidence threshold is met (based on historical success rate)
- **`--yes` flag** — override, always auto-approve regardless of mode

---

## 8. Crew Plugin (Claude Code)

The crew (`packages/crew/`) is a **Claude Code plugin** — a folder of markdown files (agents, skills, hooks, references) that Claude Code loads at startup. It turns Claude Code into a multi-agent development team.

### How it gets registered

```bash
pixl setup    # registers the crew plugin with Claude Code + installs companion plugins
```

After setup, open Claude Code in any project — agents, skills, and hooks are immediately available.

### Agents

14 specialized agents that Claude delegates to via the `Agent` tool. Each runs at a specific model tier:

| Tier | Agents | Why |
|------|--------|-----|
| **Opus** | orchestrator, architect, tech-lead, security-engineer | High-stakes design and review decisions |
| **Sonnet** | qa-engineer, devops-engineer, product-owner, build-error-resolver | Structured, repetitive work |
| **Haiku** | explorer, onboarding-agent, doc-updater | Fast, cheap read-only exploration |
| **Inherit** | frontend-engineer, backend-engineer, fullstack-engineer | Uses parent context's model |

Example usage in Claude Code:
- "Build me a landing page" → delegates to `frontend-engineer`
- "Review this PR" → delegates to `tech-lead`
- "Where is the auth logic?" → delegates to `explorer`

### Skills (slash commands)

72 slash commands you invoke with `/skill-name` in Claude Code:

| Category | Key skills |
|----------|-----------|
| **Build a website** | `/website`, `/website-project`, `/design-extraction`, `/shadcn-ui`, `/i18n-setup` |
| **Modify a website** | `/website-theme` (colors/fonts), `/website-layout` (sections/grids) |
| **Build backend** | `/ddd-pattern`, `/fastapi-service`, `/pydantic-api-endpoint`, `/saas-microservice` |
| **Project scaffolds** | `/website-project`, `/fullstack-app`, `/admin-dashboard`, `/blog`, `/fastapi-api` |
| **Quality & review** | `/self-review-fix-loop`, `/code-review`, `/cto-review`, `/spec-review`, `/code-reduction` |
| **Testing** | `/test-runner`, `/test-writer`, `/eval-harness`, `/benchmark` |
| **Audits** | `/schema-audit`, `/api-audit`, `/security-scan`, `/seo-audit`, `/dependency-review` |
| **Planning** | `/task-plan`, `/sprint-planning`, `/migration-plan`, `/prd-pipeline` |
| **DevOps** | `/docker-cloudrun`, `/pm2`, `/makefile` |
| **Workflow** | `/claude-md`, `/skill-factory`, `/batch`, `/continuous-learning`, `/client-project-setup` |
| **Intelligence** | `/intel`, `/strategic-intel`, `/vision-advisory` |

### Hooks (automations)

Event-driven hooks run automatically during Claude Code sessions:

| Event | What happens |
|-------|-------------|
| **SessionStart** | Loads last 3 session summaries + recent decisions into context |
| **PreCompact** | Saves session state before context window compacts |
| **Stop** | Captures git diff stats, modified files, token costs |
| **PostToolUse** | Quality checks (formatting, TDD, typecheck — depends on profile) |

Control hook behavior with profiles:

```bash
PIXL_HOOK_PROFILE=minimal claude     # only critical hooks (fast exploratory sessions)
PIXL_HOOK_PROFILE=standard claude    # critical + quality (default)
PIXL_HOOK_PROFILE=strict claude      # everything including typecheck
PIXL_DISABLED_HOOKS=typecheck claude # disable specific hooks
```

### Cross-session memory

Hooks persist state across sessions in `.claude/memory/`:

```
.claude/memory/
├── decisions.jsonl    # architectural decisions (auto-loaded on session start)
├── instincts.jsonl    # learned patterns from /continuous-learning
├── costs.jsonl        # per-session token costs
└── sessions/          # session summaries (last 3 loaded on start)
```

When the pixl CLI is installed, hooks use `.pixl/pixl.db` (SQLite) as primary storage. Memory files are the fallback.

### Studio stacks (scaffolding)

Two production-ready template stacks in `studio/stacks/`:

| Stack | What you get | Skill |
|-------|-------------|-------|
| **nextjs** | 75+ templates, 12 design archetypes, i18n, blog, Stripe, Supabase | `/website` |
| **saas** | 18 foundation packages (identity, tenancy, RBAC, audit, outbox, DDD) | `/saas-microservice` |

Scaffold interactively:

```bash
make scaffold STACK=nextjs
```

### Companion plugins

`pixl setup` also installs 11 companion plugins:

| Category | Plugins |
|----------|---------|
| **LSP** | `typescript-lsp`, `pyright-lsp`, `swift-lsp` — go-to-definition, find-references, type info |
| **Security** | `supply-chain-risk-auditor`, `variant-analysis`, `property-based-testing`, `static-analysis`, `semgrep-rule-creator` (Trail of Bits) |
| **Utilities** | `ralph-loop` (autonomous loops), `commit-commands` (`/amend`, `/fixup`, `/squash`), `playground` (interactive HTML) |

Skip categories during setup:

```bash
pixl setup --skip-lsp --skip-security --skip-plugins
```

### Project routing

| You want to... | Use |
|----------------|-----|
| Build a new website | `/website` or `/website-project` |
| Build a SaaS backend | Orchestrator → `/saas-microservice` |
| Build a fullstack app | Orchestrator → `/fullstack-app` |
| Add an endpoint to existing service | Backend engineer (follows existing patterns) |
| Refactor to DDD | `/ddd-pattern` |
| Review code quality | `/self-review-fix-loop` or `/cto-review` |
| Review a PR before merge | `/code-review` |
| Plan a sprint | `/task-plan` + `/sprint-planning` |

---

## 9. Common Recipes

### Build a feature end-to-end

```bash
pixl project init
pixl workflow run --workflow simple --prompt "Add Stripe payment integration"
# Review plan.md at the gate, approve, wait for implementation
pixl session list   # check status
```

### Plan a roadmap, then execute

```bash
pixl workflow run --workflow roadmap --prompt "Build a SaaS billing platform"
# Approve roadmap → epics are created automatically
pixl workflow run --workflow decompose --prompt "Decompose epic-001 into features"
# Then run simple/tdd workflow per feature
```

### CI/demo mode (fully autonomous)

```bash
pixl workflow run --workflow simple --yes --prompt "Add health check endpoint"
```

### Dry run (test workflow DAG without LLM)

```bash
PIXL_ALLOW_SIMULATED_EXECUTION=1 pixl workflow run --workflow tdd --yes --prompt "test"
```

Simulated events will show:
```json
{
  "final_event_payload": {
    "simulated": true,
    "output": "[SIMULATED] Output for node: plan"
  }
}
```

### Real-time event streaming (NDJSON)

```bash
pixl --json workflow run --workflow simple --yes --prompt "Add auth"
```

With `--json`, events stream as newline-delimited JSON in real-time:

```json
{"event_type": "node_started", "session_id": "sess-001", "node_id": "plan", "timestamp": "..."}
{"event_type": "node_completed", "session_id": "sess-001", "node_id": "plan", "timestamp": "..."}
```

---

## 10. Sandbox Execution

Run workflows in isolated Cloudflare containers with their own pixl stack.

### Configure sandbox access

```bash
pixl config set sandbox.url https://pixl-sandbox.account.workers.dev
pixl config set sandbox.api_key <key>

# Or use env vars
export PIXL_SANDBOX_URL=https://pixl-sandbox.account.workers.dev
export PIXL_SANDBOX_JWT_SECRET=<secret>   # preferred over static API key
```

### Create and run

```bash
# Create sandbox (clones repo, sets env, inits pixl)
pixl sandbox create acme-landing \
  --repo-url https://github.com/user/repo \
  --env GITHUB_TOKEN=ghp_xxx

# Run workflow inside sandbox
pixl sandbox workflow acme-landing --prompt "Build a landing page" --yes

# Stream workflow execution (SSE)
pixl sandbox workflow acme-landing --prompt "Build auth" --stream
```

### Monitor

```bash
pixl sandbox status acme-landing        # versions, git info, project state
pixl sandbox events acme-landing        # workflow events from container
pixl sandbox sessions acme-landing      # workflow sessions
```

### Session continuity (fork-from)

Bootstrap a new sandbox from an existing session:

```bash
# Export session from source, import into new sandbox
pixl sandbox create new-project --fork-from acme-landing:sess-001
```

### Sync and cleanup

```bash
pixl sandbox sync acme-landing          # pull events/sessions/artifacts to local DB
pixl sandbox destroy acme-landing       # destroy container
```

---

## 11. Cost Analytics

Track token usage and costs across models and sessions.

```bash
pixl cost summary                       # total cost, queries, top model
pixl cost by-model                      # breakdown by model name
pixl cost by-session                    # cost per session (top 20)
pixl --json cost summary                # JSON output
```

---

## 12. Workflow Templates

Manage DB-backed workflow templates (alongside filesystem YAML).

```bash
pixl template list                      # all templates (DB + filesystem)
pixl template get <id>                  # template details
pixl template create --name "custom" --yaml workflow.yaml
pixl template update <id> --description "Updated"
pixl template delete <id>
```

# pixl — Usage Guide (v8.0.0)

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
pixl --version      # 8.0.0
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

After `pixl setup`, the crew plugin adds agents and skills to Claude Code:

```bash
# Agents (use via Claude Code Agent tool)
orchestrator, architect, frontend-engineer, backend-engineer,
fullstack-engineer, qa-engineer, devops-engineer, tech-lead,
product-owner, security-engineer, explorer, build-error-resolver

# Skills (invoke via / commands in Claude Code)
/website          # build a full Next.js website
/task-plan        # break down a feature into tasks
/self-review-fix-loop  # iterative quality improvement
/code-review      # multi-agent PR review
/test-runner      # smart test execution
# ... 71 skills total (see pixl CLAUDE.md for full list)
```

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

# Scenario: PRD to Code with pixl

End-to-end walkthrough — from a PRD to a running application using the pixl CLI.

## Overview

This scenario demonstrates building a note-taking app from a PRD using pixl's workflow engine:

1. Create project and write PRD
2. Run detect-context workflow (analyze the PRD)
3. Run roadmap workflow (plan milestones)
4. Run simple workflow (build the database layer)
5. Monitor everything: sessions, costs, events, artifacts, knowledge
6. Resume/retry failed sessions

## Step 1: Create the Project

```bash
pixl project new notepad --path ~/code --no-setup
cd ~/code/notepad
```

This creates:
- `.pixl/` — pixl infrastructure (project.json, sessions/, sdk-stderr.log)
- `.claude/` — crew rules, permissions, memory directory
- `CLAUDE.md` — project instructions with 14 agents and 75 skills listed

## Step 2: Write the PRD

Create `PRD.md` with features:
- F1: Database & Models (SQLAlchemy, Alembic)
- F2: Auth API (JWT, bcrypt)
- F3: Notes CRUD API (paginated, auth-protected)
- F4: React Frontend (Vite, TailwindCSS)
- F5: Landing Page (hero, features, CTA)

```bash
git add PRD.md && git commit -m "docs: add PRD"
pixl knowledge build --full
```

## Step 3: Run Parallel Workflows

Launch 3 workflows simultaneously:

```bash
# Terminal 1: Analyze the PRD
pixl --json workflow run --workflow detect-context \
  --prompt "Analyze PRD.md — tech stack, features, gaps" --yes

# Terminal 2: Plan the roadmap
pixl --json workflow run --workflow roadmap \
  --prompt "Plan roadmap: DB, auth, CRUD, frontend, landing page" --yes

# Terminal 3: Build the database layer
pixl --json workflow run --workflow simple \
  --prompt "Build F1: Database models, async engine, Alembic migrations" --yes
```

### What happens during execution

The `simple` workflow executes 3 stages:

```
plan (60s) → approve-plan gate (auto) → implement (2-5 min)
```

1. **Plan stage**: Agent reads PRD, explores project, writes `plan.md` artifact
2. **Gate**: Plan artifact is frozen (SHA256 locked), gate auto-approved with `--yes`
3. **Implement stage**: Agent creates files per the plan — models, DB config, migrations, tests

The engine:
- Reconnects the SDK client between stages (fresh subprocess per stage)
- Emits heartbeat events on every tool call (prevents false "stalled" detection)
- Records costs per model (pricing from `pricing.yaml`)
- Bridges session summaries to `.claude/memory/sessions/`

## Step 4: Monitor Progress

```bash
# Sessions
pixl session list
# ┃ sess-abc123 │ feat-003 │ running   │ ... │ ... ┃
# ┃ sess-def456 │ feat-001 │ completed │ ... │ ... ┃

# Events
pixl event-stats
# sdk_tool_call_started: 35
# task_completed: 3
# gate_approved: 1
# artifact_frozen: 1

# Costs
pixl cost summary
# total_cost_usd: $0.176
# top_model: anthropic/claude-sonnet-4-6

pixl cost by-session
# sess-abc123 │ 2 queries │ 11,723 output │ $0.176

# Artifacts
pixl artifact list
# plan.md                    │ sess-abc123
# progress-detect-context.md │ sess-def456
# roadmap-brief.md           │ sess-ghi789

# Knowledge
pixl knowledge search "auth endpoint"
```

## Step 5: Verify Generated Code

After the implement stage completes:

```bash
# Check files created
find . -name '*.py' | sort
# ./src/db.py
# ./src/models/note.py
# ./src/models/user.py
# ./tests/conftest.py
# ./tests/test_models.py
# ./alembic/env.py
# ./alembic/versions/abc123_baseline.py

# Check git
git log --oneline
# abc1234 feat: add database layer (models, migrations, tests)
# def5678 docs: add PRD
# ghi9012 init: notepad — pixl project with crew

# Run tests
pip install -e ".[dev]"
pytest tests/ -v
```

## Step 6: Handle Failures

### Stalled sessions

Sessions that run longer than expected stay "running" (heartbeat keeps them alive).
If a session is truly stuck:

```bash
# Auto-cancel sessions idle >5 minutes
pixl session cleanup

# Or cancel manually
pixl session cancel <session-id>
```

### Resume from checkpoint

```bash
# Resume a stalled/paused session from its cursor position
pixl session resume <session-id> --yes
```

### Retry failed sessions

```bash
# Reset failed nodes and re-execute
pixl session retry <session-id> --yes
```

### Debug SDK errors

```bash
# Check subprocess error log
cat .pixl/sdk-stderr.log

# Check event details
pixl events <session-id> --type error --limit 5
```

## Step 7: Check Crew Memory

After workflows complete, data is bridged to crew memory:

```bash
# Session summaries (loaded by SessionStart hook)
ls .claude/memory/sessions/
# 2026-03-27-02-42.md

# Cost log
cat .claude/memory/costs.jsonl
# {"date":"2026-03-27T02:48:00","session_id":"sess-abc","cost_usd":0.176,"model":"anthropic/claude-sonnet-4-6"}
```

## Expected Results

| Metric | Typical Value |
|--------|---------------|
| Detect-context | Completes in 30-60s, 1 stage |
| Roadmap | 1st stage completes in 60-90s |
| Simple (plan + implement) | 3-6 min total, creates 10-15 files |
| Cost per workflow | $0.04-0.18 (sonnet-4-6) |
| SDK tool calls | 15-85 per workflow |
| Files generated | Models, DB config, migrations, tests, health endpoint |
| Git commits | Auto-committed by implement stage |

## Architecture Diagram

```
PRD.md
  ↓
pixl workflow run --workflow simple --prompt "..." --yes
  ↓
Engine: classify_prompt_fast() → WorkflowTemplate → WorkflowSession
  ↓
GraphExecutor.step() loop (up to 100 steps)
  ↓
┌─────────────────────────────────────────────────────┐
│ Stage: plan                                         │
│  → OrchestratorCore.query_with_streaming()          │
│  → ClaudeSDKClient.connect() → subprocess (claude)  │
│  → Agent reads PRD, writes plan.md artifact         │
│  → StageOutput validated, contract passed           │
│  → Client disconnected (fresh subprocess next)      │
└─────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────┐
│ Gate: approve-plan                                  │
│  → plan.md frozen (SHA256 locked)                   │
│  → Auto-approved (--yes flag)                       │
└─────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────┐
│ Stage: implement                                    │
│  → Fresh SDK subprocess (reconnected)               │
│  → Agent creates files per plan                     │
│  → Heartbeat: last_updated_at refreshed per event   │
│  → Git commit: "feat: add database layer"           │
│  → StageOutput validated                            │
└─────────────────────────────────────────────────────┘
  ↓
Session completed → summary bridged to .claude/memory/
                  → costs bridged to .claude/memory/costs.jsonl
                  → SDK subprocess killed (cleanup)
```

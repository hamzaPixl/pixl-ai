#!/bin/bash
set -euo pipefail

# run-prd.sh — Autonomous PRD-to-production multi-session pipeline
#
# Usage:
#   ./run-prd.sh [OPTIONS]
#
# Options:
#   --prd <path>        Path to PRD file (default: .context/prd.md)
#   --sprints <N>       Max sprints to execute (default: 10)
#   --skip-planning     Skip Phase 1 (resume from existing plan)
#   --max-budget <N>    Max budget in USD per headless session (default: 5.00)
#   --dry-run           Print commands without executing
#   --help              Show this help message

# ─── Defaults ──────────────────────────────────────────────────────────────────

PRD_PATH=".context/prd.md"
MAX_SPRINTS=10
MAX_BUDGET="5.00"
SKIP_PLANNING=false
DRY_RUN=false

# ─── Parse Arguments ──────────────────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
  case $1 in
    --prd)        PRD_PATH="$2"; shift 2 ;;
    --sprints)    MAX_SPRINTS="$2"; shift 2 ;;
    --max-budget) MAX_BUDGET="$2"; shift 2 ;;
    --skip-planning) SKIP_PLANNING=true; shift ;;
    --dry-run)    DRY_RUN=true; shift ;;
    --help)
      head -12 "$0" | tail -10
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# ─── Project Root ────────────────────────────────────────────────────────────

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$PROJECT_ROOT"

# ─── Validation ───────────────────────────────────────────────────────────────

if [[ ! -f "$PRD_PATH" ]] && [[ "$SKIP_PLANNING" == "false" ]]; then
  echo "Error: PRD not found at $PRD_PATH"
  echo "Place your PRD at .context/prd.md or use --prd <path>"
  exit 1
fi

if [[ "$SKIP_PLANNING" == "true" ]]; then
  if [[ ! -f ".context/task-state.json" ]] || [[ ! -f ".context/sprint-plan.md" ]]; then
    echo "Error: --skip-planning requires existing planning outputs."
    echo "Missing: .context/task-state.json and/or .context/sprint-plan.md"
    echo "Run planning phase first (remove --skip-planning)."
    exit 1
  fi
fi

if ! command -v claude &>/dev/null; then
  echo "Error: claude CLI not found. Install Claude Code first."
  exit 1
fi

if ! command -v jq &>/dev/null; then
  echo "Warning: jq not found. Progress tracking will be limited."
fi

# ─── Helpers ──────────────────────────────────────────────────────────────────

PIPELINE_STATE=".context/pipeline-state.json"

run_claude() {
  local description="$1"
  local prompt="$2"
  local budget="${3:-$MAX_BUDGET}"

  echo ""
  echo "─── $description ───"
  echo "  Max budget: \$$budget"
  echo ""

  if [[ "$DRY_RUN" == "true" ]]; then
    echo "  [DRY RUN] claude -p \"${prompt:0:80}...\""
    return 0
  fi

  claude -p "$prompt" --max-budget-usd "$budget" || {
    echo "Warning: Session exited with non-zero status. Checking state..."
    return 0
  }
}

get_pending_count() {
  if [[ -f ".context/task-state.json" ]] && command -v jq &>/dev/null; then
    jq '[.tasks[] | select(.status != "completed")] | length' .context/task-state.json 2>/dev/null || echo "?"
  else
    echo "?"
  fi
}

get_current_phase() {
  if [[ -f "$PIPELINE_STATE" ]] && command -v jq &>/dev/null; then
    jq -r '.current_phase // "unknown"' "$PIPELINE_STATE" 2>/dev/null || echo "unknown"
  else
    echo "unknown"
  fi
}

# ─── Setup ────────────────────────────────────────────────────────────────────

mkdir -p .context .context/spec

if [[ "$SKIP_PLANNING" == "false" ]] && [[ "$PRD_PATH" != ".context/prd.md" ]]; then
  cp "$PRD_PATH" .context/prd.md
  echo "PRD copied to .context/prd.md"
fi

echo "=========================================="
echo "  PRD-to-Production Pipeline"
echo "=========================================="
echo "  PRD: $PRD_PATH"
echo "  Max sprints: $MAX_SPRINTS"
echo "  Max budget/session: \$$MAX_BUDGET"
echo "=========================================="

# ─── Phase 1: Planning (Interactive) ─────────────────────────────────────────

if [[ "$SKIP_PLANNING" == "false" ]]; then
  echo ""
  echo "=== Phase 1: Planning (INTERACTIVE) ==="
  echo "This phase requires your review. An interactive Claude session will open."
  echo "Press Enter to start, or Ctrl+C to cancel..."
  read -r

  if [[ "$DRY_RUN" == "false" ]]; then
    claude --resume "prd-pipeline-planning" -p "$(cat <<'EOF'
Read the PRD at .context/prd.md and execute the /prd-pipeline skill Phase 1:

1. /spec-review .context/prd.md
2. /task-plan .context/prd.md
3. /sprint-planning on the task plan
4. Spawn architect agent for architecture decisions → .context/architecture-packet.json
5. /task-persist save
6. /continuous-learning record — log key decisions

Present the plan for my review before proceeding.
EOF
    )"
  else
    echo "[DRY RUN] Interactive planning session"
  fi
fi

# ─── Phase 2: Foundation Sprint ──────────────────────────────────────────────

if [[ ! -f ".context/task-state.json" ]]; then
  echo "Error: No task state found. Run planning phase first (remove --skip-planning)."
  exit 1
fi

echo ""
echo "=== Phase 2: Foundation Sprint ==="

run_claude "Foundation Sprint" "$(cat <<'EOF'
You are continuing the /prd-pipeline skill — Phase 2 (Foundation Sprint).

1. Load task state: read .context/task-state.json and .context/pipeline-state.json
2. Read .context/architecture-packet.json and .context/sprint-plan.md
3. If not on a feature branch, run: git checkout -b feat/prd-implementation
4. Execute Sprint 1 tasks SEQUENTIALLY (foundation/scaffolding touches shared files)
5. For each task: implement → run tests → commit with conventional commit message
6. After all Sprint 1 tasks: run full test suite
7. Update .context/pipeline-state.json: set foundation to completed
8. Save: write updated task-state.json with completed tasks
EOF
)"

# ─── Phase 3-5: Sprint Loop ─────────────────────────────────────────────────

for SPRINT in $(seq 2 "$MAX_SPRINTS"); do
  PENDING=$(get_pending_count)

  if [[ "$PENDING" == "0" ]]; then
    echo ""
    echo "All tasks completed!"
    break
  fi
  if [[ "$PENDING" == "?" ]]; then
    echo "Warning: Cannot determine task count (jq missing or task-state.json not found)."
    echo "Continuing sprint $SPRINT. Use Ctrl+C to stop if tasks are done."
  fi

  echo ""
  echo "=== Sprint $SPRINT ($PENDING tasks remaining) ==="

  # Implementation
  run_claude "Sprint $SPRINT — Implementation" "$(cat <<EOF
You are continuing the /prd-pipeline skill — Phase 3 (Implementation Sprint $SPRINT).

1. Load state: read .context/task-state.json, .context/pipeline-state.json
2. Read .context/architecture-packet.json, .context/spec/requirements.json
3. Identify Sprint $SPRINT tasks from .context/sprint-plan.md
4. For parallel tasks (non-overlapping files): use /batch with worktree isolation
5. For sequential tasks: execute in dependency order
6. After each task: run tests, typecheck, commit
7. After all tasks: run full test suite
8. Update .context/pipeline-state.json: increment sprints_completed
9. Save updated task-state.json
EOF
  )"

  # Quality gate
  run_claude "Sprint $SPRINT — Quality Gate" "$(cat <<EOF
You are continuing the /prd-pipeline skill — Phase 4 (Quality Gate for Sprint $SPRINT).

1. Load state: read .context/task-state.json, .context/pipeline-state.json
2. Run /self-review-fix-loop on changes since last sprint
3. Run /spec-review rescan — check coverage against requirements
4. If gaps found: run /task-plan in drift mode to create new tasks
5. Save updated task-state.json and pipeline-state.json
EOF
  )"

  # PR (only if there are committed changes)
  run_claude "Sprint $SPRINT — PR" "$(cat <<EOF
You are continuing the /prd-pipeline skill — Phase 5 (PR Creation for Sprint $SPRINT).

1. Push the branch: git push -u origin feat/prd-implementation
2. Create or update PR using gh pr create (or gh pr edit if PR exists)
   - Title: Sprint $SPRINT implementation
   - Body: coverage percentage from .context/spec/ latest coverage file, tasks completed
3. Update .context/pipeline-state.json
EOF
  )"
done

# ─── Phase 6: Final Validation ───────────────────────────────────────────────

echo ""
echo "=== Phase 6: Final Validation ==="

run_claude "Final Validation" "$(cat <<'EOF'
You are continuing the /prd-pipeline skill — Phase 6 (Final Validation).

1. Run /spec-review rescan — report final coverage percentage
2. Run /cto-review — architectural assessment
3. Run /security-scan — OWASP check
4. Run /dependency-review — CVE/license audit
5. Run full build + test suite
6. Run /continuous-learning observe — extract project patterns
7. Update .context/pipeline-state.json: set finalization to completed

Output a final report with:
- Coverage percentage
- Quality assessment summary
- Security findings
- Total sprints, commits, and tasks completed
EOF
)"

# ─── Done ─────────────────────────────────────────────────────────────────────

echo ""
echo "=========================================="
echo "  Pipeline Complete"
echo "=========================================="

if [[ -f "$PIPELINE_STATE" ]] && command -v jq &>/dev/null; then
  echo "  Phase: $(jq -r '.current_phase // "unknown"' "$PIPELINE_STATE")"
  echo "  Sprints: $(jq -r '.sprints_completed // 0' "$PIPELINE_STATE")/$(jq -r '.total_sprints // "?"' "$PIPELINE_STATE")"
  echo "  Coverage: $(jq -r '.coverage_percentage // "?"' "$PIPELINE_STATE")%"
fi

echo ""
echo "Review the PR and merge when ready."

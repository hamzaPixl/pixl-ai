#!/bin/bash
set -euo pipefail

# SessionStart hook — injects operational guidelines + project context into every session.
# stdout → system-reminder shown to Claude.

# ─── Part 1: Static Operational Guidelines ───────────────────────────────────

cat << 'GUIDELINES'
## pixl-crew Operational Guidelines

### When To Use Each Building Block
| Building Block | When to Use |
|---|---|
| Skills (`/skill`) | Stored workflows — always prefer over ad-hoc prompts |
| Agents (subagents) | Parallel execution, isolated heavy exploration |
| Hooks | Deterministic automations triggered by events |
| References | Shared domain knowledge auto-loaded via CLAUDE.md |

### Operational Rules
- **Explore → Plan → Implement → Commit**: Use Plan Mode for multi-file changes; skip for single-file fixes
- **Verification first**: Always provide tests, screenshots, or expected output so Claude can self-check
- **Context hygiene**: `/clear` between unrelated tasks; use subagents for heavy exploration
- **Scope investigations**: Don't read hundreds of files — use explorer agent or scoped subagents
- **Prefer CLI tools**: Use `gh` for GitHub, `bun`/`npm` for packages
- **Skills over ad-hoc prompts**: If a skill exists for the task, invoke it rather than describing the workflow manually
- **Minimal changes**: Only modify what's requested — don't add docstrings, refactor surroundings, or over-engineer
- **Explore before building**: When asked to build a new project, service, or feature set, FIRST scan the plugin's skills/ and studio/stacks/ directories to find relevant scaffolds, templates, and workflows. Never build from scratch what the plugin already provides.

### Self-Improvement Rule
When you discover a repeatable pattern or fix during a session:
1. Check if an existing skill or reference already covers it
2. If not, propose updating the relevant skill or creating a new one via `/skill-factory`
3. Never silently work around a skill limitation — fix the skill for next time
GUIDELINES

# ─── Part 2: Dynamic Project Detection ───────────────────────────────────────

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
cd "$PROJECT_DIR" 2>/dev/null || exit 0

PROJECT_NAME="$(basename "$PROJECT_DIR")"

# Tech stack detection
STACK=()
[[ -f "package.json" ]] && STACK+=("Node.js")
[[ -f "tsconfig.json" ]] && STACK+=("TypeScript")
[[ -f "next.config.js" || -f "next.config.mjs" || -f "next.config.ts" ]] && STACK+=("Next.js")
[[ -f "pyproject.toml" || -f "setup.py" || -f "requirements.txt" ]] && STACK+=("Python")
[[ -f "go.mod" ]] && STACK+=("Go")
[[ -f "Cargo.toml" ]] && STACK+=("Rust")

# Package manager detection
PKG_MANAGER="unknown"
if [[ -f "bun.lockb" || -f "bun.lock" ]]; then PKG_MANAGER="bun"
elif [[ -f "pnpm-lock.yaml" ]]; then PKG_MANAGER="pnpm"
elif [[ -f "yarn.lock" ]]; then PKG_MANAGER="yarn"
elif [[ -f "package-lock.json" ]]; then PKG_MANAGER="npm"
fi

# Monorepo detection
MONOREPO=""
if [[ -f "lerna.json" ]]; then MONOREPO="lerna"
elif [[ -f "turbo.json" ]]; then MONOREPO="turborepo"
elif [[ -f "pnpm-workspace.yaml" ]]; then MONOREPO="pnpm workspaces"
elif [[ -f "package.json" ]] && grep -q '"workspaces"' package.json 2>/dev/null; then MONOREPO="npm/yarn workspaces"
fi

# Key config files
CONFIGS=()
[[ -f "Dockerfile" || -f "docker-compose.yml" || -f "docker-compose.yaml" ]] && CONFIGS+=("Docker")
[[ -d ".github/workflows" ]] && CONFIGS+=("GitHub Actions")
[[ -f "prisma/schema.prisma" ]] && CONFIGS+=("Prisma")
[[ -f ".env" || -f ".env.local" ]] && CONFIGS+=(".env")
[[ -f "Makefile" ]] && CONFIGS+=("Makefile")
[[ -f "vitest.config.ts" || -f "jest.config.ts" || -f "jest.config.js" ]] && CONFIGS+=("Tests")

# CLAUDE.md presence
HAS_CLAUDE_MD="no"
[[ -f "CLAUDE.md" ]] && HAS_CLAUDE_MD="yes"

# Output project summary
echo ""
echo "## Current Project Context"
echo "- **Project**: $PROJECT_NAME"

if [[ ${#STACK[@]} -gt 0 ]]; then
  echo "- **Stack**: $(IFS=', '; echo "${STACK[*]}")"
fi

if [[ "$PKG_MANAGER" != "unknown" ]]; then
  echo "- **Package manager**: $PKG_MANAGER"
fi

if [[ -n "$MONOREPO" ]]; then
  echo "- **Monorepo**: $MONOREPO"
fi

if [[ ${#CONFIGS[@]} -gt 0 ]]; then
  echo "- **Key configs**: $(IFS=', '; echo "${CONFIGS[*]}")"
fi

echo "- **CLAUDE.md**: $HAS_CLAUDE_MD"

# Reset session-scoped counter (prevent leak across sessions)
rm -f "$PROJECT_DIR/.claude/memory/.session-tool-count" 2>/dev/null || true

# ─── Part 3: Memory Context Injection ─────────────────────────────────────

# Pixl detection (auto-inits .pixl/ if needed)
_PIXL_AVAILABLE=false
if command -v pixl &>/dev/null; then
  _PIXL_AVAILABLE=true
  if [ ! -d "$PROJECT_DIR/.pixl" ]; then
    pixl --project "$PROJECT_DIR" project init 2>/dev/null || true
  fi
fi

MEMORY_DIR="$PROJECT_DIR/.claude/memory"

if $_PIXL_AVAILABLE; then
  # Read last 3 session summaries from pixl DB
  RECENT_SUMMARIES=$(pixl --json artifact search --query "session-summary" --type "session_summary" --limit 3 2>/dev/null || echo '[]')
  if [[ "$RECENT_SUMMARIES" != "[]" ]] && echo "$RECENT_SUMMARIES" | jq -e 'length > 0' &>/dev/null; then
    echo ""
    echo "### Recent Session Context"
    echo "$RECENT_SUMMARIES" | jq -r '.[].content // empty' 2>/dev/null | head -240
  fi

  # Read last 10 decisions from pixl DB
  RECENT_DECISIONS=$(pixl --json artifact search --query "decision" --type "decision" --limit 10 2>/dev/null || echo '[]')
  if [[ "$RECENT_DECISIONS" != "[]" ]] && echo "$RECENT_DECISIONS" | jq -e 'length > 0' &>/dev/null; then
    echo ""
    echo "### Recent Decisions"
    echo '```json'
    echo "$RECENT_DECISIONS" | jq -r '.[].content // empty' 2>/dev/null
    echo '```'
  fi
else
  # Fallback: file-based memory
  if [[ -d "$MEMORY_DIR/sessions" ]]; then
    recent_sessions=$(find "$MEMORY_DIR/sessions" -maxdepth 1 -name '*.md' -print0 2>/dev/null | xargs -0 ls -t 2>/dev/null | head -3)
    if [[ -n "$recent_sessions" ]]; then
      echo ""
      echo "### Recent Session Context"
      for session_file in $recent_sessions; do
        echo ""
        echo "#### $(basename "$session_file" .md)"
        head -80 "$session_file"
      done
    fi

    if [[ -f "$MEMORY_DIR/decisions.jsonl" ]]; then
      recent_decisions=$(tail -10 "$MEMORY_DIR/decisions.jsonl" 2>/dev/null)
      if [[ -n "$recent_decisions" ]]; then
        echo ""
        echo "### Recent Decisions"
        echo '```jsonl'
        echo "$recent_decisions"
        echo '```'
      fi
    fi
  fi
fi

# ─── Part 4: Task State Reminder ─────────────────────────────────────────

TASK_STATE="$PROJECT_DIR/.context/task-state.json"
if [[ -f "$TASK_STATE" ]]; then
  echo ""
  echo "### Pending Task State"
  echo "A task state file exists at \`.context/task-state.json\`. Use \`/task-persist\` to reload tasks from the previous session."
fi

# ─── Part 4.5: Spec Review Status ───────────────────────────────────────────

SPEC_DIR="$PROJECT_DIR/.context/spec"
if [[ -d "$SPEC_DIR" && -f "$SPEC_DIR/requirements.json" ]]; then
  LATEST=$(ls -t "$SPEC_DIR"/coverage-*.json 2>/dev/null | head -1)
  if [[ -n "$LATEST" ]] && command -v jq &>/dev/null; then
    COV=$(jq -r '.coverage_percentage // "?"' "$LATEST")
    MISS=$(jq -r '.missing // "?"' "$LATEST")
    echo ""
    echo "### Spec Review Status"
    echo "- **Coverage**: ${COV}% | **Missing**: ${MISS}"
    echo "- Run \`/spec-review rescan\` to update."
  fi
fi

# ─── Part 5: Synq Knowledge Index ───────────────────────────────────────────

# If pixl is available, ensure knowledge index is fresh
if $_PIXL_AVAILABLE; then
  timeout 30 pixl knowledge build --code 2>/dev/null &  # Background, non-blocking, 30s max
fi

# ─── Part 6: Workflow Context ─────────────────────────────────────────
if [ -n "${PIXL_SESSION_ID:-}" ]; then
  echo ""
  echo "## Workflow Context"
  echo "You are executing inside a pixl workflow stage."
  echo "- **Session**: ${PIXL_SESSION_ID}"
  echo "- **Stage**: ${PIXL_STAGE_ID:-unknown}"
  echo ""
  echo "### Persistence Rules"
  echo "- Register significant outputs: \`pixl artifact put --name <name> --content \"...\"\`"
  echo "- Get code context before implementing: \`pixl knowledge context \"<query>\" --max-tokens 4000\`"
  echo "- Log decisions: \`pixl artifact put --name decision-<topic> --type decision --content '{...}'\`"
fi

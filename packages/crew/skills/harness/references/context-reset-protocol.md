# Context Reset Protocol

How the harness handles context resets between iterations.

## The Problem

Long-running agentic sessions degrade as context windows fill. Two failure modes:

1. **Context anxiety** -- models prematurely conclude work as context fills, rushing to "finish" before the window runs out.
2. **Quality degradation** -- accumulated noise (old reasoning, superseded plans, stale critique) reduces output quality with each iteration.

## The Engine's Built-In Solution

The pixl engine solves this through its workflow architecture:

- Each stage (plan, generate, evaluate, score-gate) runs as a **separate agent invocation** with a fresh context window.
- Stages share state ONLY through the **Baton** -- a structured handoff packet (`pixl.models.baton.Baton`).
- No raw conversation history crosses stage boundaries.
- Every stage transition is a natural context reset.

## What the Baton Carries Between Iterations

When the score-gate fails and the loop back-edge triggers, the generator receives:

| Baton Field | Content | Purpose |
|---|---|---|
| `goal` | Product description (unchanged) | Anchors the agent to the original objective |
| `quality_signals` | Scores from the evaluator | Shows what needs improvement (numeric) |
| `stage_hints["generate"]` | Detailed critique with specific fixes | Injected by score-gate hook on failure |
| `current_state` | Progress summary (3-8 bullets) | What the generator accomplished last run |
| `work_scope` | List of files created/modified | Paths only, not content |
| `decision_log` | Key decisions across iterations (last 5) | Prevents re-litigating settled choices |
| `acceptance` | Testable success criteria from planner | Defines the finish line |

## What Gets Discarded

- Full conversation history from previous iterations
- Intermediate thoughts and reasoning chains
- Raw file contents (only paths survive in `work_scope`)
- Previous critique details (only the latest critique lives in `stage_hints`)
- Stale `open_questions` that were resolved

This is deliberate. The generator starts each iteration with a clean context containing only the structured summary of what matters.

## Comparison with Manual Approaches

| Manual context reset | pixl engine |
|---|---|
| Custom serialization of state between iterations | Baton model with `apply_patch()` (JSON merge patch) |
| Orchestration code to manage reset timing | Built into DAG executor -- each node is a fresh agent |
| Risk of forgetting to reset | Automatic -- impossible to leak context across stages |
| Latency from teardown/rebuild | Minimal -- just baton deserialization |

## For the Fallback Path (No Engine)

When running the loop via crew subagents (no pixl CLI), context resets are achieved by:

1. Each iteration spawns a **new subagent** (fresh context window).
2. The subagent receives a **context packet** with scores, critique, and file paths.
3. The context packet follows the crew's `references/orchestration/context-packet.md` format (type: `review`, payload contains findings and fix directions).

The key insight: whether using the engine or crew subagents, the mechanism is the same -- new agent invocation with structured state, no conversation history carryover.

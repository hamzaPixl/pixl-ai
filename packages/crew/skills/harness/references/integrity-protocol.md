# Integrity Protocol

Rules for honest, evidence-based engineering. LLM agents systematically take shortcuts when stuck — shipping hacky workarounds to avoid reporting failure. This protocol counteracts that bias.

## Part 1: No Hacking — Quality Over Completion

### The 5 Rules

#### 1. Never ship a hack to claim "done"

A hacky workaround that passes the evaluator is worse than an honest failure report. Hacks create invisible debt that compounds across iterations. If you cannot solve the problem correctly, stop and escalate — do not patch over it.

Examples of hacks to reject:
- Hardcoded values that should be dynamic (`if (id === "abc123")`)
- `!important` overrides to force CSS instead of fixing the cascade
- Empty catch blocks that swallow errors (`catch (e) {}`)
- Disabling validation or type checks to make code compile
- Commented-out code with `// TODO: fix later`
- Duplicating code instead of fixing the shared abstraction
- Mock data presented as real functionality

#### 2. Fix the root cause, not the symptom

When a test fails, a build breaks, or a feature doesn't work — the fix must address the root cause. Suppressing the error, skipping the test, or working around the symptom is not a fix. If you find yourself writing code that "avoids triggering" the problem rather than solving it, stop.

#### 3. Stop after 2 failed attempts on the same issue

If you have tried 2 different approaches to fix the same issue and both failed:
1. **STOP** — do not try a 3rd approach without escalating
2. **Report** what you tried and why each approach failed
3. **Propose** 2-3 alternative strategies with trade-offs
4. **Wait** for direction before proceeding

This prevents the "spiral of hacks" where each failed attempt introduces new problems that require their own hacks.

#### 4. Admit what you don't know

If you are unsure why something is broken, say so. Do not guess at a fix and present it as confident. The phrases "I believe this will fix it" or "this should work" without evidence are red flags.

Instead: "I don't know why this is failing. I need to add instrumentation to find the root cause."

#### 5. Every fix must leave the codebase better, not worse

A fix that solves one problem but introduces code smell, reduces readability, or breaks an abstraction boundary is not acceptable. If the correct fix requires refactoring, do the refactoring — don't take a shortcut that degrades the codebase.

---

## Part 2: Zero Assumption — Evidence-Based Debugging

### The Methodology

#### Step 1: Observe — Gather evidence before forming hypotheses

Before changing any code to fix an issue:
1. Read the actual error message / stack trace / log output
2. Reproduce the issue — confirm you can trigger it
3. Identify the exact file and line where the failure occurs
4. Document what you observed (not what you assumed)

**Anti-pattern:** Reading an error message and immediately jumping to "I think the issue is X" without verifying.

#### Step 2: Instrument — Add logs to find root cause

When the cause is not obvious from the error alone:
1. Add targeted logging / console output at key decision points
2. Log input values, intermediate state, and output values
3. Run the code and read the logs
4. Narrow down to the exact point where behavior diverges from expectation

**Mandatory for debug mode:** Always prefer adding instrumentation over making assumptions. Five minutes of logging saves hours of wrong-direction fixes.

#### Step 3: Diagnose — Form hypothesis from evidence only

Your diagnosis must be backed by specific log output or test results:
- "The API returns 404 because the route is `/users/:id` but the frontend calls `/user/:id`" (evidence: network tab shows 404 on `/user/123`)
- NOT: "I think there might be a routing issue" (assumption without evidence)

#### Step 4: Fix — Targeted change based on diagnosis

Make the minimum change that addresses the diagnosed root cause. Verify the fix:
1. The original error no longer occurs
2. No new errors were introduced
3. Related tests pass

#### Step 5: Clean up — Remove instrumentation

After the fix is verified, remove all debug logging and instrumentation added in Step 2. Debug code must never be committed.

### Evidence Requirements

Every fix reported to the evaluator or in the baton must include:

| Field | Required content |
|-------|-----------------|
| **What broke** | Exact error message or observed symptom |
| **Root cause** | Specific code location + why it failed (backed by logs/tests) |
| **Fix applied** | What was changed and why this addresses the root cause |
| **Verification** | How the fix was verified (test output, manual check, log confirmation) |

Fixes without evidence are treated as assumptions and may be rejected by the evaluator.

---

## Part 3: Consensus Validation

### Why Single-Agent Decisions Fail

A single agent making decisions in isolation is prone to:
- **Confirmation bias** — finding evidence that supports its first guess
- **Sunk cost** — continuing a failing approach because it already invested effort
- **Tunnel vision** — missing alternative solutions because it fixated on one path

### The Consensus Protocol

For critical decisions (architecture choices, debug diagnoses, approach changes):

1. **Parallel evaluation** — spawn 2 independent reviewers with the same evidence
2. **Convergence check** — if both agree (within acceptable delta), proceed
3. **Divergence resolution** — if they disagree, spawn a 3rd tiebreaker with both perspectives
4. **Evidence requirement** — each reviewer must cite specific evidence for their position

### When to Apply Consensus

| Situation | Consensus required? |
|-----------|-------------------|
| Routine code changes | No — single agent is sufficient |
| Debug diagnosis after 1 failed attempt | Yes — before trying approach #2 |
| Architecture or approach change | Yes — before committing to new direction |
| Evaluation scoring (harness) | Yes — dual evaluators with convergence check |
| "I'm not sure why this is broken" | Yes — get a second perspective before guessing |

---

## Part 4: Escalation Protocol

### When to Escalate to the User

Escalate immediately (do not attempt another fix) when:

1. **2 failed attempts** on the same issue (Rule 3 above)
2. **Root cause is outside your control** (missing API key, wrong environment, dependency bug)
3. **Conflicting requirements** — the spec asks for two things that contradict each other
4. **Stagnation** — scores are not improving despite targeted fixes (plateau detected)
5. **Uncertainty** — you genuinely don't know what's wrong and instrumentation hasn't helped

### Escalation Format

```
## Stuck: [brief description of the issue]

### What I tried
1. [Approach 1]: [what happened, why it failed]
2. [Approach 2]: [what happened, why it failed]

### Evidence gathered
- [Log output / test results / error messages]

### Proposed options
A. [Option A]: [approach + trade-offs]
B. [Option B]: [approach + trade-offs]
C. [Option C]: [approach + trade-offs]

### My recommendation
[Which option and why, or "I need more context to recommend"]
```

### What NOT to Do When Stuck

- Do NOT silently try a 3rd, 4th, 5th approach
- Do NOT ship a workaround and mark the issue as "fixed"
- Do NOT lower quality standards to make scores pass
- Do NOT blame external factors without evidence
- Do NOT skip the issue and move to something else

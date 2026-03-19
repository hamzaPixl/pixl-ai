---
name: eval-harness
description: "Capability and regression evaluation harness for pixl-crew skills, agents, and prompts. Runs pass@k metrics, tracks regressions across versions, and generates eval reports. Use when measuring skill/agent quality or regression-testing after prompt changes. Not for comparing code patterns — see /benchmark."
allowed-tools: Read, Bash, Glob, Grep, Write, Agent
argument-hint: "<target: skill-name|agent-name|prompt-file> [--k=3] [--mode=capability|regression]"
---

# Eval Harness

Structured evaluation framework for measuring skill, agent, and prompt quality.

## Step 0: Parse Arguments

- `target` — skill name, agent name, or path to a prompt file
- `--k=N` — number of runs per test case (default: 3)
- `--mode` — `capability` (can it do X?) or `regression` (did it break?)

## Step 1: Discover Test Cases

### For Skills
1. Read the skill's `SKILL.md` for expected behavior
2. Check for existing eval files: `skills/<name>/evals/` or `skills/<name>/test-cases.jsonl`
3. If none exist, generate test cases from the skill description

### For Agents
1. Read the agent's `.md` file for trigger examples and role
2. Extract test scenarios from `<example>` blocks
3. Generate edge cases from role constraints

### For Prompts
1. Read the prompt file
2. Extract expected outputs from comments or paired `.expected` files

## Step 2: Define Evaluation Criteria

Each test case needs:
```json
{
  "input": "the prompt or task",
  "criteria": [
    {"name": "correctness", "type": "binary", "description": "Does it produce the right output?"},
    {"name": "format", "type": "binary", "description": "Does it follow the expected format?"},
    {"name": "completeness", "type": "scale_1_5", "description": "Are all required elements present?"}
  ],
  "blockers": ["must not hallucinate file paths", "must not modify excluded files"]
}
```

## Step 3: Run Evaluations

For each test case, run `k` times:
1. Execute the skill/agent/prompt
2. Capture the full output
3. Evaluate against criteria (use a judge prompt if automated checking isn't possible)
4. Record pass/fail per criterion

## Step 4: Calculate Metrics

| Metric        | Formula                                  |
| ------------- | ---------------------------------------- |
| **pass@1**    | % of test cases passing on first try     |
| **pass@k**    | % passing at least once in k runs        |
| **precision** | Correct outputs / total outputs          |
| **recall**    | Required elements present / total required |

## Step 5: Generate Report

Output a structured eval report:

```markdown
# Eval Report: <target>
Date: <timestamp>
Mode: <capability|regression>
Runs per case: <k>

## Summary
- pass@1: X%
- pass@k: Y%
- Total test cases: N
- Failures: M

## Detailed Results
| Test Case | pass@1 | pass@k | Notes |
|-----------|--------|--------|-------|
| ...       | ...    | ...    | ...   |

## Regressions (if regression mode)
| Test Case | Previous | Current | Delta |
|-----------|----------|---------|-------|
| ...       | ...      | ...     | ...   |
```

Save report to `skills/<target>/evals/report-<timestamp>.md` or `.claude/evals/`.

## Step 6: Regression Tracking

If `--mode=regression`:
1. Load previous eval report from `evals/` directory
2. Compare current results against baseline
3. Flag any test cases that regressed (pass → fail)
4. Exit with non-zero if regressions found

## Anti-Patterns

- Don't evaluate on the same examples used in the skill description
- Don't use subjective criteria without a rubric
- Don't skip edge cases — they're where regressions hide
- Don't run evals on production data — use synthetic test cases

# Multi-Model Arbitration

## When to Use

When stuck on a decision — reasoning loops, conflicting approaches, or uncertain architecture — spawn a parallel agent with a different model to get a second opinion.

## Pattern

1. **Detect stuck state**: 3+ failed attempts at the same approach, or circular reasoning
2. **Spawn cross-check agent**: launch an Explore or Plan agent with a different model tier
   - If main session is Opus → spawn Sonnet agent for a different perspective
   - If main session is Sonnet → spawn Opus agent for deeper reasoning
3. **Provide full context**: give the cross-check agent the problem, your current approach, and why you're stuck
4. **Arbitrate**: compare the two approaches. If they agree, proceed. If they disagree, present both to the user

## Example

```
Agent(
  subagent_type="Plan",
  model="sonnet",
  prompt="I'm stuck on [problem]. My current approach is [X] but it's failing because [Y]. What alternative approach would you recommend? Be specific about files and patterns."
)
```

## When NOT to Use

- Routine implementation decisions — just pick one and iterate
- When the problem is clearly a bug, not a design question
- When you haven't tried the obvious approach first

**Note**: For proactive cross-model PR review (not stuck-state arbitration), see the `/cross-review` skill.

## Cost Consideration

Cross-checking doubles the token cost for that decision. Reserve for architectural choices, not line-level edits. The pixl engine already handles this for workflow stages via ContractValidator — this pattern is for interactive sessions only.

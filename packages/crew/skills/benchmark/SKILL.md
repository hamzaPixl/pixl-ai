---
name: benchmark
description: "Compare local code patterns against real-world open-source implementations from GitHub. Use when you want to see how other projects implement the same pattern (auth, DDD, i18n) or identify gaps vs industry standards. Not for performance benchmarking — see /eval-harness for metric-based evaluation."
allowed-tools: Read, Glob, Grep, Bash, WebSearch, WebFetch, Agent, AskUserQuestion
argument-hint: "<pattern, feature, or architecture to benchmark — e.g. 'auth middleware', 'DDD aggregate pattern', 'Next.js i18n setup'>"
---

# Benchmark

Compare local code against real-world open-source implementations. Find
high-quality references, analyze differences, and produce actionable
improvement recommendations.

## Workflow

### Step 1: Scope

Identify what to benchmark from the user's request or argument:

- **Pattern**: a specific code pattern (e.g. "repository pattern", "middleware chain")
- **Architecture**: a structural approach (e.g. "hexagonal architecture", "monorepo layout")
- **Feature**: a concrete feature implementation (e.g. "auth with JWT refresh", "i18n setup")
- **Library usage**: how a library is used in practice (e.g. "Prisma with soft deletes", "Zustand store patterns")

Read the local implementation to understand:

1. Which files implement the pattern (use Glob + Grep)
2. The current approach, structure, and key decisions
3. Stack details (language, framework, libraries) to target relevant references

Ask the user to confirm scope if ambiguous (AskUserQuestion).

### Step 2: Search for References

Use `WebSearch` to find 3–5 high-quality references. Search strategies:

```
"<pattern> site:github.com <stack>" — direct GitHub repos
"<pattern> best practices <framework> <year>" — articles and guides
"<pattern> example implementation <language>" — tutorials with code
"awesome-<topic> github" — curated lists
```

Filter criteria:

- **Stars/popularity**: prefer repos with >500 stars or articles from known sources
- **Recency**: prefer references updated within the last 2 years
- **Stack match**: same language/framework as the local codebase
- **Production quality**: skip toy examples, prefer real-world usage

Collect for each reference:

- URL
- Repo name or article title
- Why it's relevant
- Star count / authority signal

### Step 3: Analyze References

Use `WebFetch` on the top 3 matches to extract:

- **Approach**: high-level strategy and design decisions
- **File structure**: how they organize the feature
- **Key patterns**: naming, error handling, testing, configuration
- **Trade-offs**: what they optimize for (simplicity, performance, extensibility)

For GitHub repos, fetch the specific files that implement the pattern (README,
main source files, config). Do not try to read entire repositories.

### Step 4: Compare

Build a side-by-side comparison table:

| Dimension      | Local Implementation | Reference A | Reference B | Reference C |
|----------------|----------------------|-------------|-------------|-------------|
| Structure      | ...                  | ...         | ...         | ...         |
| Naming         | ...                  | ...         | ...         | ...         |
| Error handling | ...                  | ...         | ...         | ...         |
| Performance    | ...                  | ...         | ...         | ...         |
| Extensibility  | ...                  | ...         | ...         | ...         |
| Testing        | ...                  | ...         | ...         | ...         |
| Configuration  | ...                  | ...         | ...         | ...         |

Add or remove dimensions based on relevance. Not every dimension applies to
every benchmark.

Mark cells with qualitative assessment:

- **Strong** — local implementation matches or exceeds references
- **Adequate** — acceptable but references show a better approach
- **Gap** — references have something the local implementation lacks
- **Different** — different approach, neither clearly better

### Step 5: Recommend

Produce a ranked list of improvements, grouped by severity:

#### Quick Wins (< 1 hour each)

Small changes inspired by reference patterns: naming improvements, missing
error cases, configuration gaps.

#### Significant Improvements (1–4 hours each)

Structural changes that bring the implementation closer to industry standards:
better separation of concerns, missing abstractions, improved patterns.

#### Architectural Considerations (> 4 hours)

Fundamental approach changes worth considering for the long term. Only suggest
these when references clearly demonstrate a superior pattern AND the local
implementation has concrete problems (not just "different").

Each recommendation must include:

- What to change and why
- Which reference inspired it (with link)
- A code snippet from the reference showing the pattern
- Estimated impact (maintainability, performance, developer experience)

### Step 6: Report

Output the full comparison as a structured markdown report:

```markdown
# Benchmark Report: <topic>

## Scope
What was benchmarked and why.

## Local Implementation
Summary of current approach with key file paths.

## References
1. **[Name](url)** — brief description, why selected
2. ...

## Comparison Matrix
(table from Step 4)

## Recommendations
(ranked list from Step 5)

## Key Takeaways
3–5 bullet points summarizing the most important findings.
```

## Guidelines

- **Be fair**: the local implementation may be better in ways references aren't.
  Call out local strengths, not just gaps.
- **Context matters**: a startup MVP has different needs than an enterprise
  library. Weight recommendations accordingly.
- **Avoid cargo-culting**: don't recommend copying a pattern just because a
  popular repo uses it. Explain WHY the pattern is better for THIS codebase.
- **Cite everything**: every recommendation must link back to the specific
  reference that inspired it.
- **Stay practical**: focus on actionable improvements, not theoretical ideals.

## Related Skills

- **`/cto-review`** — Run after benchmarking to get an opinionated review of whether the recommended changes are worth the complexity
- **`/self-review-fix-loop`** — Apply quick-win recommendations automatically

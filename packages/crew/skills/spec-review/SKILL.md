---
name: spec-review
description: "Compare implementation against a PRD or requirements document. Detects what is implemented, what is missing, what is extra (scope creep), and what drifted since last review. Use when asked to 'check against spec', 'review PRD coverage', 'compare implementation to requirements', 'spec drift', 'validate against PRD', or 'are we building the right thing'."
allowed-tools: Read, Glob, Grep, Write, WebFetch, Agent, AskUserQuestion
argument-hint: "<PRD file path, URL, or 'rescan' to re-check against stored spec>"
---

## Overview

This skill compares what you **built** against what you **planned**. It parses a PRD or requirements document into atomic, checkable requirements, scans the codebase for evidence of implementation, and produces a coverage report with gap analysis. On subsequent runs, it detects **spec drift** — requirements that were added, removed, changed, or reprioritized since the last review.

**Why this matters**: Projects are non-linear. Requirements drift, features get descoped, priorities shift. Without periodic validation, teams build the wrong thing or miss critical features. The best time to checkpoint is at natural boundaries — review completion, spec update, sprint end.

## Required References

Before starting, read these references for detailed strategies:
- `references/requirement-decomposition.md` — how to parse PRDs into checkable items
- `references/coverage-analysis.md` — codebase scanning strategies
- `references/drift-detection.md` — snapshot diffing, drift classification

## Mode Detection

Determine the operating mode from the argument and stored state:

| Input | Stored `requirements.json`? | Mode |
|-------|----------------------------|------|
| File path, URL, or text | No | **A: Baseline** — parse PRD, scan codebase, produce initial coverage |
| File path, URL, or text | Yes | **B: Drift + Coverage** — detect spec drift, re-scan, compare |
| `rescan` or no argument | Yes | **C: Rescan** — re-scan codebase against stored spec |
| No argument | No | **Error** — ask user for PRD |

Storage location in the target project:
```
.context/spec/
├── spec-snapshot-<timestamp>.md     # Immutable PRD copies
├── requirements.json                 # Decomposed requirements (mutable)
├── coverage-<timestamp>.json         # Coverage scan results
└── drift-log.jsonl                   # Append-only drift entries
```

## Step 1: Parse and Decompose Requirements (Modes A, B)

1. **Read the PRD source**:
   - If the argument is a file path (contains `/` or `.md` or `.txt` or `.pdf`): Read with the Read tool
   - If the argument is a URL (starts with `http`): Fetch with WebFetch
   - Otherwise: treat the argument as inline text

2. **Save an immutable snapshot**: Write the raw PRD text to `.context/spec/spec-snapshot-<timestamp>.md`

3. **Decompose into atomic requirements** using the patterns in `references/requirement-decomposition.md`:
   - Each requirement gets: `id` (R-001), `category` (functional/non-functional/constraint), `summary`, `acceptance_criteria[]`, `priority` (must/should/could), `search_hints[]` (patterns to grep for)
   - Functional requirements describe user-visible behavior
   - Non-functional requirements describe quality attributes (performance, security, accessibility)
   - Constraints describe technical boundaries (tech stack, deployment, compliance)

4. **Save decomposition** to `.context/spec/requirements.json`:

```json
{
  "spec_version": "<ISO timestamp>",
  "source": "<path or URL>",
  "requirements": [
    {
      "id": "R-001",
      "category": "functional",
      "summary": "User can sign up with email and password",
      "acceptance_criteria": [
        "Email validation on input",
        "Password minimum 8 chars",
        "Confirmation email sent"
      ],
      "priority": "must",
      "search_hints": ["signUp", "register", "auth/signup", "createUser"]
    }
  ]
}
```

5. **Present decomposition summary** to user: total requirements, breakdown by category and priority, any ambiguous items that need clarification. Use AskUserQuestion if any requirements are unclear.

## Step 2: Drift Detection (Mode B only)

1. **Load previous** `requirements.json` and new PRD decomposition
2. **Diff requirements** by matching on `id` and `summary`:
   - **Added**: new requirement IDs not in previous version
   - **Removed**: previous IDs not in new version
   - **Changed**: same ID, different summary/criteria/priority
   - **Reprioritized**: same ID, different priority level
3. **Append drift entries** to `.context/spec/drift-log.jsonl`:
   ```jsonl
   {"timestamp":"<ISO>","type":"added","id":"R-026","summary":"..."}
   {"timestamp":"<ISO>","type":"removed","id":"R-012","summary":"..."}
   {"timestamp":"<ISO>","type":"changed","id":"R-005","field":"acceptance_criteria","before":"...","after":"..."}
   ```
4. **Output drift summary**: count of changes by type, highlight any removed `must` requirements or newly added `must` requirements

## Step 3: Coverage Scan (All modes)

1. **For each requirement**, use `search_hints` to scan the codebase:
   - Use Grep with each hint pattern
   - Use Glob to find related files by naming convention
   - For large codebases (>20 requirements): use parallel Explore agents (one per 5-10 requirements)

2. **Classify each requirement**:
   - `implemented` — evidence found for all acceptance criteria
   - `partial` — evidence found for some acceptance criteria (note which are missing)
   - `missing` — no evidence found for any criteria
   - `extra` — implementations found that don't map to any requirement (potential scope creep)

3. **Calculate coverage**:
   ```
   coverage% = (implemented + 0.5 * partial) / total * 100
   ```

4. **Save coverage report** to `.context/spec/coverage-<timestamp>.json`:

```json
{
  "timestamp": "<ISO>",
  "total": 25,
  "implemented": 15,
  "partial": 5,
  "missing": 3,
  "extra": 2,
  "coverage_percentage": 70.0,
  "results": [
    {
      "id": "R-001",
      "status": "implemented",
      "evidence": [
        {"file": "src/auth/signup.ts", "line": 42, "match": "async function signUp"}
      ],
      "notes": ""
    },
    {
      "id": "R-005",
      "status": "partial",
      "evidence": [
        {"file": "src/auth/signup.ts", "line": 55, "match": "validateEmail"}
      ],
      "notes": "Missing: password strength validation, confirmation email"
    },
    {
      "id": "R-012",
      "status": "missing",
      "evidence": [],
      "notes": "No implementation found for admin audit log"
    }
  ],
  "extras": [
    {
      "description": "Dark mode toggle implementation",
      "files": ["src/components/ThemeToggle.tsx"],
      "notes": "Not in requirements — potential scope creep or undocumented feature"
    }
  ]
}
```

## Step 4: Output

Present a structured report:

### Coverage Report
- **Coverage percentage** with visual indicator (bar or emoji scale)
- **Per-requirement status table**: ID, summary, status, evidence location
- **Gap list**: missing/partial requirements with suggested next steps
- **Extras list**: implementations not mapped to requirements

### Drift Summary (Mode B only)
- What changed in requirements since last review
- Impact on existing implementation (newly unblocked work, invalidated work)

### Actionable Next Steps
- Prioritized list of gaps to close (must → should → could)
- Optional: produce a gap task list consumable by `/task-plan` — ask user if they want this

### Decision Logging
Append a decision entry to `.claude/memory/decisions.jsonl`:
```jsonl
{"timestamp":"<ISO>","type":"spec_review","coverage_pct":<N>,"missing":<N>,"drift_entries":<N>,"source":"<path>"}
```

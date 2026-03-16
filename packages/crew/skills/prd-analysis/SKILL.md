---
name: prd-analysis
description: "Analyze and structure a PRD into a reusable project foundation. Parses requirements documents into 8 structured categories, decomposes atomic requirements, and persists artifacts for downstream skills. Use when asked to 'analyze a PRD', 'structure requirements', 'project overview from PRD', 'parse requirements document', or 'break down a spec'."
allowed-tools: Read, Write, Bash, Glob, Grep, WebFetch, AskUserQuestion
argument-hint: "<PRD file path, URL, or paste text>"
---

## Overview

This skill sits at the top of the planning funnel — it takes a raw PRD or source document and produces a structured project foundation that downstream skills consume directly.

```
Raw PRD/source → /prd-analysis → structured .context/ → /task-plan, /sprint-planning, /prd-pipeline
```

**Why this exists**: `/prd-pipeline` goes end-to-end (PRD → code → PR) and `/spec-review` only works when code already exists. This skill fills the gap: "I have a raw PRD → produce a structured project overview → persist as artifacts → make available for downstream workflows."

## Required References

Read these before starting:
- `references/analysis-categories.md` — templates for the 8 analysis categories
- `references/output-schema.md` — JSON schema for requirements.json and project-overview.md structure
- `../spec-review/references/requirement-decomposition.md` — atomic requirement decomposition methodology (reuse, don't duplicate)

## Step 1: Input Acquisition

Detect the input type and acquire the raw PRD content:

| Input Type | Detection | Action |
|---|---|---|
| **File path** | Contains `/`, `.md`, `.txt`, `.pdf` | Read with Read tool |
| **URL** | Starts with `http://` or `https://` | Fetch with WebFetch |
| **Pasted text** | Neither of the above | Use the argument text directly |
| **No argument** | Empty | Ask user via AskUserQuestion: "Please provide a PRD file path, URL, or paste the requirements text." |

After acquiring content:

1. Create `.context/` and `.context/spec/` directories if they don't exist:
   ```bash
   mkdir -p .context/spec
   ```
2. Save the raw PRD to `.context/prd.md` (canonical location used by downstream skills)
3. Confirm to the user: source type, approximate length, and that it's saved to `.context/prd.md`

## Step 2: Structural Analysis

Parse the PRD into the 8 categories defined in `references/analysis-categories.md`:

1. **Project Overview** — elevator pitch, goals, success metrics, target users
2. **Domain Model** — entities, relationships, bounded contexts
3. **Architecture Overview** — components, integrations, tech stack, deployment
4. **Milestones** — phased delivery with objectives per phase
5. **Feature Breakdown** — epics → features, MoSCoW priorities
6. **Technical Requirements** — performance, security, scalability, accessibility
7. **Risks & Assumptions** — probability, impact, mitigation strategies
8. **Open Questions** — blocking vs informational, grouped by category

For each category:
- Extract explicitly stated information from the PRD
- Infer reasonable defaults when the PRD is silent (mark as `[inferred]`)
- Flag ambiguities for the clarification step
- Follow the output format specified in `references/analysis-categories.md`

## Step 3: Atomic Requirements Decomposition

Follow the methodology from `../spec-review/references/requirement-decomposition.md`:

1. **Identify requirement sources** — explicit, implicit, acceptance criteria, non-functional, constraints
2. **Apply atomicity rules** — each requirement must be testable, independent, and unambiguous
3. **Classify** — `functional`, `non-functional`, or `constraint`
4. **Assign MoSCoW priority** — `must`, `should`, `could` (map from PRD priority scheme if present)
5. **Generate search hints** — function names, route patterns, file paths, domain terms, test names

Output to `.context/spec/requirements.json`:

```json
{
  "source": ".context/prd.md",
  "generated_at": "ISO timestamp",
  "total": 0,
  "by_priority": { "must": 0, "should": 0, "could": 0 },
  "by_category": { "functional": 0, "non-functional": 0, "constraint": 0 },
  "requirements": [
    {
      "id": "R-001",
      "category": "functional",
      "summary": "One-sentence description",
      "acceptance_criteria": ["Testable criterion 1", "Testable criterion 2"],
      "priority": "must",
      "search_hints": ["pattern1", "pattern2"],
      "notes": "Any ambiguity or clarification needed"
    }
  ]
}
```

## Step 4: Clarification

Review all flagged ambiguities and open questions from Steps 2 and 3.

1. Group questions by category (e.g., "Domain Model", "Technical Requirements")
2. Prioritize: blocking questions first (those that affect `must` requirements), informational second
3. Limit to the **top 5-7 most impactful** questions — don't overwhelm the user
4. Present via AskUserQuestion in this format:

```
I've analyzed the PRD and have a few clarifying questions grouped by area:

**Domain Model**
1. [Question about entity relationships]
2. [Question about bounded contexts]

**Technical Requirements**
3. [Question about performance targets]

**Architecture**
4. [Question about deployment constraints]

Would you like to answer these now, or should I proceed with reasonable defaults (marked as [inferred])?
```

5. If the user provides answers, update the analysis and requirements accordingly
6. If the user skips, proceed with inferred defaults — all inferences remain marked as `[inferred]`

## Step 5: Assemble Project Overview

Write `.context/project-overview.md` with all 8 categories assembled:

```markdown
# Project Overview

> Generated by /prd-analysis from `.context/prd.md`
> Generated at: {ISO timestamp}

## 1. Project Overview
{elevator pitch, goals, success metrics, target users}

## 2. Domain Model
{entities, relationships, bounded contexts}

## 3. Architecture Overview
{components, integrations, tech stack, deployment}

## 4. Milestones
{phased delivery with objectives}

## 5. Feature Breakdown
{epics → features with MoSCoW priorities}

## 6. Technical Requirements
{performance, security, scalability, accessibility}

## 7. Risks & Assumptions
{probability, impact, mitigation}

## 8. Open Questions
{blocking vs informational, with status}

---

## Downstream Integration

- **Task planning**: Run `/task-plan .context/prd.md` — consumes `requirements.json` automatically
- **Sprint planning**: Run `/sprint-planning` after task planning
- **Spec review**: Run `/spec-review .context/prd.md` — uses pre-decomposed requirements (Mode C)
- **Full pipeline**: Run `/prd-pipeline .context/prd.md` — skips Phase 1.1 setup + partial 1.4
```

## Step 6: Persist Artifacts

### With pixl CLI (if available)

Check if `pixl` is on PATH:
```bash
command -v pixl >/dev/null 2>&1 && echo "available" || echo "unavailable"
```

If available:
```bash
pixl artifact put --type context --name "project-overview" --path .context/project-overview.md --tag prd-analysis
pixl artifact put --type requirement --name "requirements" --path .context/spec/requirements.json --tag prd-analysis
```

### Always (file-based)

The `.context/` files are always written regardless of CLI availability:
- `.context/prd.md` — raw PRD (Step 1)
- `.context/spec/requirements.json` — decomposed requirements (Step 3)
- `.context/project-overview.md` — structured overview (Step 5)

### Decision Log

If `.claude/memory/decisions.jsonl` exists, append:
```json
{"timestamp": "ISO", "type": "analysis", "summary": "PRD analyzed: {project name} — {N} requirements ({must}/{should}/{could})", "skill": "prd-analysis"}
```

## Step 7: Summary

Present the final summary to the user:

```
## PRD Analysis Complete

**Source**: {file/URL/text} → `.context/prd.md`

### Requirements
| Priority | Count |
|----------|-------|
| Must     | {n}   |
| Should   | {n}   |
| Could    | {n}   |
| **Total**| {N}   |

### Milestones
{list of milestone names with objective counts}

### Open Questions
- {n} blocking (need answers before implementation)
- {n} informational (can proceed with defaults)

### Artifacts
- `.context/prd.md` — raw PRD
- `.context/project-overview.md` — structured overview (8 categories)
- `.context/spec/requirements.json` — {N} atomic requirements

### Suggested Next Steps
1. `/task-plan .context/prd.md` — decompose into implementation tasks
2. `/sprint-planning` — organize tasks into sprint iterations
3. `/prd-pipeline .context/prd.md` — run the full autonomous pipeline
```

## Related Skills

- `/prd-pipeline` — full autonomous PRD-to-production pipeline (consumes this skill's output)
- `/spec-review` — compare implementation against requirements (consumes `requirements.json`)
- `/task-plan` — task decomposition (consumes `requirements.json` and `prd.md`)
- `/sprint-planning` — sprint sizing (consumes task plan output)
- `/vision-advisory` — strategic advisory package (complementary, higher-level)

---
name: website-project
description: "Orchestrates a full multi-agent website pipeline across four phases: parallel discovery (design-extraction + task-plan + reference site analysis), architecture (component tree + page structure), parallel implementation (scoped frontend-engineer waves + SEO/devops), and quality (self-review-fix-loop + tech-lead review). Use when asked to 'build a website project', 'orchestrate a website', 'multi-agent website', or 'website pipeline'."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Task
argument-hint: "<website brief, Figma URL, reference URL, or project description>"
context: fork
---

## Overview

Multi-agent orchestration wrapper around the `/website` skill. Adds: parallel agent routing, architecture phase, quality gate with tech-lead review. The `/website` skill defines the canonical 8-step workflow; this skill coordinates WHO executes each step.

**Relationship to other skills:**

- `/website` — the implementation reference (steps, rules, parallel waves). This skill calls it.
- `/design-extraction` — extraction skill. Called in Phase 1 if a URL/Figma input is provided.
- `/website-theme`, `/website-layout` — not used here (those modify existing sites).

**Suggested Team:** orchestrator (coordination), frontend-engineer (Phases 1, 3), product-owner (Phase 1), explorer (Phase 1), architect (Phase 2), devops-engineer (Phase 3), qa-engineer (Phase 4), tech-lead (Phase 4)

## Phase 1 — Discovery (Parallel)

Spawn 3 agents in parallel via `Task`:

| Agent | Type              | Skill                | Output                                                                             |
| ----- | ----------------- | -------------------- | ---------------------------------------------------------------------------------- |
| A     | frontend-engineer | `/design-extraction` | `design-spec.json` — full token set, variants, layout, components                  |
| B     | product-owner     | `/task-plan`         | Ordered task list, acceptance criteria, dependency chains                          |
| C     | explorer          | _(none)_             | Section inventory, nav structure, content tone, CTA placement, responsive patterns |

Each agent prompt MUST include:

- The user's original brief / URL
- Explicit output format and file ownership
- Anti-conflict guard: "DO NOT create project files"

**Gate:** All 3 agents succeed (retry once on failure). Assemble discovery context packet, write to `.context/discovery-packet.json` following `references/orchestration/context-packet.md`.

**Mode C note:** In Mode C, Agent A's `/design-extraction` runs all 9 phases (including Firecrawl, asset download, per-section screenshots). Agent B and C outputs are informational only — section order and content come from the spec.

**Mode routing:** If Agent A produced a `design-spec.json` from a URL → `/website` Mode C (replicate) or Mode B (spec-fed). If from discovery → `/website` Mode A.

## Phase 2 — Architecture (1 architect agent)

Spawn the **architect** agent with the discovery packet to produce:

1. **Component tree** — every component mapped to a file path
2. **Page structure** — section order per page, matching `design-spec.json` `pages[]`
3. **Implementation grouping** — non-overlapping file groups for parallel frontend-engineers
4. **Shared dependency identification** — components used across groups
5. **Token validation** — verify all `design-spec.json` required fields are present

**Mode C override:** In Mode C, the architect MUST NOT reorganize sections. The section list and order from `spec.pages[]` is authoritative.

Write to `.context/architecture-packet.json`.

**Gate:**

- At least one page defined
- Every section mapped to exactly one file
- Zero file overlap between implementation groups
- No unresolved token gaps in `design-spec.json`

## Phase 3 — Implementation (Parallel Waves)

This phase executes `/website` Steps 4-7 (scaffold → build sections → components → blog) using parallel agents.

### Pre-wave: Scaffold

Run `/website` Step 4 (scaffold) in the main context:

1. Write tokens file from `design-spec.json` (use mapping in `references/frontend/design-spec-schema.md`)
2. Run `bash scripts/scaffold.sh studio/stacks/nextjs/ <project-dir> /tmp/<slug>-tokens.txt`
3. Run `npm install && npx tsc --noEmit`

### Wave A: Build Sections (2-4 parallel frontend-engineer agents)

Distribute sections from the architecture packet across N agents (see `/website` Step 5 for rules):

- Each agent receives: design-spec.json tokens, its assigned section files, variant names, content
- Each agent builds its sections following `/website` Section Building Rules
- **Anti-conflict:** "DO NOT create or modify any files outside your assigned list"
- **Mode C override:** In Mode C, agents receive `screenshot_path` and `content` per section from the spec. No content-agent output to merge. Assets must be copied to `public/assets/` before section building begins.

### Wave B: SEO/DevOps (parallel with Wave A)

1 devops-engineer for: SEO metadata, sitemap, robots.txt, deployment config. Must NOT touch `components/sections/`.

### Wave C: Layout Components (after Wave A)

2 parallel agents:

- Agent LC-1: `components/nav.tsx` — variant from `design-spec.json`
- Agent LC-2: `components/footer.tsx` — variant from `design-spec.json`

### Wave D: Integration (after A, B, C)

Orchestrator integrates:

1. Import all sections into page files
2. Import nav/footer into layout
3. Run `npx tsc --noEmit` and `npm run build`

**Gate:** All files exist, tsc passes, sections in correct order, nav/footer integrated.

## Phase 4 — Quality

### Step 1: Self-Review

Spawn 1 qa-engineer with `/self-review-fix-loop`:

- Scope: all files in the new project
- 3 iteration cap, stop at no P0/P1

### Step 2: Tech-Lead Review

Spawn 1 tech-lead for final review:

- **APPROVE** → synthesize final summary
- **REQUEST_CHANGES** → route feedback to responsible agent, re-review (max 2 rounds)
- **REJECT** → escalate to user

**Mode C override:** In Mode C, visual regression results from `scripts/visual-diff.mjs` are the primary quality gate. QA agent should verify all viewports pass their diff thresholds.

**Gate:** No P0/P1 findings, tech-lead APPROVE, final tsc + build pass.

## Exit

All four phases executed, every gate passed, `npm run build` succeeds.

Final summary includes:

- Pages built with section list
- Archetype and key tokens applied
- Total agents spawned
- Key decisions and trade-offs
- Known limitations

## Context Packet Standard

All inter-agent data follows `references/orchestration/context-packet.md`:

| File                                | Content                                     |
| ----------------------------------- | ------------------------------------------- |
| `.context/design-spec.json`         | Design tokens, variants, pages, components  |
| `.context/discovery-packet.json`    | Merged output from Phase 1 agents           |
| `.context/architecture-packet.json` | Component tree, file groups, page structure |
| `.context/review-findings.json`     | Review findings from Phase 4                |

Add `.context/` to `.gitignore`.

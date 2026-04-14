---
name: design-critique
description: "Independent design review of current UI against the AI Slop Test and design anti-patterns. Scores 6 axes (typography, color, spacing, motion, interaction, originality) 1-10 with prioritized fix list. Use when asked to critique a design, review UI quality, audit for AI slop, or get a second opinion on visual craft."
allowed-tools: Read, Glob, Grep, Bash, WebFetch
argument-hint: "[component-path | page-url]"
---

## Overview

Independent, opinionated design review that evaluates UI against a catalog of anti-patterns and the "AI Slop Test" — the instinct to look generic, templated, or machine-generated. Produces a scored report (6 axes, 1-10) and a prioritized fix list. Critique only — use `/design-polish` to auto-fix findings or `/design-distill` to strip overdesign.

**How this differs**:
- `/react-doctor` — code health (hooks, a11y, perf). This skill — visual craft and design quality.
- `/cto-review` — architectural review. This skill — pixel-level aesthetics.
- `/design-variants` — generate new directions. This skill — critique what already exists.

## Required References

Before starting, read these design vocabulary files:
- `references/frontend/design/anti-patterns.md` — banned patterns catalog
- `references/frontend/design/craft-process.md` — craft rubric
- `references/frontend/design/typography.md` — type scale, pairing, hierarchy
- `references/frontend/design/color-and-contrast.md` — palette, contrast, semantic color

## Step 1: Identify Scope

Resolve what to critique:

- **File path** (`src/components/Hero.tsx`) — read the component and its styles
- **Page URL** (`http://localhost:3000/pricing`) — use WebFetch to retrieve rendered HTML/CSS
- **Directory** (`src/components/`) — scan all components, pick top 5 by size/importance
- **No arg** — look for a running dev server, critique the home page; else ask user

Gather:
1. Design tokens (`tailwind.config.*`, `design-config.ts`, CSS variables)
2. `.design-context.md` at project root (brand voice, audience, anti-references) if present
3. Screenshots from `.playwright-mcp/` if the agent-browser has been used

## Step 2: Scan for Banned Patterns

Grep the target files/HTML for known AI-slop tells:

| Pattern | Regex / signal |
|---|---|
| Gradient text | `bg-clip-text.*gradient`, `background-clip: text` with gradient |
| Default Inter everywhere | `font-family.*Inter` with no other font defined |
| Gray text on colored bg | `text-gray-\d+` inside elements with non-neutral background |
| Side-stripe borders | `border-l-4`, colored left accent on cards |
| Emoji-as-icon | Emoji characters in headings, buttons, or feature lists |
| Centered hero + 3-card grid | Classic template layout with no deviation |
| Generic placeholder imagery | `unsplash.com` stock, `placehold.co` in production |
| Overused shadow scale | `shadow-lg`, `shadow-xl` on every card |
| Purple-to-pink gradient | Hardcoded `#8B5CF6` to `#EC4899` or similar AI defaults |
| Rounded-full on everything | Pills, avatars, and buttons all sharing the same radius |

Record every hit with file:line.

## Step 3: Score 6 Axes (1-10)

Evaluate each axis on evidence gathered, not vibes:

| Axis | 1-3 (poor) | 4-6 (okay) | 7-9 (strong) | 10 (exceptional) |
|---|---|---|---|---|
| **Typography** | Default font only, no scale | One font, basic scale | Deliberate pairing, rhythm | Distinctive voice, impeccable hierarchy |
| **Color** | Grays + one accent | Working palette | Cohesive, semantic | Memorable, brand-owned |
| **Spacing** | Arbitrary values | Consistent scale | Tuned rhythm | Intentional density variance |
| **Motion** | None or jank | Default transitions | Considered micro-interactions | Signature motion language |
| **Interaction** | Hover only | States defined | Focus/active/disabled polish | Delightful feedback loops |
| **Originality** | Template | Minor variations | Recognizable identity | Could not be anywhere else |

For each score, cite 2-3 concrete pieces of evidence (file:line or screenshot observation).

## Step 4: Report

Write `DESIGN-CRITIQUE.md` in the repo root (or print inline if ephemeral). Structure:

```markdown
# Design Critique — <target>

## Scores

| Axis | Score | Rationale |
|---|---|---|
| Typography | 5/10 | Uses default Inter across all text (Hero.tsx:12, Nav.tsx:8). No display font. |
| Color | 4/10 | Purple-pink gradient in 3 places. Gray-on-white only. |
| Spacing | 6/10 | Tailwind scale used consistently but every section is `py-24`. |
| Motion | 3/10 | No transitions except default hover opacity. |
| Interaction | 5/10 | Buttons have hover, no focus ring. |
| Originality | 3/10 | Reads as generic AI SaaS template. |
| **Average** | **4.3/10** | |

## AI Slop Test: FAIL

Top offenders:
- Gradient text in Hero.tsx:24
- Default Inter everywhere
- Centered hero + 3-card grid (no layout deviation)

## Top 3 Critical Issues

1. **No design voice** — Typography and color choices are library defaults. Pick a display font and one distinctive accent color.
2. **Predictable layout** — Every section follows the same centered template. Break the grid at least twice.
3. **Dead interactions** — No focus states, no micro-animations, no feedback on submit.

## Prioritized Fix List

### P0 (ship-blockers for craft)
- [ ] Replace Inter with a display+body pairing (e.g., Fraunces + Inter)
- [ ] Remove gradient text from Hero.tsx:24, replace with solid brand color
- [ ] Add focus rings to all interactive elements

### P1 (meaningful polish)
- [ ] Introduce one asymmetric section layout
- [ ] Add entrance animations on scroll to feature cards
- [ ] Tighten type scale: 3xl → 4xl on hero, 2xl → xl on section titles

### P2 (nice-to-have)
- [ ] Add subtle noise/grain texture on dark sections
- [ ] Custom cursor on primary CTAs
```

## Step 5: Handoff

End with a one-line recommendation:
- Score < 5 avg → "Run `/design-distill` first, then `/design-polish`."
- Score 5-7 → "Run `/design-polish` to auto-fix P0/P1 findings."
- Score > 7 → "Polish manually; design is strong."

## Gotchas

- Never critique based on screenshots alone — always cross-reference source
- A high individual axis score (e.g., Typography 9) does not save a low average — originality is the multiplier
- If `.design-context.md` is absent, note it in the report — critique without brand context is incomplete
- Don't score axes you couldn't evaluate (e.g., Motion on a static SSR page) — mark N/A with explanation

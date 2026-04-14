---
name: design-polish
description: "Apply surgical micro-improvements to a UI: tighten type scale, fix spacing rhythm, add micro-interactions, fix focus states, and auto-fix anti-patterns. Never refactors structure — only polish. Use when asked to polish a UI, improve visual craft, fix design details, or auto-fix /design-critique findings."
allowed-tools: Read, Edit, Glob, Grep, Bash
argument-hint: "[component-path | --from-critique]"
---

## Overview

Surgical polish pass on existing UI. Fixes the small-but-visible details that separate "fine" from "crafted": type scale rhythm, spacing consistency, focus states, micro-interactions, hover feedback, and banned anti-patterns. Structure stays intact — no layout rewrites, no component reshaping. Use `/design-distill` first if the UI is overdesigned; use `/design-variants` if you need a new direction.

## Required References

Read before starting:
- `references/frontend/design/typography.md` — type scale and rhythm
- `references/frontend/design/spatial-design.md` — spacing, density, alignment
- `references/frontend/design/interaction-design.md` — hover/focus/active/disabled states
- `references/frontend/design/motion-design.md` — micro-interaction timing and easing
- `references/frontend/design/anti-patterns.md` — banned patterns to replace

## Step 1: Load Findings

Two entry modes:

- **From `/design-critique`** — read `DESIGN-CRITIQUE.md` if present, take P0/P1 fix items
- **Direct** — scan the target file(s) for polish opportunities using the references above

Build a concrete todo list of surgical edits (each mapped to a file:line).

## Step 2: Surgical Edits (in order)

Apply edits one category at a time, re-reading the file after each group:

### 2.1 Anti-pattern removal

- Gradient text → solid brand color with proper font weight
- `text-gray-*` on colored backgrounds → tokenized contrast color
- Side-stripe borders → removed or replaced with subtle top accent
- Emoji-as-icon → SVG icons (use `/svg-icon-creation` if none exist)
- Default Inter-only → pair a display font (see typography.md)

### 2.2 Typography rhythm

- Verify scale steps: `text-sm`, `text-base`, `text-lg`, `text-xl`, `text-2xl`, `text-4xl`, `text-6xl` — skip irregular stops
- Line-height: tighten display text to `leading-[1.05]`, keep body at `leading-relaxed`
- Letter-spacing: `tracking-tight` on headings 3xl+, `tracking-normal` on body, `tracking-wide` on eyebrows/labels
- Font weight: hero 600-700, section titles 500-600, body 400, labels 500

### 2.3 Spacing rhythm

- Section padding: consistent `py-*` scale (16, 24, 32 at most — not `py-20` mixed with `py-32`)
- Component gaps: use one gap token per axis (e.g., card grid `gap-6`, not `gap-4` on one and `gap-8` on another)
- Alignment: verify text alignment intent — don't center long paragraphs

### 2.4 Focus and interaction states

Every interactive element must have:
- `:hover` — visible color/shadow/transform change
- `:focus-visible` — ring-2 with brand color, offset-2
- `:active` — subtle press (scale-[0.98] or translate-y-px)
- `:disabled` — opacity-50 + `cursor-not-allowed`

### 2.5 Micro-interactions

- Button CTAs: `transition-all duration-150 ease-out` minimum
- Cards: `hover:shadow-lg hover:-translate-y-0.5 transition` only if card is interactive
- Entrance: consider `motion-safe:animate-in fade-in slide-in-from-bottom-4` on key heroes
- Respect `prefers-reduced-motion` — wrap motion in `motion-safe:` utilities

## Step 3: Before/After Examples

### Example: type polish

Before:
```tsx
<h1 className="text-4xl font-bold">Build faster</h1>
<p className="text-gray-600">Ship features in hours, not weeks.</p>
```

After:
```tsx
<h1 className="text-5xl font-semibold tracking-tight leading-[1.05] text-foreground">
  Build faster
</h1>
<p className="mt-4 text-lg text-muted-foreground leading-relaxed max-w-prose">
  Ship features in hours, not weeks.
</p>
```

### Example: focus state polish

Before:
```tsx
<button className="bg-primary text-white px-4 py-2 rounded">Get started</button>
```

After:
```tsx
<button className="bg-primary text-primary-foreground px-5 py-2.5 rounded-md font-medium
  transition-all duration-150 ease-out
  hover:bg-primary/90 hover:shadow-md
  focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2
  active:scale-[0.98]
  disabled:opacity-50 disabled:cursor-not-allowed">
  Get started
</button>
```

## Step 4: Verify

After edits:
1. `git diff --stat` — expect small surgical diffs, not large rewrites
2. Visual check: run dev server, screenshot the changed areas
3. If `/design-critique` was the source, re-run it on the changed files and compare scores

## Step 5: Report

Summarize the pass:

```
Polished 3 components:
  - Hero.tsx        (5 edits: type scale, focus, micro-interactions)
  - Nav.tsx         (2 edits: hover, focus)
  - PricingCard.tsx (4 edits: spacing, interaction states)

Anti-patterns removed: gradient text (1), default Inter (site-wide)
Focus states added: 12 elements
Critique score projection: 4.3 → 6.8
```

## Gotchas

- **Never restructure** — if a component needs layout change, escalate to `/design-distill` or `/design-variants`
- **One category at a time** — don't interleave typography and spacing edits; harder to verify and revert
- **Design tokens over literals** — never hardcode `#F5F5F5`; use `bg-muted` or the project token
- **Respect existing conventions** — if the codebase uses CSS modules or styled-components, match that; don't introduce Tailwind
- **Small diffs** — if a polish pass produces 500+ line diff, you're over-editing; stop and reconsider

---
name: website-layout
description: "Restructure the layout of an existing website: section order, hero variants, component shapes (cards, bento, lists, splits), spacing density, grid patterns, and section composition. Pure layout — no color, font, or token changes. Use when asked to restructure sections, change layout style, reorganize page flow, or change how components are shaped and arranged."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, WebFetch
argument-hint: "<path to existing website project OR reference URL>"
---

## Overview

Restructures the visual layout of an existing website without touching design tokens (colors, fonts, shadows). Covers: section order, hero variant, component shape patterns (cards, bento, lists, splits), grid layouts, spacing density, and section composition. Produces 3 layout direction proposals, user picks one, then applies structural changes to the codebase.

> **For a full redesign** (theme + layout together), invoke `/website-theme` first, then `/website-layout`.

## External Design Reference (Optional)

If the user provides a Figma URL or live website URL, follow the routing in `references/frontend/design-reference-routing.md`. For layout-only extraction: skip Steps 2-3 when replicating, or use extracted structure as inspiration for the 3 propositions.

## Required References

**Always read these files before generating:**

- `references/frontend/design-archetypes.md` — layout patterns per archetype (grid, density, section shapes)
- `references/frontend/sector-design-intelligence.md` — sector layout recommendations, component matrix
- `references/frontend/block-sources.md` — pre-built blocks and animated components for section restructuring
- `references/frontend/component-variants.md` — canonical variant definitions with JSX structural sketches

## Step 1: Audit Current Layout

Scan the existing site to understand its current layout structure:

- Read all page files (`app/**/page.tsx`) to identify sections and their order
- Read `components/page-hero.tsx` and other section components for current shape patterns
- Read `components/shared-layout.tsx` for nav and footer structure
- Identify: current grid pattern, hero variant, card/list patterns, section density, page flow

Output a structured audit before proposing alternatives:

```
Current layout:
- Hero: [variant — e.g. centered text, split image, full-bleed]
- Sections: [ordered list]
- Component shapes: [cards / lists / bento / splits / etc.]
- Grid pattern: [centered / asymmetric / full-bleed / broken-grid]
- Spacing density: [compact / balanced / spacious]
- What works: [strengths]
- What to improve: [weak points]
```

## Step 2: Generate 3 Layout Propositions

Each proposition must use a **structurally different** layout approach:

- **Proposition A** — sector-standard layout (safe, proven for this industry)
- **Proposition B** — creative alternative (different grid, section shapes, or flow)
- **Proposition C** — bold structural reframe (unexpected but compelling layout)

### Layout Variables to Vary

**Hero variants:**

- `centered` — headline + CTA centered, full-width background
- `split` — text left / visual right (or reversed)
- `full-bleed` — edge-to-edge image/video with overlay text
- `bento` — hero broken into a grid of tiles
- `statement` — oversized single headline, minimal content

For JSX structural sketches of each variant, read `references/frontend/component-variants.md`.

**Section shapes:**

- `card-grid` — 3-col cards with icon/image/text
- `bento-grid` — asymmetric tiles, varied sizes
- `horizontal-split` — alternating left/right text + visual
- `list` — vertical stacked items with dividers
- `masonry` — Pinterest-style uneven columns
- `timeline` — vertical or horizontal chronological flow
- `stats-row` — horizontal metrics band
- `testimonial-carousel` — sliding quotes
- `comparison-table` — side-by-side feature matrix

For JSX structural sketches of each section shape, read `references/frontend/component-variants.md`.

**Grid patterns:**

- `centered` — max-width container, symmetric
- `asymmetric` — uneven column weights (e.g. 60/40)
- `full-bleed` — edge-to-edge, no max-width
- `broken-grid` — elements intentionally overflow their grid lines
- `sidebar` — persistent side panel with scrolling main content

**Spacing density:**

- `compact` — tight padding, more content visible
- `balanced` — standard spacing
- `spacious` — large whitespace, breathing room
- `airy` — extreme whitespace, editorial feel

**Section order patterns:**

- **Standard:** Hero → Features → How it works → Testimonials → Pricing → CTA
- **Problem-first:** Problem → Solution → Features → Social proof → CTA
- **Story-driven:** Hook → Story → Features → Proof → CTA
- **Trust-first:** Logos → Features → Testimonials → Pricing → CTA
- **Portfolio/Creative:** Fullscreen hero → Gallery/Work → About → Contact (no pricing)
- **Product showcase:** Hero → Demo/Video → Features → Comparison → Pricing → CTA
- **Editorial:** Statement hero → Long-form content → Highlights → CTA
- **Minimal landing:** Hero → Single feature block → CTA (3 sections max)

### For Each Proposition, Output:

```
## Proposition [A/B/C]: [Layout Name] — "[2-word feel]"

**Grid:** [pattern] | **Density:** [compact/balanced/spacious/airy]

### Page Structure
1. [Section name] — [shape variant] — [brief description]
2. [Section name] — [shape variant] — [brief description]
...

### Component Shapes
- Hero: [variant]
- Feature section: [shape]
- Testimonials: [shape]
- CTA: [shape]
- Nav: [variant — sticky/transparent/bordered/floating]
- Footer: [variant — minimal/full/split]

### Why This Works
[2-3 sentences on why this layout suits the project and audience]
```

## Step 3: User Chooses

Present all 3 propositions. Ask:

> Which layout direction do you prefer — A, B, C, or a mix?

Wait for selection.

## Step 4: Apply Layout Changes

Once the user chooses:

### 4.1 Restructure Pages

For each page file:

- Reorder section components to match the chosen page flow
- Replace section component variants (e.g. swap `<CardGrid>` for `<BentoGrid>`)
- Update section wrappers with chosen grid pattern and density classes

### 4.2 Update Section Components

Before hand-rolling a new section shape, check `references/frontend/block-sources.md` for a pre-built block that matches the target variant. Install via `npx shadcn@latest add` (shadcn blocks, Magic UI) or fetch via WebFetch (Aceternity). Adapt the block to match existing design tokens rather than writing JSX from scratch.

For each section in the chosen layout:

- Update the JSX structure to match the new shape variant
- Update Tailwind grid classes (`grid-cols-*`, `gap-*`, `col-span-*`)
- Update padding/margin for chosen density
- Update max-width and layout containers

### 4.3 Update Hero

- Implement the chosen hero variant
- Update `components/page-hero.tsx` structure and layout classes

### 4.4 Update Nav & Footer

- Apply the chosen nav variant (sticky, transparent, floating, bordered)
- Apply the chosen footer variant (minimal, full, split)
- Update `components/shared-layout.tsx` structure

### 4.5 Verify

- Check all pages render the correct section order
- Confirm no hardcoded layout values remain that should be dynamic
- Summarize all structural changes made

**Important:** Do not change any design tokens (colors, fonts, shadows, radius) — only structural classes and JSX composition.

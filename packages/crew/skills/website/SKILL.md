---
name: website
description: "Build a production-ready Next.js website. Three modes: (A) Discovery — interactive Q&A → design → content → scaffold → build → polish, (B) Spec-fed — consumes a design-spec.json, skips discovery/design, builds directly, (C) Replicate — consumes a design-spec.json from URL extraction, exact visual match. The canonical 8-step workflow for all website creation in pixl-crew."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Task
argument-hint: "<website description, project brief, Figma URL, reference URL, or path to design-spec.json>"
context: fork
---

## Overview

End-to-end website creation using Next.js with shadcn/ui and Tailwind CSS. Three operating modes:

| Mode             | Input                       | Skips                                    | Use Case                            |
| ---------------- | --------------------------- | ---------------------------------------- | ----------------------------------- |
| **A: Discovery** | Description or brief        | Nothing                                  | New site from scratch               |
| **B: Spec-fed**  | `design-spec.json`          | Steps 1-2 (discovery + design)           | New site from extracted design      |
| **C: Replicate** | `design-spec.json` from URL | Steps 1-3 (discovery + design + content) | Exact reproduction of existing site |

## Mode Detection

- If input is a path to `design-spec.json` → check `meta.source_type`:
  - `"url"` → default to Mode C (replicate), confirm with user
  - `"figma"` or `"screenshot"` → Mode B (spec-fed)
  - `"discovery"` → Mode A (should not happen, but treat as A)
- If input is a Figma URL or website URL → run `/design-extraction` first, then re-enter with the resulting spec
- If input is a text description → Mode A (discovery)

## Mode A: Full Discovery Pipeline

Runs all 8 steps below (Steps 1 through 8).

## Mode B: Spec-Fed

1. Read the `design-spec.json`
2. Skip Steps 1-2 (discovery and design) — the spec IS the design system
3. Run Step 3 (Content) — generate content based on spec's `meta` and `pages` structure
4. Continue with Steps 4-8 (scaffold → build → components → blog → polish)

## Mode C: Replicate

1. Read the `design-spec.json` — must contain `pages[].sections[].content`, `pages[].sections[].screenshot_path`, and `assets.local_manifest` (produced by `/design-extraction` phases 7-9)
2. Skip Steps 1-3 (discovery, design, AND content) — all text comes from scraped `content` fields
3. **Copy downloaded assets** — copy `./output/assets/*` to `public/assets/` in the project, reference images as `/assets/images/filename`, fonts as `/assets/fonts/filename`
4. Continue with Steps 4-8 (scaffold → build → components → blog → polish) with the following Mode C overrides:

### Mode C Overrides for Steps 5-8

- **Step 5 override:** In Mode C, read sections from `spec.pages[].sections[]` (NOT from Step 2 design output). Content comes from `spec.pages[].sections[].content` (NOT from Step 3 content agent). Context packet must include `screenshot_path` per section and `assets.local_manifest` mapping.
- **Step 6 override:** In Mode C, use `spec.variants.*` for nav/footer variants directly. Do NOT re-select variants from archetype via `component-variants.md`.
- **Step 8 override:** In Mode C, run the visual regression loop (see `references/frontend/visual-regression.md`) as the primary quality gate. Compare against archived Phase 1 screenshots (not live URL) to avoid dynamic content drift.
- **Asset fallback:** If an image in `content.images[].src` has no matching entry in `assets.local_manifest.files[]`, use a sized placeholder `<div>` with the original dimensions and a `<!-- TODO: asset not downloaded -->` comment.

### Section-by-Section Generation

Instead of building all sections at once, each section gets its own generation context:

For each section in `pages[].sections[]`:

1. **Visual target:** Read the section's cropped screenshot (`screenshot_path`) — this is what the output must look like
2. **Exact content:** Use the section's `content` object — `headings`, `paragraphs`, `ctas`, `images`, `lists`
3. **Design tokens:** Apply the spec's `theme`, `typography`, `layout`, and `motion` tokens
4. **Asset paths:** Map `content.images[].src` to local paths via `assets.local_manifest.files[]`
5. **Build the section component** matching the visual target as closely as possible

**Anti-hallucination rule:** If `content` is missing for a section, use `{/* TODO: content not scraped */}` as a placeholder — NEVER fabricate copy. All visible text must come from the `content` fields or `meta.firecrawl_content`.

### Visual Regression Loop

See `references/frontend/visual-regression.md` for the full visual regression loop protocol (agent-browser screenshots → pixel diff → threshold evaluation → iteration).

---

## Step 1: Discovery (Mode A only)

Gather website requirements through interactive Q&A:

1. Identity: brand name, tagline, value proposition
2. Visual: colors, fonts, style preferences, mood
3. Pages: which pages and their purpose
4. Features: blog, forms, API routes, i18n
5. Content: copy source, tone, target audience
6. Data sources: CMS, APIs, static files
7. Infrastructure: hosting, domain, analytics

## Steps 2 + 3: Design System & Content (Parallel Wave)

After Step 1 (Discovery) completes, you MUST spawn the following 2 agents in parallel via the `Task` tool. Do NOT run these sequentially — design and content have no dependencies on each other; both depend only on the discovery output.

### Pre-wave: Discovery Packet

Before spawning agents, compile a **discovery packet** containing:

- All discovery outputs (brand identity, visual preferences, pages, features, content tone, sector)
- The project directory path
- Any user-provided reference URLs or Figma links

### Parallel Wave — Design + Content (2 parallel Task agents)

| Agent | Role           | Responsibility                                                                                                                                                                                                                                     |
| ----- | -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A     | designer       | Execute Step 2 (Design System) below — read design archetypes, sector intelligence, reference URL. Output `design.output` with all tokens and variant selections. **File ownership:** design token files only. DO NOT write content or copy files. |
| B     | content-writer | Execute Step 3 (Content) below — generate page copy, SEO metadata from brand info and discovery output. Output `content.output` with all page content. **File ownership:** content files only. DO NOT write design token files.                    |

Each agent prompt MUST include:

- The full discovery packet
- Its assigned step instructions (Step 2 or Step 3, as documented below)
- Explicit anti-conflict guard: "You MUST NOT create or modify any files outside your assigned responsibility"

### Post-wave: Merge

After both agents complete, the coordinator merges `design.output` and `content.output` into the tokens file for Step 4 (Scaffold). Verify both outputs are complete before proceeding.

---

### Step 2: Design System (Agent A)

Generate a unique, sector-appropriate design system. **Read the design references first.**

##### Required References

- `references/frontend/design-archetypes.md` — 12 archetypes with complete token sets
- `references/frontend/sector-design-intelligence.md` — sector mappings, color psychology, layout patterns
- `references/frontend/design-resources.md` — color formulas, typography scales, font catalog
- `references/frontend/component-variants.md` — named structural variants per component category

##### Procedure

This step walks through archetype selection, color palette generation, typography pairing, spacing/shape/motion/shadow token definition, component variant selection, and ui-layouts browsing. The output is a complete `design.output` object with every token populated.

For the complete design system procedure (archetype selection, color palette, typography, spacing, motion, shadows, layout variants, component variants, design brief compilation, ui-layouts browsing), read `references/frontend/website-design-system.md`.

##### Output Schema (top-level keys)

```yaml
design.output:
  archetype: "..."
  colors: { primary_hsl, secondary_hsl, accent_hsl, surface_hsl }
  typography: { font_sans, font_serif, font_sans_import, font_serif_import, font_serif_weight, heading_font }
  shape: { border_radius }
  shadows: { sm, md, lg }
  motion: { duration_micro, duration_page, ease, distance, stagger }
  layout: { nav_classes, footer_classes, section_padding, max_width }
  variants: { hero, nav, footer, features, testimonials, cta, pricing }
```

**Every token must have a value. Every variant must be explicitly selected.** Do not leave any token empty or undefined. Do not default every project to the same variant combination.

---

### Step 3: Content (Agent B)

Generate website copy:

1. Page-by-page content strategy
2. Hero, features, testimonials, CTA copy
3. SEO metadata per page
4. Optional translations for configured locales

Output a structured `content.output` object with all page content organized by section.

---

## Step 4: Scaffold

Initialize the project from studio templates using the bulk scaffold script:

1. **Write tokens file** — Create `/tmp/<project-slug>-tokens.txt` with one `KEY=VALUE` per line for every token from discovery and design output (see `studio/stacks/nextjs/manifest.yaml` `token_registry` for the full list)
2. **Run scaffold** — Execute: `bash scripts/scaffold.sh studio/stacks/nextjs/ <project-dir> /tmp/<project-slug>-tokens.txt`
3. **Install & verify** — Run `npm install && npx tsc --noEmit` to confirm a clean build
4. **Spot-check** — Read `lib/design-config.ts` and `app/globals.css` to verify tokens were replaced correctly

## Step 5: Build Sections (Parallel Waves)

**You MUST spawn parallel sub-agents via the `Task` tool.** Do NOT build sections sequentially in the main context — this wastes turns and loses the quality benefits of isolated agent contexts. For parallel spawning patterns, see `references/methodology/parallel-execution.md`.

### Pre-wave: Context Packet

See `references/orchestration/context-packet.md` for the canonical format. For projects with 4+ parallel agents, write the packet to `.context/design-tokens.json`.

Before spawning agents, compile a **context packet** string containing:

- All design token values from `lib/design-config.ts`
- **Selected component variant names** from Step 2.8 (hero, nav, footer, features, testimonials, cta, pricing)
- Content/copy for each section from Step 3
- CSS variable contract (shadow, duration, ease variable names)
- Section building rules (below)
- The archetype name and personality notes

**CRITICAL:** Do NOT copy the full JSX sketches from `references/frontend/component-variants.md` into each agent prompt. Instead, pass only the variant name (e.g., `hero: split`) and instruct each agent to `Read references/frontend/component-variants.md` and find its variant's structural sketch. This avoids multiplying 800+ lines across 3-5 agents.

### Wave 1 — Core Sections (2-3 parallel Task agents, dynamic)

**Do NOT hardcode a fixed section-to-agent mapping.** Instead, read the section list from the design output (Step 2) and distribute sections evenly across 2-3 `general-purpose` sub-agents:

1. Collect all sections from the design brief's page structure (e.g., hero, features, testimonials, pricing, cta, demo, comparison, gallery — whatever was designed)
2. Distribute sections evenly: if 6 sections → 2 per agent (3 agents); if 4 sections → 2 per agent (2 agents)
3. Assign each agent its section files under `components/sections/`

Example (for a standard SaaS page with 5 core sections):

| Agent | Files                                                              | Sections        |
| ----- | ------------------------------------------------------------------ | --------------- |
| A     | `components/sections/hero.tsx`, `components/sections/features.tsx` | Hero + Features |
| B     | `components/sections/testimonials.tsx`                             | Testimonials    |
| C     | `components/sections/pricing.tsx`, `components/sections/cta.tsx`   | Pricing + CTA   |

Example (for a portfolio page with 4 sections):

| Agent | Files                                                              | Sections        |
| ----- | ------------------------------------------------------------------ | --------------- |
| A     | `components/sections/hero.tsx`, `components/sections/gallery.tsx`  | Hero + Gallery  |
| B     | `components/sections/about.tsx`, `components/sections/contact.tsx` | About + Contact |

Each agent prompt MUST include:

- The full context packet
- Its assigned files (and ONLY those files)
- The variant name for each of its sections (from Step 2.8)
- Explicit instruction: "DO NOT create or modify any files outside your assigned list"

### Wave 2 — Conditional Sections (1-2 parallel Task agents)

Spawn only if the design brief includes additional sections not covered in Wave 1:

| Agent | Condition                      | Files                                                                                           |
| ----- | ------------------------------ | ----------------------------------------------------------------------------------------------- |
| D     | Contact form requested         | `components/sections/contact.tsx`                                                               |
| E     | FAQ, stats, or logos requested | `components/sections/faq.tsx`, `components/sections/stats.tsx`, `components/sections/logos.tsx` |

### Integration

After both waves complete:

1. Import all built sections into `app/page-client.tsx`
2. Run `npx tsc --noEmit` to verify

### Section Building Rules

- **Always implement the selected variant** — read the structural sketch from `references/frontend/component-variants.md` and build that specific layout, not a generic default
- **Always use CSS variables** for shadows (`var(--shadow-sm)`), animation timing (`var(--duration-micro)`), and easing (`var(--ease-default)`)
- **Always use the design config** for section padding, max-width, and border radius
- **Never hardcode** `py-16`, `max-w-7xl`, `rounded-xl`, specific shadow values, or fixed animation durations directly in section code
- **Never copy the scaffolded template as-is** — templates like `page-hero.tsx.tmpl` and `shared-layout.tsx.tmpl` are starting points. Agents MUST rewrite them to match the selected variant structure. The template exists for token replacement only; the layout must be rebuilt per variant.
- Refer to `references/frontend/sector-design-intelligence.md` for section order and layout patterns appropriate to the sector

## Step 6: Components (Parallel Waves)

**You MUST assemble shared components using parallel sub-agents via the `Task` tool.** Do NOT build nav and footer sequentially in the main context.

### Wave 1 — Layout Components (2 parallel Task agents)

| Agent | Files                   | Details                                                                                                                                   |
| ----- | ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| A     | `components/nav.tsx`    | Navigation — use selected `variants.nav` structure from `component-variants.md` (NOT always a bar nav). Apply `NAV_CLASSES` for styling.  |
| B     | `components/footer.tsx` | Footer — use selected `variants.footer` structure from `component-variants.md` (NOT always 4-column). Apply `FOOTER_CLASSES` for styling. |

Each agent receives the context packet from Step 5 (design tokens + archetype).

### Wave 2 — Conditional Components (1 agent, if needed)

| Agent | Condition                                 | Files                                                                         |
| ----- | ----------------------------------------- | ----------------------------------------------------------------------------- |
| C     | CTA blocks, galleries, or forms requested | `components/cta-block.tsx`, `components/gallery.tsx`, `components/form-*.tsx` |

### Integration

After waves complete:

1. Import nav and footer into `app/layout.tsx` (or `components/shared-layout.tsx`)
2. Run `npx tsc --noEmit` to verify

## Step 7: Blog (Conditional)

**Only if blog is requested in discovery.**

1. MDX content setup
2. Blog listing page
3. Blog post template
4. RSS feed

## Step 8: Production Polish

1. SEO: metadata, Open Graph, structured data, sitemap, robots.txt
2. Performance: image optimization, font loading, bundle analysis
3. Accessibility: WCAG 2.1 AA audit
4. Final review: responsive check, cross-browser test
5. **Self-review** (optional): Spawn a sub-agent with `/self-review-fix-loop` to run an automated quality pass over all changed files. This catches issues across section boundaries that individual agents may have missed.

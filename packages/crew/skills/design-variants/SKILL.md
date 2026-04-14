---
name: design-variants
description: "Generate N distinct visual design variants for comparison. Creates multiple HTML previews with different aesthetics, layouts, or approaches. Use when exploring design directions, comparing visual options, or when asked for design alternatives."
allowed-tools: Read, Bash, Glob, Grep, Write, Edit, Agent
argument-hint: "<component or page> [--count N]"
---

## Overview

Visual exploration tool that generates multiple distinct design variants for side-by-side comparison. Each variant takes a meaningfully different approach — not just color swaps, but different layouts, typography scales, visual hierarchies, and interaction patterns.

**How this differs from other skills**:
- `/website-theme` — applies a single chosen theme. This skill generates multiple options for comparison.
- `/design-extraction` — extracts tokens from existing designs. This skill creates new design directions.
- `/frontend-design` — builds a single high-quality component. This skill generates N variants for exploration.

## Step 1: Understand the Target

Determine what to generate variants for:

- **Component**: A specific UI element (hero section, pricing table, navigation, card grid)
- **Page**: A full page layout (landing page, dashboard, settings page)
- **Section**: A page section (CTA, features grid, testimonials)

Gather context:
1. Read existing design tokens if available (`design-config.ts`, `tailwind.config.*`, CSS variables)
2. Check for brand guidelines or existing components
3. Understand the content: what text, images, and data will populate the design?

If no context is available, ask the user for: purpose, audience, and tone (professional, playful, minimal, bold).

## Step 2: Define Variant Directions

Generate N distinct directions (default: 3, max: 6). Each must differ meaningfully:

| Variant | Archetype | Characteristics |
|---------|-----------|-----------------|
| A | **Minimal** | Lots of whitespace, subtle typography, muted colors, clean lines |
| B | **Bold** | Strong typography scale, vivid colors, asymmetric layouts, motion hints |
| C | **Editorial** | Magazine-like, mixed media, strong grid, serif/sans pairing |
| D | **Brutalist** | Raw, high-contrast, monospace, visible grid, intentionally rough |
| E | **Organic** | Rounded shapes, warm palette, flowing layouts, nature-inspired |
| F | **Tech** | Dark mode, neon accents, code-inspired, sharp edges, data-heavy |

Select directions based on the target audience and purpose. Don't always default to A/B/C — choose directions that are genuinely useful for the context.

## Step 3: Generate Variants

For each variant, create a self-contained HTML file:

```bash
VARIANT_DIR=".variants"
mkdir -p "$VARIANT_DIR"
```

Each file should be:
- **Self-contained**: Single HTML file with inline CSS (no external dependencies except CDN fonts)
- **Responsive**: Works at desktop and mobile widths
- **Real content**: Use actual text and placeholder images, not lorem ipsum
- **Interactive**: Include hover states and basic transitions
- **Labeled**: Header banner identifying the variant name and direction

Write each variant:
```
.variants/
  variant-a-minimal.html
  variant-b-bold.html
  variant-c-editorial.html
```

### Variant Quality Rules

- Each variant must look intentionally designed — no "default Bootstrap" or "generic template" aesthetics
- Typography must be deliberate: choose specific font pairings, not just system fonts
- Color must be cohesive: 1 primary, 1 accent, 2-3 neutrals per variant
- Spacing must be consistent: use a scale (4, 8, 12, 16, 24, 32, 48, 64, 96)
- Every variant must be production-plausible, not a rough sketch

### Archetype & Anti-Slop Requirements

- **Distinct archetype per variant.** Each generated variant MUST map to a distinct named archetype from `references/frontend/design-archetypes.md` (the 12 core + 4 extended: Industrial Brutalist, Minimalist, Soft, Stitch). Two variants mapping to the same archetype is a failure.
- **Anti-pattern check.** Every variant MUST pass the anti-patterns check in `references/frontend/design/anti-patterns.md`. Before writing the HTML, grep your own tokens for banned fonts (Inter, Roboto, Arial), banned patterns (gradient text, pure `#000`/`#fff`, side-stripe accent borders, centered-hero + 3-card-grid), and banned copy ("Elevate", "Seamless", "Unleash", "John Doe", "Acme Corp").
- **Variant labels call out archetype.** Each variant's report header must name its archetype, e.g. `Variant A — Industrial Brutalist (Telemetry)`, `Variant B — Soft (Editorial Luxury)`, `Variant C — Stitch (Creativity 9 / Density 3)`.

## Step 4: Generate Comparison Board

Create an index page that shows all variants side-by-side:

```bash
# .variants/compare.html
```

The comparison board should:
- Show all variants in a grid or tabbed interface
- Allow toggling between desktop and mobile preview widths
- Include a brief description of each direction's design rationale
- Have a "Pick this one" annotation area for each

## Step 5: Present to User

```
Generated 3 design variants in .variants/

  A. Minimal — Clean, spacious, muted. Best for: professional B2B.
  B. Bold — Vivid, energetic, asymmetric. Best for: consumer products, startups.
  C. Editorial — Magazine-style, rich typography. Best for: content-heavy, storytelling.

  Open comparison: .variants/compare.html
  
  Individual previews:
  - .variants/variant-a-minimal.html
  - .variants/variant-b-bold.html
  - .variants/variant-c-editorial.html

Which direction would you like to develop further?
```

## Step 6: Iterate (on user feedback)

When the user picks a variant or gives feedback:
1. If they pick one: hand off to `/website-theme` or `/frontend-design` to implement it
2. If they want to mix: create a new variant combining elements from their favorites
3. If none work: ask what's missing, generate 2-3 new directions

## Gotchas

- Generating 6 variants takes significant tokens — default to 3 unless asked for more
- CDN fonts (Google Fonts) require network access — fall back to system fonts if offline
- Self-contained HTML files can be large — keep each under 500 lines
- Don't generate variants that are too similar — if two look like the same design with different colors, that's a failure
- Real content matters — a beautiful design with "Lorem ipsum" tells you nothing about how it actually reads
- Image placeholders should use https://placehold.co/ or solid color blocks, not broken image links

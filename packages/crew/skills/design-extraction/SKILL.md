---
name: design-extraction
description: "Extract design tokens and layout structure from Figma URLs, websites, or screenshots into a design-spec.json. Use when implementing a new site from a visual source or redesigning an existing one."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
argument-hint: "<figma URL, website URL, or screenshot path> [path to existing project]"
---

## Overview

Extracts design tokens and layout structure from three input types and outputs a `design-spec.json`:

- **Figma URL** (`figma.com/design/...` or `figma.com/file/...`) — reads the design via Figma API
- **Live website URL** (any other URL) — captures and analyzes via `agent-browser` CLI following `references/frontend/url-design-extraction.md`
- **Screenshot / image file** — visual analysis of a provided image

**Output:** Always a `design-spec.json` conforming to `references/frontend/design-spec-schema.md`.

**Two modes after extraction:**

- **Implement mode** — design source only → extract → `design-spec.json` → build new site via `/website` Mode B (spec-fed) or Mode C (replicate)
- **Redesign mode** — design source + existing project path → extract → `design-spec.json` → apply to existing site via `/website-theme` then `/website-layout`

## Prerequisites

- For Figma URLs: Figma API access must be configured
- For live website URLs: `agent-browser` CLI must be available (`npm install -g agent-browser`)
- For Mode C replication: `npx firecrawl` recommended for content scraping (optional — falls back to DOM extraction)
- For redesign mode: target project must already exist

## URL Type Detection

Detect the input type and route accordingly:

- **Figma URL** (`figma.com/design/...` or `figma.com/file/...`) → Step 1 (Figma extraction)
- **Live website URL** (any other URL) → Step 2 (URL extraction)
- **Screenshot / image file** (local path ending in `.png`, `.jpg`, `.webp`) → Step 3 (Visual extraction)

---

## Step 1: Extract from Figma

### 1.1 Parse the Figma URL

Extract the file key and node ID from the URL:

- File key: the segment after `/design/` or `/file/`
- Node ID: from `node-id=` query parameter (optional — if absent, use the root)

### 1.2 Read the Figma File

Use the Figma API tools to inspect the design:

1. **Get file metadata** — file name, pages, top-level frames
2. **Get the target node** (or root frame) — inspect its children to understand the page structure
3. **Extract styles and variables:**
   - Colors (fills, strokes) → `theme.colors`
   - Typography (font families, sizes, weights, line heights) → `typography`
   - Spacing (padding, gaps, auto-layout settings) → `layout`
   - Border radius → `theme.border_radius`
   - Effects (shadows, blurs) → `theme.shadows`
4. **Extract layout structure:**
   - Top-level sections in order → `pages[].sections`
   - Component patterns — cards, grids, splits
   - Navigation and footer patterns → `components.navbar`, `variants.footer`
   - Hero variant → `variants.hero`

### 1.3 Build design-spec.json

Map all extracted Figma data to the spec schema (`references/frontend/design-spec-schema.md`):

- Set `meta.source_type` to `"figma"`
- Convert Figma hex colors to HSL for `theme.colors`
- Match Figma fonts to Google Fonts (see Font Mapping below)
- Detect closest archetype by comparing tokens against `references/frontend/design-archetypes.md`
- Map Figma auto-layout gaps to Tailwind gap classes
- Map Figma frame padding to section padding tokens

Write spec to `./output/design-spec.json`.

→ Continue to Step 4 (Mode Selection).

---

## Step 2: Extract from Live URL

Follow the complete pipeline in `references/frontend/url-design-extraction.md`:

1. **Phase 1:** Homepage capture + multi-viewport screenshots + CSS tokens + font inventory + layout structure
2. **Phase 2:** Multi-page navigation (3+ additional pages)
3. **Phase 3:** Component-level deep extraction (buttons, cards, headings, badges) + motion/animation extraction + hover states + asset inventory
4. **Phase 4:** Content inventory
5. **Phase 5:** Compile `design-spec.json` (set `meta.source_type` to `"url"`)
6. **Phase 6:** Implementation overlay plan
7. **Phase 7:** Firecrawl content scraping (Mode C only) — scrape exact text content per section
8. **Phase 8:** Asset download (Mode C only) — download images, fonts, backgrounds to local paths
9. **Phase 9:** Per-section screenshots (Mode C only) — crop individual section screenshots as visual targets

For Mode C replication, all 9 phases are required. For Mode B or redesign, phases 1-6 are sufficient (phases 7-9 can be skipped).

Write spec to `./output/design-spec.json`.

→ Continue to Step 4 (Mode Selection).

---

## Step 3: Extract from Screenshot

Use visual analysis of the provided image:

1. **Read the image** — identify overall mood, color palette, layout structure
2. **Extract colors** — sample dominant colors, map to primary/secondary/accent/surface
3. **Identify typography** — estimate font categories (sans/serif/mono), weights, sizes
4. **Map layout** — section types, grid patterns, component shapes
5. **Detect archetype** — match visual style against `references/frontend/design-archetypes.md`
6. **Build design-spec.json** — set `meta.source_type` to `"screenshot"`, fill what can be determined visually, leave ambiguous fields with best-guess values

Write spec to `./output/design-spec.json`.

→ Continue to Step 4 (Mode Selection).

---

## Step 4: Mode Selection

### If no existing project path provided → Implement Mode

Present the extracted spec summary to the user:

```
## Extracted Design Spec

- Source: [URL/Figma/screenshot]
- Archetype: [detected]
- Mode: [dark/light]
- Colors: [primary] / [secondary] / [accent]
- Fonts: [heading] + [body]
- Hero: [variant]
- Sections: [count] across [page count] pages
```

Ask: **"Should I replicate this design exactly (Mode C) or use it as the design system for a new site (Mode B)?"**

- **Replicate (Mode C)** → Pass spec to `/website` with mode=replicate. The spec drives everything — no discovery, no propositions, exact match.
- **New site (Mode B)** → Pass spec to `/website` with mode=spec-fed. The spec provides the design system, but content and structure may differ.

### If existing project path provided → Redesign Mode

1. Audit the existing site (read `app/globals.css`, `app/layout.tsx`, `lib/design-config.ts`, section components)
2. Present comparison: current design vs. extracted spec
3. Ask: "Should I apply this design to the existing project?"
4. On confirmation, invoke `/website-theme` with the `design-spec.json` token values, then `/website-layout` with the layout structure (skip propositions, apply directly)

---

## Font Mapping Reference

Figma/computed fonts may not be available on Google Fonts. Fallback strategy:

1. Exact match on Google Fonts → use directly
2. Same foundry alternative → substitute with note
3. Visual equivalent → find closest match by x-height, weight range, and character
4. Always validate availability against `references/frontend/design-resources.md` font catalog

## Color Conversion Reference

Figma uses hex/RGBA. Computed styles use RGB. Convert to HSL for the token system:

- `#RRGGBB` → `H S% L%` using standard conversion
- `rgb(r, g, b)` → normalize to 0-1 → compute H, S, L
- For fills with opacity, factor alpha into the lightness calculation
- Validate WCAG contrast ratios: primary text on surface must be >= 4.5:1

## Tips

- Figma auto-layout `gap` values map directly to Tailwind `gap-*` classes
- Figma frame padding maps to section padding tokens
- Figma component variants often map to shadcn/ui component variants
- If the Figma file uses a design system with variables, prefer those over inspecting individual fills
- Multiple pages in Figma may represent different routes — check the page names
- For Framer sites, the visual fallback in `url-design-extraction.md` is often needed since Framer obfuscates class names

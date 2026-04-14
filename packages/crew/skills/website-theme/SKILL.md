---
name: website-theme
description: "Apply a complete design theme to an existing website: colors, fonts, radius, shadows, motion, nav/footer variants. Proposes 3 archetype-based theme directions, user picks one, then applies all tokens to the codebase. Pure theming — no layout or section restructuring. Use when asked to retheme, recolor, change fonts, or reskin an existing site."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, WebFetch
argument-hint: "<path to existing website project OR design preferences OR reference URL>"
---

## Overview

Generates 3 distinct theme propositions for an existing website, each based on a different archetype. The user picks one (or mixes), and the skill applies all design tokens to the codebase. Covers colors, typography, radius, shadows, motion, and nav/footer style — no layout or section restructuring.

> **For a full redesign** (theme + layout together), invoke `/website-theme` first, then `/website-layout`.

## External Design Reference (Optional)

If the user provides a Figma URL or live website URL, follow the routing in `references/frontend/design-reference-routing.md`. For theme-only extraction: skip Steps 2-3 when matching/replicating, or use extracted tokens as inspiration for the 3 propositions.

## Required References

**Always read these files before generating:**
- `references/frontend/design-archetypes.md` — 12 core archetypes + **4 new extended archetypes** now available: `Industrial Brutalist`, `Minimalist` (editorial utility), `Soft` (Awwwards-tier), `Stitch` (tunable taste standard). These carry deeper motion, typographic, and anti-pattern guidance than the core 12 — use them when the core archetypes feel generic for the brief.
- `references/frontend/sector-design-intelligence.md` — sector mappings, color psychology, layout patterns
- `references/frontend/design-resources.md` — color formulas, typography scales, font catalog
- `references/frontend/block-sources.md` — animated components that match archetype personalities

> **Anti-Slop Guard:** Theme propositions MUST avoid every font, pattern, and device banned in `references/frontend/design/anti-patterns.md`. Before presenting the 3 propositions, cross-check each against the anti-pattern list — if any proposition relies on a banned font (Inter/Roboto/Arial) or banned pattern (gradient text, pure black/white, side-stripe borders, generic thin-stroke icons), replace it.

## Step 1: Audit Current Theme

Read the existing site to understand what's already there:
- `app/globals.css` — current CSS custom properties (colors, radius, shadows)
- `app/layout.tsx` — current font imports
- `lib/design-config.ts` (if exists) — archetype and layout config

Identify: current archetype, colors in use, font pair, shadow style, radius, motion personality.
Output a brief audit summary before proceeding.

## Step 2: Generate 3 Theme Propositions

Each proposition must use a **different archetype** and produce a visually distinct result:
- **Proposition A** — sector-recommended archetype (safe, proven)
- **Proposition B** — contrasting archetype that still fits the sector (creative alternative)
- **Proposition C** — bold/unexpected reframe (ambitious direction)

All 3 must differ from the current design. Each must use different font pairs and different color harmonies.

### For Each Proposition, Output:

```
## Proposition [A/B/C]: [Archetype Name] — "[2-word personality]"

**Archetype:** [name] | **Mood:** [description]

| Property | Value |
|----------|-------|
| Colors | Primary: `H S% L%` / Secondary: `H S% L%` / Accent: `H S% L%` |
| Fonts | [Sans Name] + [Serif Name] — headings in [sans/serif] |
| Radius | [N]px |
| Shadows | [none / subtle / dramatic / hard offset] |
| Motion | [snappy / smooth / cinematic / bouncy / instant] |
| Nav | [pill / bar / transparent / bordered] |
| Footer | [dark / light / muted] |

[2-3 sentences on why this archetype fits the project]
```

**Diversity guarantee:**
- Different primary hue ranges (at least 60° apart)
- No shared fonts between propositions
- No repeated archetypes
- At least 2 of 3 nav/footer variants must differ

## Step 3: User Chooses

Ask the user which proposition to apply (A, B, C, or a mix). Wait for selection.

## Step 4: Build Complete Token Set

From the chosen proposition, resolve ALL tokens:

### Colors
- `primary_hsl`, `secondary_hsl`, `accent_hsl`, `surface_hsl`
- Validate WCAG contrast before finalizing

### Typography
- `font_sans` / `font_sans_import` — exact `next/font/google` import name
- `font_serif` / `font_serif_import` — exact `next/font/google` import name
- `font_serif_weight` — quoted weight string (e.g. `"400;700"`)
- `heading_font` — `"sans"` or `"serif"`

### Shape
- `border_radius` — CSS value (e.g. `8px`)

### Shadows
- `sm`, `md`, `lg` — resolved CSS box-shadow values

### Motion
- `duration_micro`, `duration_page`, `ease` (cubic bezier), `distance`, `stagger`

### Layout
- `nav_classes`, `footer_classes`, `section_padding`, `max_width`

## Step 5: Apply Tokens to Codebase

### 5.1 `app/globals.css` — CSS Custom Properties

Update BOTH `:root` (light) and `.dark` blocks.

**Token → CSS Variable mapping** (from `globals.css.tmpl`):

| Token | CSS Variable | Format |
|-------|-------------|--------|
| `primary_hsl` | `--primary` | `H S% L%` (bare, no `hsl()`) |
| `secondary_hsl` | `--secondary` | `H S% L%` |
| `accent_hsl` | `--accent` | `H S% L%` |
| `surface_hsl` | `--muted`, `--border`, `--input` | `H S% L%` |
| `border_radius` | `--radius` | CSS value (e.g. `8px`) |
| `shadow_sm/md/lg` | `--shadow-sm/md/lg` | Full CSS box-shadow |
| `duration_micro/page` | `--duration-micro/page` | e.g. `200ms` |
| `ease` | `--ease-default` | `cubic-bezier(...)` |

❌ WRONG: `--primary: hsl(217, 91%, 60%);`
✅ CORRECT: `--primary: 217 91% 60%;`

**CRITICAL:** Update BOTH `:root` AND `.dark` blocks. Missing dark mode is the #1 cause of broken themes. In dark mode:
- `--primary`, `--secondary`, `--ring` use the same hue values
- `--muted` shifts to `0 0% 15%` (dark neutral)
- `--border`, `--input` shift to `0 0% 18%`
- `--accent` shifts to `0 0% 15%`

### 5.2 `app/layout.tsx` — Font Imports

**WARNING:** `next/font/google` uses underscores for multi-word fonts. `Playfair_Display`, NOT `Playfair Display`.

Replace the existing font constructors:
```tsx
import { Inter, Playfair_Display } from "next/font/google";
const fontSans = Inter({ subsets: ["latin"], variable: "--font-sans" });
const fontSerif = Playfair_Display({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--font-serif",
});
```

Update the `<body>` className to include both variables.

### 5.3 `lib/design-config.ts` — Runtime Config

Update `archetype`, `navClasses`, `footerClasses`, `sectionPadding`, `maxWidth`.

### 5.4 `components/shared-layout.tsx` — Nav/Footer Classes

Replace nav className with resolved `nav_classes` value.
Replace footer className with resolved `footer_classes` value.

### 5.5 `lib/animations.ts` — Motion Values

Update `durationMicro`, `durationPage`, `ease`, `distance`, `stagger`.

### 5.6 Hardcoded Value Scan

Run these greps and replace any hits with CSS variable references:
```bash
grep -rn 'rounded-\(xl\|lg\|md\|2xl\)' components/  # → rounded-[var(--radius)]
grep -rn 'shadow-\(sm\|md\|lg\)' components/          # → shadow-[var(--shadow-md)]
grep -rn 'duration-\[' components/                     # → var(--duration-micro)
```

### 5.7 Suggest Animated Component Enhancements (Optional)

If the new archetype has strong personality (Bold, Aurora, Glassmorphism, Cyberpunk, Playful), suggest animated component upgrades from `references/frontend/block-sources.md` that match the archetype:

- List 3-5 Magic UI or Aceternity components that would elevate the new theme
- Provide install commands for each
- Note which existing sections they would enhance (e.g., "Replace static logo bar with Magic UI `marquee` for animated scrolling logos")

Present suggestions to the user — do NOT install automatically (this is a theme skill, not a layout skill).

## Step 6: Verification

- [ ] No `{{` tokens remain: `grep -rn '{{' app/ lib/ components/`
- [ ] No hardcoded HSL in globals.css outside `:root`/`.dark` blocks
- [ ] Dark mode has matching updates for all color variables
- [ ] `npx tsc --noEmit` passes
- [ ] Font renders correctly (check browser dev tools → Computed → font-family)

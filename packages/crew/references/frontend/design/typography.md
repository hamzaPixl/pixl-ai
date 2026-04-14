---
title: Typography
domain: frontend/design
source: adapted from impeccable (github.com/pbakaus/impeccable, Apache-2.0)
---

# Typography

Typography is the fastest tell of AI-generated UI. Distinctive typography requires rejecting the defaults, committing to a scale, and using fewer sizes with more contrast.

## Vertical Rhythm

Line-height is the base unit for ALL vertical spacing. Body at `line-height: 1.5` on `16px` → 24px → every vertical spacing should be a multiple of 24px. Text and space share one mathematical foundation.

## Modular Scale & Hierarchy

Common failure: too many sizes, too close together (14 / 15 / 16 / 18). Muddy hierarchy. **Use fewer sizes with more contrast** — a 5-step system covers most needs:

| Role | Ratio | Use |
|------|-------|-----|
| xs   | 0.75rem | Captions, legal |
| sm   | 0.875rem | Secondary UI, metadata |
| base | 1rem | Body |
| lg   | 1.25–1.5rem | Subheads, lead text |
| xl+  | 2–4rem | Headlines, hero |

Ratios: 1.25 (major third), 1.333 (perfect fourth), 1.5 (perfect fifth). Pick one and commit. Aim for at least a **1.25 ratio** between steps.

## Readability & Measure

- Cap body lines at **65–75ch** (`max-width: 65ch`).
- Line-height scales **inversely** with line length: narrow column → tighter leading, wide column → more.
- Light text on dark background: add **0.05–0.1** to normal line-height. Light type reads as lighter weight and needs more breathing room.

## Font Selection: Reject the Defaults

The common AI failure: picking the same "tasteful" font for every editorial brief, the same "modern" font for every tech brief. The right font matches *this specific* brand, audience, and moment.

**Reflex fonts to reject** (training-data defaults that create monoculture):

> Inter, Roboto, Arial, Open Sans, DM Sans / DM Serif, Plus Jakarta Sans, Outfit, Instrument Sans / Serif, IBM Plex (Sans/Serif/Mono), Space Mono / Space Grotesk, Fraunces, Newsreader, Lora, Crimson (Pro/Text), Playfair Display, Cormorant / Garamond, Syne.

Rejection alone is not enough — do not just switch to your second-favorite. See `anti-patterns.md` for the full ban list.

### Procedure (do this BEFORE typing any font name)

1. Read the brief. Write 3 concrete words for the brand voice — not "modern" or "elegant" (dead categories). Try "warm and mechanical and opinionated" or "calm and clinical and careful."
2. Imagine the font as a physical object: typewriter ribbon, hand-painted shop sign, 1970s mainframe manual, fabric label, children's book on cheap newsprint, museum caption.
3. Browse a catalog with that object in mind (Google Fonts, Pangram Pangram, Future Fonts, ABC Dinamo, Klim, Velvetyne). Reject the first thing that "looks designy" — that's the reflex.
4. Cross-check: elegant ≠ serif, technical ≠ sans, warm ≠ Fraunces. If the pick matches your reflex, go back to step 3.

### Anti-reflexes

- A technical brief does NOT need a serif "for warmth." Tech tools should look like tech tools.
- Editorial / premium does NOT require an expressive serif. Can be Swiss-modern, neo-grotesque, monospace, or a quiet humanist sans.
- Children's products do NOT need rounded display fonts. Real kids' books use real type.
- "Modern" does NOT mean geometric sans. The most modern move in 2026 is not using the font everyone else is using.

### Pairing

Often you don't need a second font. One family across weights creates cleaner hierarchy than two competing typefaces. Pair only for genuine contrast:

- Serif + Sans (structure)
- Geometric + Humanist (personality)
- Condensed display + Wide body (proportion)

Never pair two fonts that are **similar but not identical** — tension without hierarchy.

System fonts (`-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui`) are underrated for apps where performance > personality.

## Fluid vs Fixed Type

- **Fluid** (`clamp(min, preferred, max)`): headings on marketing/content pages.
- **Fixed rem**: app UIs, dashboards, data-dense interfaces. No major design system (Material, Polaris, Primer, Carbon) uses fluid type in product UI. Body text stays fixed even on marketing pages.

## Web Font Loading

Prevent FOUT/FOIT layout shift with `font-display: swap` plus a fallback matched via `size-adjust`, `ascent-override`, `descent-override`, `line-gap-override`. Tools like Fontaine compute the overrides automatically.

```css
@font-face {
  font-family: 'Brand';
  src: url('brand.woff2') format('woff2');
  font-display: swap;
}
@font-face {
  font-family: 'Brand-Fallback';
  src: local('Arial');
  size-adjust: 105%;
  ascent-override: 90%;
  descent-override: 20%;
}
```

## OpenType Features

Underused polish:

```css
.data-table { font-variant-numeric: tabular-nums; }
.recipe     { font-variant-numeric: diagonal-fractions; }
abbr        { font-variant-caps: all-small-caps; }
code        { font-variant-ligatures: none; }
body        { font-kerning: normal; }
```

Check supported features at wakamaifondue.com.

## Tokens & Accessibility

- Name tokens semantically (`--text-body`, `--text-heading`), not by value (`--font-size-16`).
- Never disable zoom. Never `px` for body text — use `rem`/`em`.
- Minimum body text 16px. Touch text needs padding/line-height for 44px targets.

## Rules Checklist

**DO**

- Use a modular type scale with clear contrast.
- Vary weights and sizes for hierarchy.
- Vary font choices across projects — if last project was serif display, try sans/mono/display next.

**DON'T**

- Use reflex fonts (see list above).
- Use monospace as lazy "technical/developer" shorthand.
- Place large rounded-corner icons above every heading.
- Run the whole page in one family.
- Set a flat scale with steps <1.25×.
- Set long body passages in uppercase. Reserve caps for short labels/headings.

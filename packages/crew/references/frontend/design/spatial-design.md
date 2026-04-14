---
title: Spatial Design
domain: frontend/design
source: adapted from impeccable (github.com/pbakaus/impeccable, Apache-2.0)
---

# Spatial Design

Rhythm, hierarchy, and composition come from *varied* spacing — not uniform padding everywhere.

## Use a 4pt Scale, Not 8pt

8pt is too coarse — you will often need 12px (between 8 and 16). Use a **4pt base**:

```
4, 8, 12, 16, 24, 32, 48, 64, 96
```

Name tokens **semantically** (`--space-sm`, `--space-md`, `--space-lg`), not by value (`--spacing-8`). Values change; relationships don't.

Use `gap` for sibling spacing, not margins. Eliminates margin-collapse and the cleanup hacks that follow.

## The Self-Adjusting Grid

The breakpoint-free responsive grid for cards:

```css
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--space-md);
}
```

Columns are at least 280px, as many as fit per row, leftovers stretch. For complex layouts, use `grid-template-areas` and redefine per breakpoint.

## Visual Hierarchy

### The Squint Test

Blur your eyes (or screenshot + blur). Can you still identify the most important element? The second? Clear groupings? If everything reads the same weight blurred, you have a hierarchy problem.

### Hierarchy Through Multiple Dimensions

Do not rely on size alone. Combine:

| Dimension | Strong | Weak |
|-----------|--------|------|
| Size | 3:1 ratio or more | <2:1 |
| Weight | Bold vs Regular | Medium vs Regular |
| Color | High contrast | Similar tones |
| Position | Top/left (primary) | Bottom/right |
| Space | Surrounded by whitespace | Crowded |

Best hierarchy uses **2–3 dimensions at once**: a heading that is larger, bolder, AND has more space above it.

## Cards Are Not Required

Cards are overused. Spacing and alignment create visual grouping naturally. Use cards only when:

- Content is truly distinct and actionable.
- Items need visual comparison in a grid.
- Content needs clear interaction boundaries.

**Never nest cards inside cards.** Use spacing, typography, and subtle dividers for hierarchy within a card.

## Container Queries Are for Components

Viewport queries are for page layouts. Container queries handle components that adapt to their container's width — a card in a sidebar stays compact, the same card in a main column expands, automatically.

```css
.card-container { container-type: inline-size; }

.card { display: grid; gap: var(--space-md); }

@container (min-width: 400px) {
  .card { grid-template-columns: 120px 1fr; }
}
```

## Optical Adjustments

Geometry and perception diverge. Real designers compensate.

- Text at `margin-left: 0` looks indented because of letterform whitespace. Apply a small negative margin (`-0.05em`) to optically align.
- Centered icons often look off-center. Play icons shift right; arrows shift toward their direction.
- Round shapes look smaller than squares at the same pixel size. Slightly upsize circles.

## Touch Targets vs Visual Size

Buttons can look small but need **44px minimum** touch targets. Expand with padding or pseudo-elements:

```css
.icon-button { width: 24px; height: 24px; position: relative; }
.icon-button::before {
  content: '';
  position: absolute;
  inset: -10px;   /* 44px tap target */
}
```

## Line Length

Cap body copy at **65–75ch**. Wider is fatiguing; the eye loses the next line.

## Depth & Elevation

Use semantic z-index scales instead of arbitrary numbers:

```
dropdown (100)
sticky (200)
modal-backdrop (300)
modal (400)
toast (500)
tooltip (600)
```

Build a shadow elevation scale (sm → md → lg → xl). **If you can clearly see a shadow, it is probably too strong.** Subtlety reads as craft.

## Rhythm, Not Uniformity

- Tight groupings between related items. Generous separations between sections.
- Fluid spacing with `clamp()` lets sections breathe on larger screens.
- Break the grid intentionally for emphasis — asymmetry and left-aligned text with asymmetric layouts feel more designed than centered-everything.

## Rules Checklist

**DO**

- Vary spacing for rhythm: tight + generous in the same layout.
- Use `gap`, not margins, between siblings.
- Use container queries for components, viewport queries for pages.
- Combine size + weight + color + position + space for hierarchy.

**DON'T**

- Invent arbitrary spacing outside the 4pt scale.
- Wrap everything in cards.
- Nest cards inside cards.
- Build endless uniform card grids (icon + heading + text, repeated).
- Use the hero-metric template (big number, small label, gradient accent, supporting stats) as default layout.
- Center everything.
- Let body text wrap past ~80 characters.

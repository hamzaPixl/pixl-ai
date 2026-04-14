---
title: Responsive Design
domain: frontend/design
source: adapted from impeccable (github.com/pbakaus/impeccable, Apache-2.0)
---

# Responsive Design

Adapt the interface for the context; do not just shrink it.

## Mobile-First

Start with base styles for mobile, layer complexity with `min-width`. Desktop-first (`max-width`) ships unneeded styles to the smallest, slowest devices first.

## Content-Driven Breakpoints

Do not chase device sizes. Start narrow, widen until the design breaks, add a breakpoint there. Three breakpoints usually suffice: **640, 768, 1024px**. For fluid values, prefer `clamp()` over a new breakpoint.

## Detect Input Method, Not Just Screen Size

Screen size does not tell you input method. A laptop has a touchscreen; a tablet has a keyboard. Use pointer and hover queries:

```css
@media (pointer: fine)    { .button { padding: 8px 16px;  } }
@media (pointer: coarse)  { .button { padding: 12px 20px; } }  /* larger tap */

@media (hover: hover)     { .card:hover { transform: translateY(-2px); } }
@media (hover: none)      { /* no hover — use :active instead */ }
```

**Critical**: never rely on hover for functionality. Touch users cannot hover.

## Safe Areas: Handle the Notch

```css
body {
  padding-top:    env(safe-area-inset-top);
  padding-bottom: env(safe-area-inset-bottom);
  padding-left:   env(safe-area-inset-left);
  padding-right:  env(safe-area-inset-right);
}

.footer {
  padding-bottom: max(1rem, env(safe-area-inset-bottom));
}
```

Enable in the meta tag:

```html
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
```

## Responsive Images

### srcset + Width Descriptors

```html
<img
  src="hero-800.jpg"
  srcset="hero-400.jpg 400w, hero-800.jpg 800w, hero-1200.jpg 1200w"
  sizes="(max-width: 768px) 100vw, 50vw"
  alt="Hero"
>
```

- `srcset`: available images with actual widths (`w` descriptors).
- `sizes`: how wide the image will display.
- Browser picks the best file by viewport width AND device pixel ratio.

### Picture for Art Direction

When you need different crops/compositions (not just resolutions):

```html
<picture>
  <source media="(min-width: 768px)" srcset="wide.jpg">
  <source media="(max-width: 767px)" srcset="tall.jpg">
  <img src="fallback.jpg" alt="...">
</picture>
```

## Layout Adaptation

- **Navigation**: three-stage — hamburger + drawer on mobile, horizontal compact on tablet, full labels on desktop.
- **Tables**: transform to cards on mobile via `display: block` + `data-label` attributes.
- **Progressive disclosure**: use `<details>` / `<summary>` for content that can collapse on mobile.
- Adapt the interface, never amputate it. Hiding critical functionality on mobile is unacceptable.

## Container Queries > Viewport Queries (for components)

A card in a sidebar should adapt to the sidebar's width, not the viewport's. See `spatial-design.md`.

## Testing: Do Not Trust DevTools Alone

Device emulation gets layout right but misses:

- Actual touch interactions.
- Real CPU / memory constraints.
- Network latency patterns.
- Font rendering differences.
- Browser chrome and on-screen keyboard appearances.

Test on at least: one real iPhone, one real Android, a tablet if relevant. **Cheap Android phones reveal performance issues simulators never show.**

## Rules Checklist

**DO**

- Write mobile-first with `min-width` queries.
- Use feature detection (`pointer`, `hover`, `prefers-*`) over device detection.
- Use `clamp()` for fluid values.
- Use `env(safe-area-inset-*)` with `viewport-fit=cover`.
- Use container queries for components.
- Test on real devices.

**DON'T**

- Write desktop-first and "fix" mobile.
- Hide critical functionality on mobile.
- Maintain separate mobile / desktop codebases.
- Ignore tablet and landscape.
- Assume all mobile devices are powerful.
- Rely on hover for any action that must work on touch.

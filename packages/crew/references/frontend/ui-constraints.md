# UI Constraints

## Stack Defaults

| Purpose | Default |
|---------|---------|
| Styling | Tailwind CSS (never inline styles unless dynamic) |
| Animation | motion/react (formerly framer-motion) |
| Animation utilities | tw-animate-css |
| Class merging | `cn()` from clsx + tailwind-merge |

## Component Primitives

Choose ONE library and never mix: Base UI, Radix UI, or React Aria.

## Interaction Patterns

- Always use `AlertDialog` (not `Dialog`) for destructive actions (delete, irreversible, data loss)
- Use `h-dvh` not `h-screen` for full viewport height
- Always account for `safe-area-inset` on mobile

## Animation Rules

### Allowed Properties
Only animate `transform` and `opacity` — these are GPU-accelerated.

### Never Animate
`width`, `height`, `margin`, `padding`, `top`/`left`/`right`/`bottom`, `border-radius`

### Duration
- Micro-interactions: 200ms max
- Page transitions: 300-500ms

### Reduced Motion
Always respect `prefers-reduced-motion`:
- Use `useReducedMotion()` hook, or
- Use `motion-safe:` Tailwind variant

## Typography

- `text-balance` for headings
- `text-pretty` for body text
- `tabular-nums` for numeric data (tables, counters, prices)
- Never customize letter-spacing

## Layout

- Fixed z-index scale: 0 / 10 / 20 / 30 / 40 / 50
- Use `size-*` instead of `w-* h-*` for squares
- Every empty state needs ONE clear action

## Performance Constraints

Never use in animations:
- `blur-*` or `backdrop-blur-*`
- `backdrop-filter`
- Large `box-shadow`

Never use `will-change` outside of active animations.

## Design Defaults

Avoid unless explicitly requested:
- Gratuitous gradients
- Glows and neon colors
- Drop shadows and text shadows
- Decorative blur effects

## Accessibility

- Semantic HTML (`<button>` not `<div onClick>`)
- `aria-label` on all icon buttons
- `focus-visible:ring-*` on all interactive elements
- Never `outline-none` without a replacement focus style
- Tab order: only `tabIndex={0}` or `tabIndex={-1}`, never positive values
- Modals trap focus and return focus on close

## Design Token System

The website builder uses a token-based design system. All visual values are resolved at generation time from an archetype and injected as CSS custom properties.

### CSS Custom Properties Available

| Property | Usage |
|----------|-------|
| `var(--radius)` | Border radius for cards, inputs, buttons |
| `var(--shadow-sm)` | Small/subtle shadow |
| `var(--shadow-md)` | Medium shadow (default card) |
| `var(--shadow-lg)` | Large shadow (hover/elevated) |
| `var(--duration-micro)` | Micro-interaction timing (hover, focus) |
| `var(--duration-page)` | Page-level transition timing |
| `var(--ease-default)` | Default easing curve |

### Forbidden Hardcoded Values

When building page sections or components in a tokenized project, **never** hardcode these values:

| Forbidden Pattern | Replacement |
|-------------------|-------------|
| `py-16`, `py-24` on sections | Use `{{SECTION_PADDING}}` or design config value |
| `max-w-7xl` on sections | Use `max-w-{{LAYOUT_MAX_WIDTH}}` or design config value |
| `rounded-xl`, `rounded-lg` on cards | Use `rounded-[var(--radius)]` |
| `shadow-sm`, `shadow-md` on cards | Use `.card-hover` class or `shadow-[var(--shadow-sm)]` |
| `duration-300`, `duration-500` | Use CSS variable `var(--duration-micro)` or `var(--duration-page)` |
| `ease-out`, `ease-in-out` | Use `var(--ease-default)` |
| `font-serif` on headings | Already set globally via CSS; don't repeat |
| `0.5s` in motion/react | Import from `lib/animations.ts` instead |
| Raw `box-shadow:` values | Use `var(--shadow-sm/md/lg)` |
| `bg-foreground text-white` on footer | Already set via `{{FOOTER_CLASSES}}` token |
| `bg-background/80 backdrop-blur` on nav | Already set via `{{NAV_CLASSES}}` token |

### Runtime Design Config

Projects using the design system export a `designConfig` object from `lib/design-config.ts`. Import it for runtime layout decisions:

```tsx
import { designConfig } from "@/lib/design-config";
// designConfig.archetype, .layout.sectionPadding, .shadows.md, etc.
```

## Quick Reference

| Item | Rule |
|------|------|
| Full height | `h-dvh` not `h-screen` |
| Squares | `size-*` not `w-* h-*` |
| Animate | `transform` + `opacity` only |
| Duration | `var(--duration-micro)` / `var(--duration-page)` |
| Blur | Never in animations |
| Numbers | `tabular-nums` |
| Headings | `text-balance` |
| Delete actions | `AlertDialog` |
| Shadows | `var(--shadow-sm/md/lg)` |
| Radius | `var(--radius)` |
| Section padding | From design config, never hardcoded |

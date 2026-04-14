---
title: Motion Design
domain: frontend/design
source: adapted from impeccable (github.com/pbakaus/impeccable, Apache-2.0)
---

# Motion Design

Focus on high-impact moments. One well-orchestrated page load with staggered reveals creates more delight than scattered micro-interactions everywhere.

## Durations: 100 / 300 / 500

Timing matters more than easing.

| Duration | Use | Examples |
|----------|-----|----------|
| 100–150ms | Instant feedback | Button press, toggle, color change |
| 200–300ms | State changes | Menu open, tooltip, hover |
| 300–500ms | Layout changes | Accordion, modal, drawer |
| 500–800ms | Entrances | Page load, hero reveal |

**Exits are faster than entrances** — use ~75% of enter duration.

## Easing: Pick the Right Curve

Do not use `ease`. It is a compromise that is rarely optimal. Use:

| Curve | For | CSS |
|-------|-----|-----|
| `ease-out` | Elements entering | `cubic-bezier(0.16, 1, 0.3, 1)` |
| `ease-in` | Elements leaving | `cubic-bezier(0.7, 0, 0.84, 0)` |
| `ease-in-out` | Toggles (there → back) | `cubic-bezier(0.65, 0, 0.35, 1)` |

For micro-interactions, prefer **exponential** curves — they mimic real friction and deceleration:

```css
--ease-out-quart: cubic-bezier(0.25, 1, 0.5, 1);   /* recommended default */
--ease-out-quint: cubic-bezier(0.22, 1, 0.36, 1);  /* slightly dramatic */
--ease-out-expo:  cubic-bezier(0.16, 1, 0.3, 1);   /* snappy, confident */
```

### Never Use Bounce or Elastic

They were trendy in 2015 and now feel tacky and amateurish. Real objects do not bounce when they stop — they decelerate smoothly. Overshoot draws attention to the animation itself, not the content.

## The Only Two Properties You Should Animate

`transform` and `opacity`. Everything else causes layout recalculation.

For height animations (accordions), use `grid-template-rows: 0fr → 1fr` instead of animating `height` directly.

```css
.accordion { display: grid; grid-template-rows: 0fr; transition: grid-template-rows 300ms var(--ease-out-quart); }
.accordion > div { overflow: hidden; }
.accordion[open] { grid-template-rows: 1fr; }
```

## Staggered Animations

Cleaner via CSS custom properties:

```css
.item { animation-delay: calc(var(--i, 0) * 50ms); }
```
```html
<li style="--i: 0">...</li>
<li style="--i: 1">...</li>
```

**Cap total stagger time.** 10 items × 50ms = 500ms. For long lists, reduce per-item delay or cap the staggered count.

## Reduced Motion Is Not Optional

Vestibular disorders affect ~35% of adults over 40.

```css
.card { animation: slide-up 500ms ease-out; }

@media (prefers-reduced-motion: reduce) {
  .card { animation: fade-in 200ms ease-out; }  /* crossfade, no motion */
}

/* Or blanket disable */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

Preserve functional motion (progress bars, spinners slowed down, focus indicators). Kill spatial/parallax/decorative motion.

## Perceived Performance

Nobody cares how fast your site is — only how fast it *feels*.

- **80ms threshold**: the brain buffers sensory input ~80ms. Under 80ms feels instantaneous. Target for micro-interactions.
- **Preemptive start**: begin transitions immediately while loading (iOS zoom, skeletons). Users perceive work happening.
- **Early completion**: show content progressively — streaming HTML, progressive images, video buffering.
- **Optimistic UI**: update immediately, sync later, roll back on failure. Use for low-stakes actions (likes, follows). Never for payments or destructive operations.
- **Easing affects perceived duration**: ease-in toward task completion compresses perceived time (peak-end effect weights final moments).
- **Caution**: too-fast responses can decrease perceived value. Users distrust instant results for complex operations (search, analysis). A brief delay can signal "real work is happening."

## Performance Details

- Do not set `will-change` preemptively. Only apply just-in-time (on `:hover`, `.animating`).
- For scroll-triggered animations, use `IntersectionObserver`; unobserve after the first firing.
- Create motion tokens: durations, easings, common transitions. One source of truth.

## Rules Checklist

**DO**

- Use motion to convey state (entrances, exits, feedback).
- Use exponential ease-out curves for natural deceleration.
- Use `grid-template-rows` for height animations.
- Provide a reduced-motion alternative.

**DON'T**

- Animate layout properties (`width`, `height`, `padding`, `margin`).
- Use bounce, elastic, or overshoot easing.
- Animate >500ms for UI feedback.
- Ignore `prefers-reduced-motion`.
- Use animation to mask slow loading.
- Animate everything — animation fatigue is real.

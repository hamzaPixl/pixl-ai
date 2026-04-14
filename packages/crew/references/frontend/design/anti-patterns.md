---
title: Anti-Patterns and the AI Slop Test
domain: frontend/design
source: adapted from impeccable (github.com/pbakaus/impeccable, Apache-2.0)
---

# Anti-Patterns

The fingerprints of AI-generated UI from 2024–2026. Match-and-refuse: if you are about to ship any of these, stop and rewrite with a different structure entirely.

The core test: **if someone saw this and said "AI made this," would they believe it immediately?** If yes, it has a problem. A distinctive interface should make people ask *"how was this made?"* — not *"which AI made this?"*

## 1. Banned Fonts (Reflex Defaults)

These are training-data defaults. Reject ALL of them, and do not simply switch to your second-favorite — that becomes the next monoculture.

| Category | Banned |
|----------|--------|
| Generic sans | Inter, Roboto, Arial, Open Sans, Lato, Montserrat, Outfit, Plus Jakarta Sans, DM Sans, Instrument Sans |
| Expressive serif | Fraunces, Playfair Display, Cormorant, Cormorant Garamond, Lora, Newsreader, Crimson, Crimson Pro, Crimson Text, Instrument Serif, DM Serif Display, DM Serif Text |
| "Technical" mono / geometric | IBM Plex Sans, IBM Plex Serif, IBM Plex Mono, Space Mono, Space Grotesk, Syne |

Also ban the *reflex patterns* those fonts represent:

- Technical brief → a serif "for warmth". No. Tech should look like tech.
- Editorial / premium → the same expressive serif everyone is using right now.
- Children's product → rounded display font. Real kids' books use real type.
- "Modern" → geometric sans. The most modern move in 2026 is not using the font everyone else is using.

See `typography.md` for the font-selection procedure that replaces the reflex.

## 2. Banned Visual Patterns

### Absolute bans

**Side-stripe borders** — `border-left:` or `border-right:` with width greater than 1px on cards, list items, callouts, or alerts.

- Includes hard-coded colors AND CSS variables (`var(--color-warning)` does not make it OK).
- Single most overused "design touch" in admin, dashboard, and medical UIs.
- Rewrite: change the element structure entirely. Do not swap to `box-shadow` inset. Reach for full borders, background tints, leading numbers/icons, or no indicator at all.

**Gradient text** — `background-clip: text` (or `-webkit-`) combined with any gradient.

- Forbidden for any `linear-gradient`, `radial-gradient`, `conic-gradient` fill on text.
- Decorative rather than meaningful; one of the top three AI design tells.
- Rewrite: single solid color for text. For emphasis, use weight or size.

### Banned patterns

- **Glassmorphism used decoratively** — blur cards, glow borders applied everywhere for "premium feel".
- **Nested cards** — cards inside cards inside cards. Flatten.
- **Generic card grids** — same-sized cards with icon + heading + text, repeated endlessly.
- **Hero-metric template** — big number, small label, gradient accent, supporting stats. The default AI dashboard layout.
- **Rounded rectangles + generic drop shadows** on everything. Safe, forgettable, interchangeable.
- **Sparklines as decoration** — tiny charts that look sophisticated but convey nothing.
- **Large rounded-corner icons above every heading.** Templated.
- **Every button primary.** Use ghost, text, and secondary buttons. Hierarchy matters.
- **Monospace as "technical shorthand"** — code fonts used for labels or body copy to signal "developer vibes."
- **Uppercase body text.** Reserve caps for short labels/headings.
- **Modals without necessity.** Most modals are lazy — prefer inline editing, drawers, or undo.
- **Hiding critical functionality on mobile.** Adapt the interface, do not amputate it.
- **Animating layout properties** (`width`, `height`, `padding`, `margin`). Use `transform` + `opacity` only.
- **Bounce or elastic easing.** Tacky and dated. Real objects decelerate smoothly.
- **Parallax and scroll-hijacking** as default marketing behavior.
- **Centering everything.** Left-aligned text with asymmetric layouts feels more designed.

## 3. Banned Color Combinations

- **Pure black (`#000`)** or **pure white (`#fff`)** for large areas. They do not exist in nature — always tint.
- **Pure gray** (`oklch(50% 0 0)`). Pure gray is dead. Add chroma 0.005–0.015 toward the brand hue.
- **Gray text on colored backgrounds.** Washed out, dead. Use a darker shade of the background color itself, or transparency.
- **Light gray text on white.** The #1 accessibility fail. Placeholder text still needs 4.5:1.
- **Red on green / green on red** — 8% of men cannot distinguish.
- **Blue on red** — vibrates visually.
- **Yellow on white** — almost always fails contrast.
- **Thin light text over images** — unpredictable contrast.

### The AI Color Palette (banned)

- Cyan-on-dark everything.
- Purple-to-blue gradients (hero sections, CTAs, backgrounds).
- Neon accents on dark backgrounds.
- Default dark mode with glowing accents. Looks "cool" without requiring real design decisions.
- Default light mode "to play it safe." The point is to choose, not retreat.
- Tinting toward warm orange by default ("friendly") or cool blue by default ("tech"). Both lazy; create their own monoculture.

## 4. The AI Slop Test (Pre-Ship Checklist)

Before declaring UI complete, run through this list. Any "yes" means iterate.

- [ ] Uses a banned font from section 1?
- [ ] Has `border-left`/`border-right` > 1px anywhere?
- [ ] Has gradient-fill text anywhere?
- [ ] Uses glassmorphism, nested cards, or generic card grids as primary layout?
- [ ] Uses the hero-metric template as the dashboard?
- [ ] Uses pure `#000`, pure `#fff`, or pure gray?
- [ ] Uses gray text on colored backgrounds?
- [ ] Uses the AI palette (cyan-on-dark, purple-to-blue gradients, neon-on-dark)?
- [ ] Defaults to dark-with-glowing-accents without theme justification from audience/context?
- [ ] Has rounded-icon-above-heading templating?
- [ ] Has every button styled as primary?
- [ ] Has monospace body text for "developer vibes"?
- [ ] Has uppercase body passages?
- [ ] Animates layout properties (`width`, `height`, `padding`, `margin`)?
- [ ] Uses bounce or elastic easing?
- [ ] Hides critical functionality on mobile?
- [ ] Uses parallax / scroll-hijack as default?
- [ ] Centers everything?
- [ ] Uses placeholder text as labels?
- [ ] Has focus rings removed without `:focus-visible` replacement?
- [ ] Uses "OK" / "Submit" / "Yes" / "No" on buttons?
- [ ] Has an empty state that just says "No items"?

If the team can answer "someone would immediately guess AI made this" — it is not done. Send it back through the iteration loop in `craft-process.md`.

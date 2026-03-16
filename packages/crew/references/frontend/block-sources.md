# Block Sources Catalog

Pre-built, installable component blocks from external registries. Prefer these over hand-rolling JSX — they ship with built-in animations, interactions, and responsive behavior.

**Selection priority:** shadcn blocks > Magic UI > Aceternity > hand-roll.

---

## Design Quality Principles

Avoid generic AI aesthetics — the "AI slop" look:

**Typography:** Never default to Inter, Roboto, Arial, or system fonts. Choose distinctive fonts:
- Code/technical: JetBrains Mono, Fira Code, Space Grotesk
- Editorial: Playfair Display, Crimson Pro, Fraunces
- Startup: Clash Display, Satoshi, Cabinet Grotesk
- Technical: IBM Plex family, Source Sans 3
- Distinctive: Bricolage Grotesque, Newsreader, Obviously

Use extreme weight contrasts (100-200 vs 800-900, not 400 vs 600). Size jumps of 3x+, not 1.5x.

**Color:** Dominant colors with sharp accents outperform timid, evenly-distributed palettes. Avoid purple gradients on white backgrounds. Use CSS variables for consistency.

**Motion:** One well-orchestrated page load with staggered reveals (animation-delay) creates more delight than scattered micro-interactions. Prioritize CSS-only for HTML; Motion library for React.

**Backgrounds:** Create atmosphere and depth. Layer CSS gradients, use geometric patterns, or add contextual effects. Never default to flat white/gray.

**Spatial Composition:** Employ unexpected layouts — asymmetry, overlap, diagonal flow. Break the centered-everything pattern.

---

## 1. shadcn/ui Blocks

**Install:** `npx shadcn@latest add <block-name> --yes`
**Discovery:** `npx shadcn@latest add --list`

| Category   | Blocks                                                        | Use For                        |
| ---------- | ------------------------------------------------------------- | ------------------------------ |
| Auth       | `login-01` through `login-05`                                 | Login/signup pages             |
| Dashboard  | `dashboard-01` through `dashboard-07`                         | Admin panels, analytics        |
| Sidebar    | `sidebar-01` through `sidebar-15`                             | App navigation, sidebar layouts|
| Charts     | `chart-area-*`, `chart-bar-*`, `chart-line-*`, `chart-pie-*`  | Data visualization             |
| Calendar   | `calendar-*`                                                  | Date pickers, scheduling       |

Blocks can be customized after installation — they're source code, not dependencies.

---

## 2. Magic UI (150+ animated components)

**Install:** `npx shadcn@latest add "https://magicui.design/r/<component>" --yes`
**Browse full catalog:** https://magicui.design/docs/components

Key categories: buttons (shimmer-button, pulsating-button), text effects (animated-gradient-text, sparkles-text, hyper-text, typing-animation, word-rotate), layout (marquee, bento-grid, animated-list), backgrounds (dot-pattern, meteors, particles, retro-grid, ripple), decorations (animated-beam, shine-border, border-beam, orbiting-circles), mockups (safari, iphone-15-pro), data (number-ticker, animated-circular-progress, globe).

---

## 3. Aceternity UI (100+ components)

**Browse:** https://ui.aceternity.com/components
**Install:** Copy-paste from website or use shadcn CLI 3.0 compatibility. Some components available via WebFetch.

Key categories: heroes (hero-parallax, lamp-effect), cards (spotlight-card, 3d-card-effect, wobble-card, infinite-moving-cards), backgrounds (background-beams, wavy-background, aurora-background, spotlight, vortex), text (text-generate-effect, encrypted-text, colourful-text), navigation (floating-navbar, floating-dock, resizable-navbar), scroll (parallax-scroll, sticky-scroll-reveal, macbook-scroll).

---

## Archetype Affinity Map

Which animated components match each archetype's personality. Use this to select the right enhancements during block discovery.

| Archetype     | Strong Matches                                                          | Subtle Matches                    |
| ------------- | ----------------------------------------------------------------------- | --------------------------------- |
| **Aurora**    | animated-beam, shine-border, meteors, particles, aurora-background, globe, orbiting-circles | blur-fade, fade-text              |
| **Glassmorphism** | animated-beam, shine-border, particles, spotlight, border-beam      | blur-fade, magic-card             |
| **Bold**      | shimmer-button, animated-gradient-text, marquee, number-ticker, pulsating-button | safari (mockups), bento-grid      |
| **Playful**   | confetti, sparkles-text, animated-list, dock, word-rotate, typing-animation | marquee, number-ticker            |
| **Cyberpunk** | dot-pattern, retro-grid, ripple, hyper-text, text-generate-effect       | tracing-beam, background-beams    |
| **Neubrutalism** | marquee, number-ticker, animated-list                                | bento-grid                        |
| **Luxury**    | blur-fade, fade-text, text-reveal, spotlight                            | tracing-beam                      |
| **Minimal**   | blur-fade, fade-text                                                    | _(minimal = minimal effects)_     |
| **Corporate** | number-ticker, animated-circular-progress                               | marquee (logo bars)               |
| **Organic**   | blur-fade, fade-text                                                    | marquee (subtle logo scroll)      |
| **Brutalist** | _(rarely uses animated components — raw static preferred)_              | hyper-text, text-generate-effect  |
| **Editorial** | blur-fade, text-reveal, fade-text                                       | tracing-beam                      |

---

## Section-to-Block Mapping Guide

When planning blocks for a website, map each section to potential block sources:

| Section Type  | shadcn Block          | Magic UI                                        | Aceternity                          |
| ------------- | --------------------- | ----------------------------------------------- | ----------------------------------- |
| Hero          | —                     | shimmer-button, animated-gradient-text, globe   | hero-parallax, lamp-effect          |
| Logo Bar      | —                     | marquee                                         | infinite-moving-cards               |
| Features      | —                     | bento-grid, magic-card, animated-list           | spotlight-card, 3d-card-effect      |
| Testimonials  | —                     | marquee, animated-list                          | infinite-moving-cards               |
| Stats/Numbers | —                     | number-ticker, animated-circular-progress       | —                                   |
| CTA           | —                     | shimmer-button, pulsating-button, shine-border  | moving-border                       |
| Backgrounds   | —                     | dot-pattern, meteors, particles, retro-grid     | background-beams, wavy-background   |
| Auth Pages    | `login-01` – `05`    | —                                               | —                                   |
| Dashboards    | `dashboard-01` – `07`| —                                               | —                                   |
| Navigation    | `sidebar-01` – `15`  | dock                                            | —                                   |
| Product Shots | —                     | safari, iphone-15-pro                           | hero-parallax                       |
| Text Effects  | —                     | animated-gradient-text, sparkles-text, hyper-text | text-generate-effect              |

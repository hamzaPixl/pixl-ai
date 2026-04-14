# Design Archetypes

Twelve design archetypes. Each defines a cohesive visual personality via resolved token values.

## Archetype Overview

| Archetype         | Personality                              | Best For                           |
| ----------------- | ---------------------------------------- | ---------------------------------- |
| **Minimal**       | Clean, restrained, content-first         | SaaS, dev tools, portfolios        |
| **Bold**          | High contrast, statement-making          | Agencies, startups, launches       |
| **Playful**       | Rounded, colorful, approachable          | EdTech, community, consumer        |
| **Corporate**     | Professional, structured, trustworthy    | B2B, consulting, finance           |
| **Luxury**        | Dark, elegant, generous whitespace       | Fashion, fine dining, architecture |
| **Organic**       | Warm, natural, handmade                  | Restaurants, wellness, local       |
| **Brutalist**     | Raw, typography-first, unconventional    | Art, indie studios, dev portfolios |
| **Editorial**     | Magazine-style, reading-focused          | Blogs, media, publications         |
| **Neubrutalism**  | Bold borders, flat fills, offset shadows | Fintech, design tools, startups    |
| **Glassmorphism** | Frosted layers, depth, dark gradients    | SaaS, AI products, dashboards      |
| **Aurora**        | Gradient-rich, luminous, atmospheric     | Creative, AI, premium SaaS         |
| **Cyberpunk**     | Neon, dark, technical, edge              | Gaming, dev tools, security        |

---

## 1. Minimal

**Personality:** Whitespace is the primary design element. Typography and layout carry all visual weight.

```yaml
BORDER_RADIUS: "6px"
SHADOW_SM: "none"
SHADOW_MD: "0 1px 2px rgba(0,0,0,0.04)"
SHADOW_LG: "0 4px 12px rgba(0,0,0,0.06)"
DURATION_MICRO: "150ms"
DURATION_PAGE: "300ms"
ANIM_EASE: "[0.25, 0.1, 0.25, 1]"
ANIM_DISTANCE: "16"
ANIM_STAGGER: "0.06"
HEADING_FONT: "sans"
NAV_CLASSES: "bg-background/80 backdrop-blur-md border-b border-border"
FOOTER_CLASSES: "bg-muted text-foreground border-t border-border"
SECTION_PADDING: "py-16 sm:py-20"
LAYOUT_MAX_WIDTH: "6xl"
```

**Character:** No decorative shadows. Borders replace shadow. One accent color. Monochromatic palette.

**Real-world references:** Apple.com, Notion, Linear, Stripe.

**Prescribed Variants:**
- Hero: centered
- Nav: bar
- Footer: 4-column
- Features: card-grid
- Testimonials: single-spotlight
- CTA: banner
- Pricing: tier-cards

---

## 2. Bold

**Personality:** Designed to grab attention. Large type, high contrast, cinematic motion.

```yaml
BORDER_RADIUS: "12px"
SHADOW_SM: "0 2px 8px rgba(0,0,0,0.08)"
SHADOW_MD: "0 8px 24px rgba(0,0,0,0.12)"
SHADOW_LG: "0 20px 40px rgba(0,0,0,0.16)"
DURATION_MICRO: "200ms"
DURATION_PAGE: "500ms"
ANIM_EASE: "[0.16, 1, 0.3, 1]"
ANIM_DISTANCE: "32"
ANIM_STAGGER: "0.1"
HEADING_FONT: "sans"
NAV_CLASSES: "bg-background/90 backdrop-blur-xl border-b border-border shadow-lg"
FOOTER_CLASSES: "bg-foreground text-background"
SECTION_PADDING: "py-20 sm:py-28"
LAYOUT_MAX_WIDTH: "7xl"
```

**Character:** Full-bleed hero. Large gradient backgrounds. Dramatic hover shadows. Vibrant saturated palette.

**Real-world references:** Vercel, Figma, Pitch, Framer.

**Prescribed Variants:**
- Hero: fullscreen or asymmetric
- Nav: transparent
- Footer: dark-inverted
- Features: stacked-full
- Testimonials: card-carousel
- CTA: split-visual
- Pricing: toggle-plans

---

## 3. Playful

**Personality:** Friendly and fun without being childish. Bouncy, colorful, inviting.

```yaml
BORDER_RADIUS: "16px"
SHADOW_SM: "0 2px 6px rgba(0,0,0,0.06)"
SHADOW_MD: "0 6px 16px rgba(0,0,0,0.08)"
SHADOW_LG: "0 12px 32px rgba(0,0,0,0.1)"
DURATION_MICRO: "200ms"
DURATION_PAGE: "400ms"
ANIM_EASE: "[0.34, 1.56, 0.64, 1]"
ANIM_DISTANCE: "24"
ANIM_STAGGER: "0.08"
HEADING_FONT: "sans"
NAV_CLASSES: "bg-white/90 backdrop-blur-xl border border-border shadow-lg rounded-full"
FOOTER_CLASSES: "bg-muted text-foreground"
SECTION_PADDING: "py-16 sm:py-24"
LAYOUT_MAX_WIDTH: "6xl"
```

**Character:** Pill nav (floating, rounded-full). Overshoot easing. Light footer. Multi-color palette.

**Real-world references:** Duolingo, Slack, Notion templates, Canva.

**Prescribed Variants:**
- Hero: asymmetric
- Nav: pill
- Footer: dark-inverted
- Features: card-grid
- Testimonials: card-carousel
- CTA: card
- Pricing: toggle-plans

---

## 4. Corporate

**Personality:** Reliable, structured, authoritative. Serif headings signal expertise.

```yaml
BORDER_RADIUS: "8px"
SHADOW_SM: "0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)"
SHADOW_MD: "0 4px 12px rgba(0,0,0,0.08)"
SHADOW_LG: "0 12px 24px rgba(0,0,0,0.1)"
DURATION_MICRO: "200ms"
DURATION_PAGE: "400ms"
ANIM_EASE: "[0.4, 0, 0.2, 1]"
ANIM_DISTANCE: "20"
ANIM_STAGGER: "0.08"
HEADING_FONT: "serif"
NAV_CLASSES: "bg-background/80 backdrop-blur-md shadow-sm"
FOOTER_CLASSES: "bg-foreground text-background"
SECTION_PADDING: "py-20 sm:py-28"
LAYOUT_MAX_WIDTH: "7xl"
```

**Character:** Split hero (text left, graphic right). Dark footer (split variant preferred over 4-column). Deep blues or navy palette. Data and statistics prominent.

**Real-world references:** Salesforce, IBM, Deloitte, McKinsey.

**Prescribed Variants:**
- Hero: centered or split
- Nav: bar
- Footer: 4-column
- Features: card-grid
- Testimonials: card-carousel
- CTA: banner
- Pricing: comparison-table

---

## 5. Luxury

**Personality:** Sophisticated, refined, generous space. Premium perception through restraint.

```yaml
BORDER_RADIUS: "2px"
SHADOW_SM: "0 1px 2px rgba(0,0,0,0.1)"
SHADOW_MD: "0 4px 16px rgba(0,0,0,0.15)"
SHADOW_LG: "0 16px 48px rgba(0,0,0,0.2)"
DURATION_MICRO: "250ms"
DURATION_PAGE: "600ms"
ANIM_EASE: "[0.16, 1, 0.3, 1]"
ANIM_DISTANCE: "40"
ANIM_STAGGER: "0.12"
HEADING_FONT: "serif"
NAV_CLASSES: "bg-transparent border-b border-white/10"
FOOTER_CLASSES: "bg-foreground text-background border-t border-white/10"
SECTION_PADDING: "py-24 sm:py-32"
LAYOUT_MAX_WIDTH: "7xl"
```

**Character:** Sharp 2px radius. Transparent nav over hero. Slow-reveal animations. Dark scheme preferred. Gold or cream accents.

**Real-world references:** Cartier, Aesop, Bang & Olufsen, Rapha.

**Prescribed Variants:**
- Hero: fullscreen
- Nav: transparent
- Footer: minimal
- Features: stacked-full
- Testimonials: single-spotlight
- CTA: banner
- Pricing: tier-cards

---

## 6. Organic

**Personality:** Warm, grounded, human. Evokes authenticity and natural materials.

```yaml
BORDER_RADIUS: "10px"
SHADOW_SM: "0 1px 4px rgba(0,0,0,0.06)"
SHADOW_MD: "0 4px 14px rgba(0,0,0,0.08)"
SHADOW_LG: "0 10px 28px rgba(0,0,0,0.1)"
DURATION_MICRO: "200ms"
DURATION_PAGE: "450ms"
ANIM_EASE: "[0.4, 0, 0.2, 1]"
ANIM_DISTANCE: "20"
ANIM_STAGGER: "0.09"
HEADING_FONT: "serif"
NAV_CLASSES: "bg-background border-b border-border"
FOOTER_CLASSES: "bg-muted text-foreground border-t border-border"
SECTION_PADDING: "py-16 sm:py-24"
LAYOUT_MAX_WIDTH: "6xl"
```

**Character:** Earthy palette (warm brown, olive, terracotta, cream). Solid grounded nav bar. Split hero with large photography.

**Real-world references:** Sweetgreen, Patagonia, Aesop, Headspace.

**Prescribed Variants:**
- Hero: split
- Nav: bar
- Footer: split
- Features: alternating-rows
- Testimonials: single-spotlight
- CTA: split-visual
- Pricing: tier-cards

---

## 7. Brutalist

**Personality:** Raw, unconventional, typography-first. Structure is exposed, not hidden.

```yaml
BORDER_RADIUS: "0px"
SHADOW_SM: "none"
SHADOW_MD: "none"
SHADOW_LG: "4px 4px 0 0 rgba(0,0,0,1)"
DURATION_MICRO: "100ms"
DURATION_PAGE: "200ms"
ANIM_EASE: "[0, 0, 1, 1]"
ANIM_DISTANCE: "0"
ANIM_STAGGER: "0.03"
HEADING_FONT: "sans"
NAV_CLASSES: "bg-background border-b-2 border-foreground"
FOOTER_CLASSES: "bg-foreground text-background border-t-2 border-foreground"
SECTION_PADDING: "py-12 sm:py-16"
LAYOUT_MAX_WIDTH: "full"
```

**Character:** Zero radius. Hard offset shadows only. Instant linear motion. Full-width layout. Thick 2px+ borders. Pure black/white with one raw accent.

**Real-world references:** Bloomberg, Balenciaga, Craigslist, Hacker News.

**Prescribed Variants:**
- Hero: statement
- Nav: split-bar
- Footer: minimal
- Features: icon-list
- Testimonials: inline-quotes
- CTA: banner
- Pricing: tier-cards

---

## 8. Editorial

**Personality:** Content-first, reading-optimized. Typography hierarchies carry the design.

```yaml
BORDER_RADIUS: "6px"
SHADOW_SM: "0 1px 2px rgba(0,0,0,0.04)"
SHADOW_MD: "0 2px 8px rgba(0,0,0,0.06)"
SHADOW_LG: "0 8px 20px rgba(0,0,0,0.08)"
DURATION_MICRO: "150ms"
DURATION_PAGE: "350ms"
ANIM_EASE: "[0.25, 0.1, 0.25, 1]"
ANIM_DISTANCE: "16"
ANIM_STAGGER: "0.06"
HEADING_FONT: "serif"
NAV_CLASSES: "bg-background border-b border-border"
FOOTER_CLASSES: "bg-muted text-foreground border-t border-border"
SECTION_PADDING: "py-12 sm:py-16"
LAYOUT_MAX_WIDTH: "5xl"
```

**Character:** Narrow max-width (5xl) for optimal reading. Dense but organized sections. Serif headings. Light, minimal footer.

**Real-world references:** Medium, The New York Times, Substack, The Verge.

**Prescribed Variants:**
- Hero: statement
- Nav: bar or sidebar
- Footer: split
- Features: alternating-rows
- Testimonials: inline-quotes
- CTA: banner
- Pricing: tier-cards

---

## 9. Neubrutalism

**Personality:** Retro-digital, bold flat fills, visible structure. Anti-polish with deliberate intent.

```yaml
BORDER_RADIUS: "0px"
SHADOW_SM: "none"
SHADOW_MD: "3px 3px 0 0 rgba(0,0,0,1)"
SHADOW_LG: "6px 6px 0 0 rgba(0,0,0,1)"
DURATION_MICRO: "120ms"
DURATION_PAGE: "250ms"
ANIM_EASE: "[0, 0, 1, 1]"
ANIM_DISTANCE: "8"
ANIM_STAGGER: "0.04"
HEADING_FONT: "sans"
NAV_CLASSES: "bg-background border-b-2 border-foreground"
FOOTER_CLASSES: "bg-foreground text-background"
SECTION_PADDING: "py-12 sm:py-20"
LAYOUT_MAX_WIDTH: "7xl"
```

**Character:** All borders 2px solid black. Flat solid fills — no gradients. Hard offset box-shadows (not diffuse). Primary palette: bold primary, black, white. Grotesque or extended sans type.

**Real-world references:** Figma 2023 marketing, Gumroad, Read.cv, Pika.

**Prescribed Variants:**
- Hero: asymmetric
- Nav: split-bar
- Footer: dark-inverted
- Features: icon-list
- Testimonials: grid-mosaic
- CTA: card
- Pricing: toggle-plans

---

## 10. Glassmorphism

**Personality:** Layered depth, frosted surfaces, premium dark ambiance.

```yaml
BORDER_RADIUS: "16px"
SHADOW_SM: "0 2px 8px rgba(0,0,0,0.2)"
SHADOW_MD: "0 8px 32px rgba(0,0,0,0.3)"
SHADOW_LG: "0 24px 64px rgba(0,0,0,0.4)"
DURATION_MICRO: "200ms"
DURATION_PAGE: "450ms"
ANIM_EASE: "[0.16, 1, 0.3, 1]"
ANIM_DISTANCE: "24"
ANIM_STAGGER: "0.1"
HEADING_FONT: "sans"
NAV_CLASSES: "bg-white/5 backdrop-blur-xl border-b border-white/10"
FOOTER_CLASSES: "bg-white/5 border-t border-white/10"
SECTION_PADDING: "py-20 sm:py-28"
LAYOUT_MAX_WIDTH: "7xl"
```

**Character:** Dark gradient base (deep purple, navy, near-black). Cards use backdrop-blur with semi-transparent white border. Geometric sans. Light text on dark. Glowing accent orbs in backgrounds.

**Real-world references:** Arc Browser, Apple WWDC pages, Vercel AI.

**Prescribed Variants:**
- Hero: bento
- Nav: transparent
- Footer: dark-inverted
- Features: bento
- Testimonials: grid-mosaic
- CTA: card
- Pricing: tier-cards

---

## 11. Aurora

**Personality:** Luminous, atmospheric, gradient-rich. Evokes Northern Lights energy.

```yaml
BORDER_RADIUS: "20px"
SHADOW_SM: "0 2px 12px rgba(0,0,0,0.15)"
SHADOW_MD: "0 8px 32px rgba(0,0,0,0.2)"
SHADOW_LG: "0 20px 60px rgba(0,0,0,0.25)"
DURATION_MICRO: "220ms"
DURATION_PAGE: "500ms"
ANIM_EASE: "[0.16, 1, 0.3, 1]"
ANIM_DISTANCE: "28"
ANIM_STAGGER: "0.1"
HEADING_FONT: "sans"
NAV_CLASSES: "bg-background/10 backdrop-blur-2xl border-b border-white/10"
FOOTER_CLASSES: "bg-background/20 border-t border-white/10"
SECTION_PADDING: "py-20 sm:py-32"
LAYOUT_MAX_WIDTH: "7xl"
```

**Character:** Multi-color gradient backgrounds (teal → purple → pink). Glowing orbs as background elements. Large rounded cards. Semi-bold display type. Dark mode base. Smooth color transitions.

**Real-world references:** Luma, Framer landing pages, some Anthropic pages.

**Prescribed Variants:**
- Hero: bento
- Nav: pill
- Footer: dark-inverted
- Features: bento
- Testimonials: grid-mosaic
- CTA: card
- Pricing: toggle-plans

---

## 12. Cyberpunk

**Personality:** Dark, technical, neon-accented. High-density, code-adjacent aesthetic.

```yaml
BORDER_RADIUS: "4px"
SHADOW_SM: "0 0 8px rgba(0,255,255,0.15)"
SHADOW_MD: "0 0 20px rgba(0,255,255,0.2)"
SHADOW_LG: "0 0 48px rgba(0,255,255,0.25)"
DURATION_MICRO: "100ms"
DURATION_PAGE: "250ms"
ANIM_EASE: "[0, 0, 0.58, 1]"
ANIM_DISTANCE: "12"
ANIM_STAGGER: "0.04"
HEADING_FONT: "sans"
NAV_CLASSES: "bg-background border-b border-primary/30"
FOOTER_CLASSES: "bg-background border-t border-primary/30"
SECTION_PADDING: "py-16 sm:py-20"
LAYOUT_MAX_WIDTH: "7xl"
```

**Character:** Near-black base (#0a0a0f). Neon accent (electric blue or hot magenta). Monospace or techno fonts. Glowing border effects via box-shadow. Grid/scanline texture overlays. Dense layout.

**Real-world references:** Vercel (dark theme), Raycast, Linear dark mode.

**Prescribed Variants:**
- Hero: statement
- Nav: split-bar
- Footer: dark-inverted
- Features: icon-list
- Testimonials: inline-quotes
- CTA: banner
- Pricing: toggle-plans

---

## Mixing Archetypes

Pick one as **primary** (60%) and one as **modifier** (40%). Use primary's structural tokens (nav, footer, layout, radius) and modifier's personality tokens (animation, shadow, color approach).

| Blend                  | Result                      |
| ---------------------- | --------------------------- |
| Minimal + Corporate    | Clean professional SaaS     |
| Bold + Playful         | Energetic consumer app      |
| Luxury + Editorial     | Premium magazine            |
| Organic + Editorial    | Warm storytelling brand     |
| Brutalist + Minimal    | Technical raw documentation |
| Glassmorphism + Aurora | Premium AI product          |
| Neubrutalism + Bold    | High-energy design tool     |
| Cyberpunk + Minimal    | Technical dark SaaS         |

---

# Extended Archetypes (Taste Pack)

The following archetypes extend the core 12 with deeper personality packs imported from the taste-skill reference library. They are richer on motion, anti-patterns, and typographic intent — use them when the default 12 archetypes feel too generic for the brief.

> Note: `Brutalist` (core #7) is a minimal "raw, typography-first" variant. The `Industrial Brutalist` below is a heavier, more opinionated pack that adds terminal/telemetry modes. Treat them as distinct variants — pick one per project.

---

## 13. Industrial Brutalist (Telemetry / Swiss-Print)

**Personality:** Raw mechanical interfaces fusing Swiss typographic print with military terminal aesthetics. Rigid grids, extreme type scale contrast, utilitarian color, analog degradation effects.

```yaml
BORDER_RADIUS: "0px"
SHADOW_SM: "none"
SHADOW_MD: "none"
SHADOW_LG: "none"
DURATION_MICRO: "80ms"
DURATION_PAGE: "180ms"
ANIM_EASE: "[0, 0, 1, 1]"
ANIM_DISTANCE: "0"
ANIM_STAGGER: "0.02"
HEADING_FONT: "sans"
NAV_CLASSES: "bg-background border-b border-foreground"
FOOTER_CLASSES: "bg-foreground text-background"
SECTION_PADDING: "py-10 sm:py-14"
LAYOUT_MAX_WIDTH: "full"
```

**Color palette:**
- Light (Swiss-Print): newsprint/off-white `#F5F2EA`, ink `#0A0A0A`, hazard red accent `#E61919`.
- Dark (Tactical Telemetry): deactivated CRT `#0A0A0A` / `#121212`, white phosphor foreground `#EAEAEA`, aviation red `#E61919`, optional terminal green `#4AF626` (single-purpose only).
- Never pure `#000000` or `#FFFFFF`. Commit to ONE mode per project — do not mix Swiss-Print and Telemetry.

**Typography:**
- Macro headings: Neue Haas Grotesk Black, Archivo Black, Monument Extended, Inter Black — `clamp(4rem, 10vw, 15rem)`.
- Monospace for metadata, tables, labels: IBM Plex Mono, JetBrains Mono, Berkeley Mono.
- Extreme scale contrast (huge / tiny), ALL-CAPS labels with wide tracking, no mid-range sizes.

**Radius / Shadow / Spacing:**
- Radius: absolute zero (`border-radius: 0`). 90-degree corners are mandatory.
- Shadows: none — use visible borders (`1px`/`2px solid`) to delineate zones instead.
- Spacing: bimodal — tight data clusters adjacent to vast negative space around macro numerals.

**Motion personality:** Instant, linear, mechanical. No easing curves, no entry fades. State changes are snaps, not transitions.

**Signature devices:** ASCII framing brackets `[ REV 2.6 ]`, crosshairs at grid intersections, registration marks as structural elements, CRT scanline overlays, halftone/1-bit dithering on imagery, horizontal warning stripes.

**When to use:** Data dashboards, editorial/news, security/infosec landing pages, developer portfolios, declassified-blueprint aesthetics.

**Anti-patterns:** Rounded corners. Diffuse shadows. Easing curves on transitions. Mixing Swiss-Print + Telemetry modes. Pure black `#000000`. Mid-range type sizes.

**Real-world references:** Bloomberg Terminal, Palantir marketing, Arc Raiders site, Teenage Engineering, Craigslist.

---

## 14. Minimalist (Editorial Utility)

**Personality:** Clean editorial-style interfaces. Warm monochrome palette, typographic contrast, flat bento grids, muted pastels. Document-like, gallery-airy, Notion-tier refinement.

```yaml
BORDER_RADIUS: "4px"
SHADOW_SM: "0 1px 2px rgba(0,0,0,0.02)"
SHADOW_MD: "0 2px 8px rgba(0,0,0,0.04)"
SHADOW_LG: "0 4px 16px rgba(0,0,0,0.05)"
DURATION_MICRO: "200ms"
DURATION_PAGE: "600ms"
ANIM_EASE: "[0.16, 1, 0.3, 1]"
ANIM_DISTANCE: "12"
ANIM_STAGGER: "0.08"
HEADING_FONT: "serif"
NAV_CLASSES: "bg-background/80 backdrop-blur-md border-b border-border"
FOOTER_CLASSES: "bg-background border-t border-border"
SECTION_PADDING: "py-24 sm:py-32"
LAYOUT_MAX_WIDTH: "5xl"
```

**Color palette:**
- Warm monochrome base: cream `#F7F6F3`, off-white surface `#FFFFFF`, charcoal text `#111111` (never `#000`), muted secondary `#787774`, hairline border `#EAEAEA`.
- Accents: muted pastels only (dusty rose, sage, butter, sky) — applied sparingly as badge fills or illustration accents. Never large colored sections.

**Typography:**
- UI sans: SF Pro Display, Geist Sans, Switzer, Helvetica Neue. Never Inter / Roboto / Open Sans.
- Editorial serif for headings & pull-quotes: Lyon Text, Newsreader, Instrument Serif, Playfair Display. Tight tracking (`-0.02em` to `-0.04em`), `line-height: 1.1`.
- Mono for meta/keystrokes: Geist Mono, SF Mono, JetBrains Mono.

**Radius / Shadow / Spacing:**
- Radius: small (4-6px). No `rounded-full` on large containers.
- Shadow: ultra-diffuse, opacity < 0.05. Effectively invisible but present for micro-elevation.
- Spacing: macro-whitespace. Section padding `py-24`/`py-32`. Content constrained to `max-w-4xl` or `max-w-5xl`.

**Motion personality:** Invisible sophistication. 600ms fades with `cubic-bezier(0.16, 1, 0.3, 1)`. 12px translateY on entry. Staggered cascades at `80ms` per index. No spectacle.

**Signature devices:** Pill-shaped badges with ALL-CAPS tracked text. `<kbd>` keystroke chips. Faux-OS window chrome for app mocks. Monochromatic line illustrations with one pastel shape offset. Ambient drifting radial gradient at `opacity: 0.02-0.04`.

**When to use:** SaaS dashboards, productivity tools, editorial blogs, consulting/advisory sites, documentation sites, portfolios that prioritize content.

**Anti-patterns:** Inter / Roboto / Open Sans. Heavy shadows (`shadow-md`+). Primary-colored hero sections. Gradients. Neon. 3D glassmorphism (except subtle nav blur). `rounded-full` on large cards/buttons. Emojis. "Lorem ipsum" / "John Doe" / "Acme Corp". AI cliches ("Elevate", "Seamless", "Unleash").

**Real-world references:** Notion, Linear docs, Vercel blog, Stripe marketing pages, Read.cv.

---

## 15. Soft (High-End Visual / Awwwards-Tier)

**Personality:** $150k+ agency-level experiences. Haptic depth, cinematic spatial rhythm, obsessive micro-interactions, fluid spring motion. Soft structuralism with exaggerated squircles and double-bezel layering.

```yaml
BORDER_RADIUS: "32px"
SHADOW_SM: "0 4px 12px rgba(0,0,0,0.04)"
SHADOW_MD: "0 20px 40px -15px rgba(0,0,0,0.08)"
SHADOW_LG: "0 40px 80px -20px rgba(0,0,0,0.12)"
DURATION_MICRO: "400ms"
DURATION_PAGE: "800ms"
ANIM_EASE: "[0.32, 0.72, 0, 1]"
ANIM_DISTANCE: "64"
ANIM_STAGGER: "0.12"
HEADING_FONT: "sans"
NAV_CLASSES: "bg-background/70 backdrop-blur-2xl border border-white/10 rounded-full mx-auto mt-6 w-max"
FOOTER_CLASSES: "bg-foreground text-background rounded-t-[32px]"
SECTION_PADDING: "py-32 sm:py-40"
LAYOUT_MAX_WIDTH: "7xl"
```

**Color palette (pick ONE vibe per project):**
- Ethereal Glass: OLED black `#050505`, radial purple/emerald orb glows, vantablack cards with `backdrop-blur-2xl`, white/10 hairlines.
- Editorial Luxury: warm cream `#FDFBF7`, muted sage, deep espresso, film-grain noise overlay at `opacity-[0.03]`.
- Soft Structuralism: silver-grey or pure white, bold Grotesk headings, diffused ambient shadows, floating components.

**Typography:**
- Display: Geist, Clash Display, PP Editorial New, Plus Jakarta Sans. Banned: Inter, Roboto, Arial, Helvetica, Open Sans.
- Icons: ultra-light stroke only (Phosphor Light, Remix Line). No Lucide / FontAwesome defaults.

**Radius / Shadow / Spacing:**
- Radius: exaggerated squircle (`rounded-[2rem]` / 32px). Pills on floating nav.
- Shadow: diffused, low-opacity ambient (`0 20px 40px -15px rgba(0,0,0,0.05)`). Never harsh drops.
- Spacing: `py-24` minimum, often `py-40`. Heavy breathing room. Double-bezel nesting (outer shell + inner core) on all major cards.

**Motion personality:** Spring physics (`stiffness: 100, damping: 20`). Custom cubic-bezier `[0.32, 0.72, 0, 1]` — never linear or ease-in-out. Fluid Island nav. Magnetic button hover (scale 0.98 on press, inner icon translates diagonally). 800ms+ entry fades with blur-md → blur-0. Staggered mask reveals.

**Signature devices:** Floating pill nav detached from top. Hamburger → X morph. Button-in-button trailing icon. Perpetual micro-loops (pulse, float, shimmer). Asymmetric bento grids. Eyebrow tags (`text-[10px] uppercase tracking-[0.2em]`).

**When to use:** Premium SaaS launches, AI product marketing, agency portfolios, luxury consumer apps, any brief where "Awwwards SOTD" is the bar.

**Anti-patterns:** Inter / Roboto. Harsh dark shadows. Edge-to-edge sticky navbars glued to top. Symmetric 3-column Bootstrap grids. Linear / ease-in-out transitions. Instant state changes. Animating `top`/`left`/`width`/`height` (only `transform` + `opacity`). Arbitrary `z-[9999]`. `h-screen` (use `min-h-[100dvh]`).

**Real-world references:** Arc Browser, Rauno Freiberg sites, Family agency, recent Linear/Anthropic landing work, Mercury.com.

---

## 16. Stitch (Taste Standard)

**Personality:** Restrained, gallery-airy interface with confident asymmetric layouts and fluid spring-physics motion. Clinical yet warm — a well-lit architecture studio where every element earns its place through function. Tuned via four dials: Creativity, Density, Variance, Motion Intent.

```yaml
BORDER_RADIUS: "40px"
SHADOW_SM: "0 2px 6px rgba(0,0,0,0.03)"
SHADOW_MD: "0 20px 40px -15px rgba(0,0,0,0.05)"
SHADOW_LG: "0 40px 80px -20px rgba(0,0,0,0.08)"
DURATION_MICRO: "300ms"
DURATION_PAGE: "700ms"
ANIM_EASE: "spring(100, 20)"
ANIM_DISTANCE: "48"
ANIM_STAGGER: "0.10"
HEADING_FONT: "sans"
NAV_CLASSES: "bg-background/80 backdrop-blur-xl border-b border-[rgba(226,232,240,0.5)]"
FOOTER_CLASSES: "bg-background border-t border-[rgba(226,232,240,0.5)]"
SECTION_PADDING: "py-24 sm:py-32"
LAYOUT_MAX_WIDTH: "[1400px]"
```

**Color palette:**
- Canvas White `#F9FAFB` (warm-neutral, never clinical blue-white).
- Pure Surface `#FFFFFF` with whisper border `rgba(226,232,240,0.5)`.
- Charcoal Ink `#18181B` (zinc-950, never pure black).
- Steel Secondary `#71717A`, Muted Slate `#94A3B8`.
- Diffused shadow: `rgba(0,0,0,0.05)` at 40px blur, -15px offset.

**Typography:**
- Display: Geist, Satoshi, Cabinet Grotesk, Outfit. Tracking `-0.025em`, weight 700-900, leading `1.1`. Inter is BANNED.
- Body: same family at 400, leading `1.65`, max 65ch, Steel Secondary color.
- Mono: Geist Mono, JetBrains Mono for metadata/timestamps. At Density ≥7, all numbers switch to mono.
- Scale: display `clamp(2.25rem, 5vw, 3.75rem)`, body `1rem/1.125rem`.

**Radius / Shadow / Spacing:**
- Radius: generously rounded (`2.5rem` / 40px) on cards. Never `rounded-full` on large containers.
- Shadow: diffused whisper (`0 20px 40px -15px rgba(0,0,0,0.05)`). Internal card padding `2rem-2.5rem`.
- Spacing: max-width `1400px` centered. Horizontal padding `1rem` mobile / `2rem` tablet / `4rem` desktop. Section gaps `clamp(3rem, 8vw, 6rem)`.

**Motion personality:** Spring-based exclusively (`stiffness: 100, damping: 20`). No linear easing anywhere. Perpetual micro-loops on active components: pulse dots, typewriter search, float icons, shimmer loaders. Staggered orchestration at `100ms * index`. Hardware-accelerated `transform`/`opacity` only.

**Signature devices:** Inline image typography (small photos between words in headlines). No overlapping elements — every element has its own spatial zone. Bento architecture (Row 1: 3 cols / Row 2: 2 cols 70/30 split). Skeletal shimmer loaders (never circular spinners). Composed illustrations for empty states.

**Dial configuration:** Creativity `1-10`, Density `1-10`, Variance `1-10`, Motion Intent `1-10`. Defaults: `8/4/8/6` (expressive, balanced-density, high-variance, moderate-motion). Adjust per-project brief.

**When to use:** Products generated through Google Stitch (or Stitch-adjacent tooling). AI-first companies that want anti-generic output by default. Projects that need a tunable taste baseline rather than a single fixed archetype.

**Anti-patterns:** Emojis anywhere. Inter font. Generic serifs (Times/Georgia/Garamond). Pure `#000000`. Neon outer glows. Oversaturated accents (>80% sat). Gradient text on large headers. Overlapping text and images. 3-column equal feature cards. Centered heroes at high Variance. Filler UI ("Scroll to explore", bouncing chevrons). Generic names ("John Doe", "Acme", "Nexus"). Round numbers (`99.99%`, `50%`). AI cliches. `h-screen` (use `min-h-[100dvh]`). Circular spinners.

**Real-world references:** Linear, Vercel Ship pages, Mercury, Arc Browser, Raycast marketing, Family.co work.

---

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

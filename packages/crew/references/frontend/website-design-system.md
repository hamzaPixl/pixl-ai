# Website Design System Procedure

> Full design system procedure extracted from the `/website` skill (Step 2).
> Reusable by `/website` and `/website-theme`.

## Required References

Before starting, read these files to inform your decisions:

- `references/frontend/design-archetypes.md` — 12 archetypes with complete token sets (Minimal, Bold, Playful, Corporate, Luxury, Organic, Brutalist, Editorial, Neubrutalism, Glassmorphism, Aurora, Cyberpunk)
- `references/frontend/sector-design-intelligence.md` — sector mappings, color psychology, layout patterns
- `references/frontend/design-resources.md` — color formulas, typography scales, font catalog

## Sub-steps

### 2.1 Determine Archetype

- Identify the project's sector from discovery output (e.g., SaaS, restaurant, agency)
- Look up the sector-to-archetype mapping in `sector-design-intelligence.md`
- Select the primary archetype (and optional modifier archetype for blends)
- Apply any user overrides from discovery (e.g., "I want a dark, minimal look" -> Luxury or Minimal)
- Copy the archetype's full resolved token set as the starting point

### 2.2 Build Color Palette

- Start with user-provided brand colors OR generate from sector color psychology
- Choose a harmony type (analogous, complementary, split-complementary, triadic, monochromatic)
- Compute the full palette using formulas from `design-resources.md`:
  - `PRIMARY_COLOR_HSL` — primary brand color
  - `SECONDARY_COLOR_HSL` — harmony-derived secondary
  - `ACCENT_COLOR_HSL` — tinted accent variant
  - `SURFACE_COLOR_HSL` — primary-tinted neutral (e.g., `H 10% 97%`)
- Validate WCAG contrast ratios (primary on white >= 4.5:1, foreground on background >= 7:1)

### 2.3 Select Typography

- Pick a font pair from the recommendations in `sector-design-intelligence.md`
- Or choose fonts from the catalog in `design-resources.md` based on archetype personality
- Set tokens:
  - `FONT_SANS_IMPORT` — exact `next/font/google` import name
  - `FONT_SERIF_IMPORT` — exact `next/font/google` import name
  - `FONT_SERIF_WEIGHT` — weight config string (e.g., `"400;700"`)
  - `HEADING_FONT` — `"sans"` or `"serif"` for heading font family

### 2.4 Define Spacing & Shape

- From the archetype, set:
  - `SECTION_PADDING` — Tailwind padding classes (e.g., `py-16 sm:py-24`)
  - `LAYOUT_MAX_WIDTH` — Tailwind max-width suffix (e.g., `6xl`, `7xl`, `full`)
  - `BORDER_RADIUS` — CSS value (e.g., `8px`, `16px`, `0px`)

### 2.5 Define Motion

- From the archetype, set:
  - `DURATION_MICRO` — micro-interaction timing (e.g., `200ms`)
  - `DURATION_PAGE` — page-level transition timing (e.g., `400ms`)
  - `ANIM_EASE` — cubic bezier array (e.g., `[0.4, 0, 0.2, 1]`)
  - `ANIM_DISTANCE` — pixel distance for fade-in animations (e.g., `24`)
  - `ANIM_STAGGER` — stagger delay in seconds (e.g., `0.08`)

### 2.6 Define Shadows

- From the archetype, set resolved CSS values:
  - `SHADOW_SM` — small shadow (or `none`)
  - `SHADOW_MD` — medium shadow
  - `SHADOW_LG` — large shadow (hover/elevated state)

### 2.7 Define Layout Variants

- From the archetype, set CSS class strings:
  - `NAV_CLASSES` — nav bar variant classes (e.g., pill, bar, transparent)
  - `FOOTER_CLASSES` — footer variant classes (e.g., dark, light, muted)
- Set `DESIGN_ARCHETYPE` — archetype name for runtime config

### 2.8 Select Component Variants (REQUIRED)

**Read `references/frontend/component-variants.md`** and select a named variant for each component category based on the archetype. This is what makes each website structurally unique — tokens alone only change colors, not layout.

Select and record:

- **Hero variant** — e.g., `split`, `fullscreen`, `bento`, `statement` (NOT always `centered`)
- **Nav variant** — e.g., `transparent`, `pill`, `split-bar` (NOT always `bar`)
- **Footer variant** — e.g., `minimal`, `dark-inverted`, `split` (NOT always `4-column`)
- **Features variant** — e.g., `bento`, `alternating-rows`, `icon-list` (NOT always `card-grid`)
- **Testimonials variant** — e.g., `single-spotlight`, `grid-mosaic`, `inline-quotes`
- **CTA variant** — e.g., `card`, `split-visual`
- **Pricing variant** (if applicable) — e.g., `comparison-table`, `toggle-plans`

**Anti-sameness rule:** If the archetype maps to `centered` hero + `bar` nav + `4-column` footer + `card-grid` features, that combination is ONLY valid for Minimal/Corporate archetypes. All other archetypes MUST use different structural variants.

### 2.9 Compile Design Brief

Output a structured `design.output` object with ALL token values:

```yaml
# Schema: references/orchestration/context-packet.md (type: design)
design.output:
  archetype: "minimal"
  colors:
    primary_hsl: "217 91% 60%"
    secondary_hsl: "187 70% 50%"
    accent_hsl: "217 40% 96%"
    surface_hsl: "217 10% 97%"
  typography:
    font_sans: "Inter"
    font_serif: "Playfair_Display"
    font_sans_import: "Inter"
    font_serif_import: "Playfair_Display"
    font_serif_weight: '"400;700"'
    heading_font: "serif"
  shape:
    border_radius: "6px"
  shadows:
    sm: "none"
    md: "0 1px 2px rgba(0, 0, 0, 0.04)"
    lg: "0 4px 12px rgba(0, 0, 0, 0.06)"
  motion:
    duration_micro: "150ms"
    duration_page: "300ms"
    ease: "[0.25, 0.1, 0.25, 1]"
    distance: "16"
    stagger: "0.06"
  layout:
    nav_classes: "bg-background/80 backdrop-blur-md border-b border-border"
    footer_classes: "bg-muted text-foreground border-t border-border"
    section_padding: "py-16 sm:py-20"
    max_width: "6xl"
  variants: # from references/frontend/component-variants.md
    hero: "fullscreen" # NOT always "centered" or "split"
    nav: "transparent"
    footer: "minimal" # NOT always "4-column"
    features: "alternating-rows" # NOT always "card-grid"
    testimonials: "single-spotlight"
    cta: "banner"
    pricing: "tier-cards"
```

**Every token must have a value. Every variant must be explicitly selected.** Do not leave any token empty or undefined. Do not default every project to the same variant combination.

### 2.10 Browse ui-layouts for Component Inspiration

After selecting archetype and variants, search the `ui-layouts` registry for animated/interactive component blocks that match the selected variants:

1. Use `search_components` to find components matching each variant (e.g., search "hero split", "pricing cards", "testimonial carousel")
2. Use `get_component_meta` to evaluate fit — check if the component's style matches the archetype personality
3. Use `get_source_code` to retrieve implementation code for any components you plan to use
4. **Prefer ui-layouts implementations** over plain static JSX when a matching component exists — they come with built-in animations and interactions
5. Record which ui-layouts components will be used in the design brief so section-building agents know to integrate them

This step is optional but strongly recommended — it produces more polished, interactive results than hand-rolling every component.

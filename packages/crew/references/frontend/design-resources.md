# Design Resources

Color formulas, typography systems, spacing scales, font catalog, online references, and the parametric variation axes that guarantee unique output per generation.

---

## What Composes a Good Website Theme

A theme is four layers working together:

| Layer | What It Is | Tokens |
|-------|-----------|--------|
| **Scheme** | Color relationships — primary, secondary, accent, surface, background, foreground, muted, border | `primary_hsl`, `secondary_hsl`, `accent_hsl`, `surface_hsl` |
| **Typography** | Font pair + size scale + weight hierarchy | `font_sans`, `font_serif`, `heading_font`, `font_serif_weight` |
| **Shape & Depth** | Border radius, shadow set (sm / md / lg) | `border_radius`, `shadow_sm`, `shadow_md`, `shadow_lg` |
| **Motion** | Timing, easing, stagger, travel distance | `duration_micro`, `duration_page`, `ease`, `distance`, `stagger` |
| **Layout** | Max-width, section padding, nav and footer variant | `max_width`, `section_padding`, `nav_classes`, `footer_classes` |

A component inherits all five layers through CSS custom properties. Any component written to the design system will look correct without per-component style decisions.

---

## Parametric Variation Axes

Run one value from each axis per generation. Combining axes produces thousands of guaranteed-unique designs.

| Axis | Options |
|------|---------|
| **Archetype** | minimal · bold · playful · corporate · luxury · organic · brutalist · editorial · neubrutalism · glassmorphism · aurora · cyberpunk |
| **Palette harmony** | analogous · complementary · split-complementary · triadic · monochromatic |
| **Type category** | geometric-sans · humanist-sans · grotesque · monospace · transitional-serif · display-serif |
| **Layout grid** | centered · split-screen · asymmetric · bento · full-bleed · broken-grid |
| **Motion level** | none · subtle · moderate · kinetic · scroll-driven |
| **Density** | airy · balanced · dense |

**Rule:** Never produce the same archetype + palette harmony + type category combination twice in a row without a user request.

---

## Color Palette Formulas

Given a primary color `P = H S% L%` in HSL space:

| Role | Formula |
|------|---------|
| Primary | `H S% L%` |
| Secondary | varies by harmony (see below) |
| Accent | `H (S−15)% (L+10)%` |
| Surface (light) | `H 10% 97%` |
| Surface (dark) | `H 10% 12%` |
| Muted (light) | `H 8% 96%` |
| Muted (dark) | `H 8% 15%` |
| Border (light) | `H 12% 90%` |
| Border (dark) | `H 12% 18%` |

### Harmony Formulas

| Harmony | Secondary | Accent | Feel |
|---------|-----------|--------|------|
| Analogous | `(H+30) (S−10)% (L+5)%` | `(H−20) (S−15)% (L+10)%` | Calm, unified |
| Complementary | `(H+180) S% L%` | `(H+180) (S−20)% (L+15)%` | Vibrant tension |
| Split-complementary | `(H+150) (S−5)% (L+5)%` | `(H+210) (S−5)% (L+5)%` | Balanced contrast |
| Triadic | `(H+120) (S−10)% L%` | `(H+240) (S−10)% L%` | Colorful, balanced |
| Monochromatic | `H (S−30)% (L+20)%` | `H (S−20)% (L−10)%` | Refined, cohesive |

### WCAG Contrast Validation

| Pair | Min Ratio |
|------|-----------|
| Primary on Background | 4.5:1 |
| Foreground on Background | 7:1 (target AAA) |
| Muted-foreground on Background | 4.5:1 |
| Primary-foreground on Primary | 4.5:1 |

Quick rule: For light themes, primary lightness < 45%. For dark themes, primary lightness > 55%.

---

## Typography Scale Systems

### Scale Ratios

| Scale | Ratio | Feel | Best For |
|-------|-------|------|----------|
| Minor Third | 1.200 | Compact | Dashboards, data-heavy UI |
| Major Third | 1.250 | Balanced | General websites (default) |
| Perfect Fourth | 1.333 | Dramatic | Marketing, landing pages |
| Golden Ratio | 1.618 | Grand | Luxury, editorial, display |

### Heading Size Mapping

| Element | Tailwind Classes | Use |
|---------|-----------------|-----|
| Display | `text-5xl sm:text-6xl lg:text-7xl` | Hero headline only |
| H1 | `text-3xl sm:text-4xl lg:text-5xl` | Page titles |
| H2 | `text-2xl sm:text-3xl` | Section headings |
| H3 | `text-xl sm:text-2xl` | Sub-section headings |
| H4 | `text-lg` | Card titles |
| Body | `text-base` | Paragraphs |
| Small | `text-sm` | Captions, metadata |
| Tiny | `text-xs` | Labels, badges |

---

## Spacing Scale Systems

| System | Section Padding | Tailwind Classes | Best For |
|--------|----------------|-----------------|----------|
| Compact | 48–64px | `py-12 sm:py-16` | Editorial, Brutalist, dense |
| Default | 64–96px | `py-16 sm:py-24` | Most archetypes |
| Generous | 80–112px | `py-20 sm:py-28` | Bold, Playful |
| Spacious | 96–128px | `py-24 sm:py-32` | Luxury, Aurora |

### Max Width by Archetype

| Tailwind | Width | Best For |
|----------|-------|----------|
| `max-w-5xl` | 1024px | Editorial, content-focused |
| `max-w-6xl` | 1152px | Minimal, Playful, Organic |
| `max-w-7xl` | 1280px | Corporate, Bold, Luxury, Cyberpunk |
| `max-w-full` | 100% | Brutalist |

---

## Google Fonts Catalog

### Geometric Sans-Serif
| Font | Import Name | Character |
|------|-------------|-----------|
| Inter | `Inter` | Neutral workhorse |
| Outfit | `Outfit` | Rounded geometric |
| Sora | `Sora` | Soft geometric |
| Space Grotesk | `Space_Grotesk` | Technical, spacious |
| Geist | `Geist` | Vercel's system font |

### Humanist Sans-Serif
| Font | Import Name | Character |
|------|-------------|-----------|
| Plus Jakarta Sans | `Plus_Jakarta_Sans` | Friendly professional |
| Nunito | `Nunito` | Rounded, approachable |
| DM Sans | `DM_Sans` | Clean, proportional |
| Work Sans | `Work_Sans` | Screen-optimized |
| Rubik | `Rubik` | Slightly rounded |

### Grotesque Sans-Serif
| Font | Import Name | Character |
|------|-------------|-----------|
| Manrope | `Manrope` | Modern grotesque |
| Albert Sans | `Albert_Sans` | Contemporary, clear |

### Monospace
| Font | Import Name | Character |
|------|-------------|-----------|
| JetBrains Mono | `JetBrains_Mono` | Developer favorite |
| Fira Code | `Fira_Code` | Ligature support |
| IBM Plex Mono | `IBM_Plex_Mono` | Corporate tech |
| Source Code Pro | `Source_Code_Pro` | Adobe's mono |

### Transitional Serif
| Font | Import Name | Character |
|------|-------------|-----------|
| Lora | `Lora` | Elegant, readable |
| Merriweather | `Merriweather` | Screen-optimized |
| Source Serif 4 | `Source_Serif_4` | Adobe's text serif |
| Crimson Pro | `Crimson_Pro` | Warm, humanist |
| Libre Baskerville | `Libre_Baskerville` | Classic book face |

### Display Serif
| Font | Import Name | Character |
|------|-------------|-----------|
| Playfair Display | `Playfair_Display` | High contrast, editorial |
| DM Serif Display | `DM_Serif_Display` | Single weight, elegant |
| Fraunces | `Fraunces` | Variable, quirky |

### Elegant Serif
| Font | Import Name | Character |
|------|-------------|-----------|
| Cormorant Garamond | `Cormorant_Garamond` | Delicate, refined |
| EB Garamond | `EB_Garamond` | Classic Garamond revival |

---

## Online Design References

### Inspiration Galleries

| Gallery | URL | Best For |
|---------|-----|----------|
| Awwwards | awwwards.com/websites/ui-design | Award-winning production sites |
| Godly | godly.website | Highest aesthetic bar, hand-curated |
| Lapa Ninja | lapa.ninja | 7,000+ landing pages by industry |
| Mobbin | mobbin.com/explore/web | 400k+ real-world app screenshots |
| Landbook | land-book.com | SaaS and startup landing pages |
| Framer Gallery | framer.com/gallery | Live interactive sites, motion design |
| Httpster | httpster.net | Experimental, off-grid designs |

### Real-World Design System References

| Product | Design DNA | Key Patterns |
|---------|-----------|--------------|
| **Vercel** | Minimal, monochrome | Dot grid backgrounds, glass nav, gradient text |
| **Linear** | Dark, tight spacing | Keyboard-first, spotlight nav, status badges |
| **Stripe** | Clean, gradient accents | Animated mesh gradients, documentation polish |
| **Apple** | Generous space, bento | Full-viewport sections, scroll-linked animation |
| **Arc Browser** | Playful, gradient-heavy | Glassmorphism, animated backgrounds |
| **Raycast** | Dark, keyboard-centric | Command palette, monospace accents |
| **Loom** | Warm, approachable | Video-first, pastel gradients, soft shadows |
| **Figma** | Bold, colorful | Gradient patterns, community-driven, neubrutalism era |
| **Notion** | Minimal, playful details | Toggle patterns, clean typography |
| **Airbnb** | Warm, accessible, rounded | Category pills, photo-driven |

### Archetype-Specific References

| Archetype | Reference Sites |
|-----------|----------------|
| Neubrutalism | Gumroad, Read.cv, Pika.art, Figma (2022-2023 era) |
| Glassmorphism | Arc Browser landing, Apple WWDC, Vercel AI pages |
| Aurora | Luma.app, Framer editorial templates |
| Cyberpunk | Raycast.com, Linear dark mode, Vercel dark theme |
| Luxury | Net-a-Porter, Bang & Olufsen, Rolls-Royce |
| Editorial | NY Times digital, The Verge, Substack |
| Brutalist | Bloomberg Businessweek, Balenciaga (older), bejamas.io |

---

## Design Trend Patterns (2025–2026)

| Pattern | Description |
|---------|-------------|
| **Bento grids** | Asymmetric card layouts — CSS Grid with span-2 featured items |
| **Gradient text** | Brand colors applied to headings via clip-text |
| **Mesh gradients** | Multi-point radial gradients layered for atmospheric depth |
| **Scroll-linked** | Animations tied to scroll position via Intersection Observer |
| **Noise texture** | Subtle grain overlay using SVG filter or background-image |
| **Glassmorphism nav** | Frosted glass header with backdrop-blur |
| **Dark mode first** | Dark as primary theme, light as variant |
| **Variable fonts** | Single font file with weight/width axes |
| **Aurora backgrounds** | Full-bleed gradient spheres, animated or static |
| **Kinetic type** | Text that scrolls, morphs, or reacts to cursor |

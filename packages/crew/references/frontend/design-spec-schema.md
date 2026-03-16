# Design Spec Schema

Standard contract between extraction skills and build skills. Every extraction produces this format; every build consumes it.

## When to Use

- `/design-extraction` outputs `design-spec.json`
- `/website` Mode B/C consumes `design-spec.json`
- `/website-project` Phase 1 produces, Phase 3 consumes
- `/website-theme`, `/website-layout` can consume for "match exactly" mode

## File Location

- Inline in agent prompt when < 500 tokens or 1-2 consumers
- `.context/design-spec.json` when 3+ agents need it or across phases

## Schema

```json
{
  "version": "1.0",
  "meta": {
    "name": "Project Name",
    "source_url": "https://example.com",
    "source_type": "url | figma | screenshot | discovery",
    "archetype": "minimal | bold | playful | corporate | luxury | organic | brutalist | editorial | neubrutalism | glassmorphism | aurora | cyberpunk",
    "archetype_modifier": null,
    "sector": "saas | agency | restaurant | ...",
    "mood": "clean, professional, modern"
  },

  "theme": {
    "mode": "light | dark",
    "colors": {
      "primary_hsl": "217 91% 60%",
      "secondary_hsl": "187 70% 50%",
      "accent_hsl": "217 40% 96%",
      "surface_hsl": "217 10% 97%",
      "background": "#0a0a0a",
      "foreground": "#fafafa",
      "muted": "#262626",
      "muted_foreground": "#a3a3a3",
      "border": "#262626",
      "card": "#141414",
      "card_foreground": "#fafafa"
    },
    "border_radius": "8px",
    "shadows": {
      "sm": "none",
      "md": "0 1px 2px rgba(0,0,0,0.04)",
      "lg": "0 4px 12px rgba(0,0,0,0.06)"
    },
    "surfaces": {
      "blur": "backdrop-blur-md",
      "gradients": ["linear-gradient(...)"],
      "overlays": []
    }
  },

  "typography": {
    "fonts": {
      "sans": "Inter",
      "serif": "Playfair Display",
      "mono": null
    },
    "google_fonts_import": "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@400;700&display=swap",
    "heading_font": "sans | serif",
    "scale": {
      "h1": {
        "size": "3.5rem",
        "weight": "700",
        "line_height": "1.1",
        "letter_spacing": "-0.02em"
      },
      "h2": {
        "size": "2.25rem",
        "weight": "600",
        "line_height": "1.2",
        "letter_spacing": "-0.01em"
      },
      "h3": {
        "size": "1.5rem",
        "weight": "600",
        "line_height": "1.3",
        "letter_spacing": "0"
      },
      "h4": {
        "size": "1.25rem",
        "weight": "600",
        "line_height": "1.4",
        "letter_spacing": "0"
      },
      "body": {
        "size": "1rem",
        "weight": "400",
        "line_height": "1.6",
        "letter_spacing": "0"
      },
      "small": {
        "size": "0.875rem",
        "weight": "400",
        "line_height": "1.5",
        "letter_spacing": "0"
      }
    },
    "text_styles": {
      "uppercase_labels": false,
      "tight_heading_spacing": true
    }
  },

  "layout": {
    "max_width": "1280px",
    "container_padding": {
      "desktop": "2rem",
      "tablet": "1.5rem",
      "mobile": "1rem"
    },
    "section_spacing": "py-20 sm:py-28",
    "grid_pattern": "centered | asymmetric | full-bleed | bento | broken-grid",
    "density": "compact | balanced | spacious | airy",
    "breakpoints": {
      "sm": "640px",
      "md": "768px",
      "lg": "1024px",
      "xl": "1280px"
    },
    "nav_classes": "bg-background/80 backdrop-blur-md border-b border-border",
    "footer_classes": "bg-muted text-foreground border-t border-border"
  },

  "motion": {
    "duration_micro": "200ms",
    "duration_page": "400ms",
    "ease": "cubic-bezier(0.4, 0, 0.2, 1)",
    "ease_array": [0.4, 0, 0.2, 1],
    "distance": "24px",
    "stagger": "0.08s",
    "page_load": {
      "type": "stagger-fade-up",
      "delay_per_element": "0.08s",
      "initial_delay": "0.2s"
    },
    "scroll_reveal": {
      "type": "fade-up | fade-in | slide-left | none",
      "threshold": 0.1,
      "once": true
    },
    "hover_effects": {
      "buttons": "brightness + shadow",
      "cards": "translateY(-4px) + shadow-lg",
      "links": "color shift"
    },
    "special": []
  },

  "variants": {
    "hero": "centered | split | fullscreen | bento | statement | asymmetric",
    "nav": "bar | pill | transparent | sidebar | split-bar",
    "footer": "4-column | minimal | dark-inverted | split",
    "features": "card-grid | bento | alternating-rows | icon-list | stacked-full",
    "testimonials": "card-carousel | single-spotlight | grid-mosaic | inline-quotes",
    "cta": "banner | card | split-visual",
    "pricing": "tier-cards | comparison-table | toggle-plans"
  },

  "components": {
    "navbar": {
      "position": "fixed | sticky | static",
      "height": "64px",
      "background": "transparent | solid | blur",
      "has_cta": true,
      "mobile_menu": "hamburger | sheet | fullscreen",
      "items": ["Home", "About", "Projects", "Blog", "Contact"]
    },
    "hero": {
      "elements": [
        "badge",
        "headline",
        "subtitle",
        "cta_primary",
        "cta_secondary",
        "image"
      ],
      "arrangement": "description of spatial layout"
    },
    "buttons": {
      "primary": {
        "bg": "#fff",
        "color": "#000",
        "border_radius": "8px",
        "padding": "12px 24px",
        "font_size": "14px",
        "font_weight": "500",
        "hover": "opacity 0.9"
      },
      "secondary": {
        "bg": "transparent",
        "color": "#fff",
        "border": "1px solid rgba(255,255,255,0.2)",
        "border_radius": "8px",
        "padding": "12px 24px",
        "hover": "border-color rgba(255,255,255,0.5)"
      }
    },
    "cards": {
      "bg": "#141414",
      "border": "1px solid #262626",
      "border_radius": "12px",
      "shadow": "none",
      "padding": "24px",
      "hover": "border-color #404040"
    },
    "badges": null,
    "inputs": null,
    "special": []
  },

  "pages": [
    {
      "path": "/",
      "title": "Home",
      "sections": [
        { "type": "nav", "variant": "transparent" },
        {
          "type": "hero",
          "variant": "centered",
          "content_summary": "Main headline + 2 CTAs"
        },
        { "type": "features", "variant": "card-grid", "item_count": 6 },
        { "type": "cta", "variant": "banner" },
        { "type": "footer", "variant": "minimal" }
      ]
    }
  ],

  "assets": {
    "images": [
      {
        "url": "https://...",
        "alt": "description",
        "usage": "hero background",
        "dimensions": "1920x1080"
      }
    ],
    "svgs": [],
    "external_stylesheets": [],
    "placeholder_strategy": "gradient | blur | solid-color"
  }
}
```

## Required Fields

Every design-spec.json MUST have values for:

- `meta.source_type` and `meta.archetype`
- `theme.colors.primary_hsl` through `theme.colors.surface_hsl`
- `theme.border_radius`
- `typography.fonts.sans` and `typography.heading_font`
- `typography.scale.h1` through `typography.scale.body`
- `layout.max_width`, `layout.section_spacing`, `layout.nav_classes`, `layout.footer_classes`
- `motion.duration_micro`, `motion.duration_page`, `motion.ease`
- `variants.hero`, `variants.nav`, `variants.footer`, `variants.features`
- `pages` array with at least one page and its sections

## Optional Fields

- `theme.surfaces` — only if blur/gradient/overlay effects detected
- `motion.special` — marquees, tickers, parallax, etc.
- `components.special` — non-standard components
- `assets` — only needed for replication mode
- `typography.scale.h4`, `typography.scale.small` — fill from scale if not directly extracted

### Mode C Replication Fields

Required for Mode C replication pipelines, optional otherwise.

- **`pages[].sections[].content`** — per-section scraped content object:
  ```json
  {
    "headings": ["Main Heading", "Sub Heading"],
    "paragraphs": ["First paragraph text...", "Second paragraph..."],
    "ctas": ["Get Started", "Learn More"],
    "images": [{ "src": "https://...", "alt": "description" }],
    "lists": [["Item 1", "Item 2"]],
    "raw_markdown": "## Main Heading\n\nFirst paragraph text..."
  }
  ```
- **`pages[].sections[].screenshot_path`** — path to cropped screenshot of this section from original site (e.g., `./output/screenshots/section-0-hero.png`)
- **`assets.local_manifest`** — downloaded asset mapping:
  ```json
  {
    "base_dir": "./output/assets",
    "files": [
      {
        "original_url": "https://example.com/hero.jpg",
        "local_path": "images/hero.jpg",
        "type": "image"
      },
      {
        "original_url": "https://fonts.gstatic.com/s/inter/v13/font.woff2",
        "local_path": "fonts/font.woff2",
        "type": "font"
      }
    ]
  }
  ```
- **`meta.firecrawl_content`** — full Firecrawl scrape output:
  ```json
  {
    "markdown": "# Page Title\n\nFull page content as markdown...",
    "links": ["https://example.com/about", "https://example.com/pricing"],
    "metadata": { "title": "Page Title", "description": "Meta description" }
  }
  ```

## Mapping to Studio Tokens

When scaffolding via `scripts/scaffold.sh`, map spec fields to template tokens:

| Spec Field                   | Studio Token          |
| ---------------------------- | --------------------- |
| `theme.colors.primary_hsl`   | `PRIMARY_COLOR_HSL`   |
| `theme.colors.secondary_hsl` | `SECONDARY_COLOR_HSL` |
| `theme.colors.accent_hsl`    | `ACCENT_COLOR_HSL`    |
| `theme.colors.surface_hsl`   | `SURFACE_COLOR_HSL`   |
| `typography.fonts.sans`      | `FONT_SANS_IMPORT`    |
| `typography.fonts.serif`     | `FONT_SERIF_IMPORT`   |
| `typography.heading_font`    | `HEADING_FONT`        |
| `theme.border_radius`        | `BORDER_RADIUS`       |
| `theme.shadows.sm/md/lg`     | `SHADOW_SM/MD/LG`     |
| `motion.duration_micro`      | `DURATION_MICRO`      |
| `motion.duration_page`       | `DURATION_PAGE`       |
| `motion.ease_array`          | `ANIM_EASE`           |
| `motion.distance`            | `ANIM_DISTANCE`       |
| `motion.stagger`             | `ANIM_STAGGER`        |
| `layout.nav_classes`         | `NAV_CLASSES`         |
| `layout.footer_classes`      | `FOOTER_CLASSES`      |
| `layout.section_spacing`     | `SECTION_PADDING`     |
| `layout.max_width`           | `LAYOUT_MAX_WIDTH`    |
| `meta.archetype`             | `DESIGN_ARCHETYPE`    |

## Validation Rules

1. All HSL values must be in `"H S% L%"` format (no `hsl()` wrapper)
2. All hex colors must include `#` prefix
3. Font names must be valid Google Fonts names (verify against `references/frontend/design-resources.md`)
4. Variant names must match the options listed in `references/frontend/component-variants.md`
5. `pages[].sections[].type` must be one of: nav, hero, features, testimonials, pricing, cta, faq, stats, logos, team, blog, contact, steps, gallery, footer, custom
6. WCAG contrast: primary text on background >= 4.5:1

---
title: Color and Contrast
domain: frontend/design
source: adapted from impeccable (github.com/pbakaus/impeccable, Apache-2.0)
---

# Color & Contrast

Color makes the aesthetic land or fall apart. Commit to a cohesive palette: dominant neutrals with sharp accents outperform timid, evenly-distributed palettes.

## Use OKLCH, Not HSL

> **Stop using HSL.** Use OKLCH (or LCH).

OKLCH is perceptually uniform: equal steps in lightness *look* equal. HSL does not deliver this — 50% lightness in yellow looks bright, 50% in blue looks dark.

```
oklch(lightness chroma hue)
  lightness: 0–100%
  chroma:    ~0–0.4
  hue:       0–360
```

Build a scale by holding chroma + hue roughly constant and varying lightness — but **reduce chroma as you approach white or black**. High chroma at extreme lightness looks garish. A light blue at 85% lightness wants ~0.08 chroma, not the 0.15 of your base.

The hue is a brand decision. Do not reach for blue (hue ~250) or warm orange (hue ~60) by reflex — those are the dominant AI-design defaults, not the right answer for any specific brand.

## Tinted Neutrals

> **Pure gray is dead.**

A neutral with zero chroma feels lifeless next to a colored brand. Add a tiny chroma (**0.005–0.015**) to every neutral, hued toward your brand. Small enough that it does not read as "tinted" consciously; creates subconscious cohesion.

Tint toward THIS brand's hue. If the brand is teal, neutrals lean teal. If amber, they lean amber. Do not default to warm-orange-tint or cool-blue-tint — those are the two laziest defaults and create their own monoculture.

## Palette Structure

| Role | Purpose | Count |
|------|---------|-------|
| Primary | Brand, CTAs, key actions | 1 color, 3–5 shades |
| Neutral | Text, backgrounds, borders | 9–11 shade scale |
| Semantic | Success, error, warning, info | 4 colors, 2–3 shades each |
| Surface | Cards, modals, overlays | 2–3 elevation levels |

Skip secondary/tertiary unless you need them. Most apps work fine with one accent.

## 60-30-10 (Weight, Not Pixels)

This rule is about **visual weight**, not pixel count:

- **60%** — neutral backgrounds, whitespace, base surfaces
- **30%** — secondary (text, borders, inactive states)
- **10%** — accent (CTAs, highlights, focus)

Common mistake: using the accent everywhere because "it's the brand color." Accents work *because* they are rare. Overuse kills their power.

## WCAG Contrast

| Content | AA | AAA |
|---------|----|----|
| Body text | 4.5:1 | 7:1 |
| Large text (18px+ / 14px bold) | 3:1 | 4.5:1 |
| UI components, icons | 3:1 | 4.5:1 |

Gotcha: placeholder text still needs 4.5:1. Most "light gray on white" placeholders fail.

## Dangerous Combinations

- Light gray text on white — the #1 accessibility fail.
- **Gray text on any colored background** — washed out, dead. Use a darker shade of the background color itself, or transparency.
- Red on green (or vice versa) — 8% of men cannot distinguish.
- Blue on red — vibrates visually.
- Yellow on white — almost always fails.
- Thin light text over images — unpredictable contrast.

## Never Use Pure Gray or Pure Black

Pure gray (`oklch(50% 0 0)`) and pure black (`#000`) do not exist in nature — real shadows and surfaces always carry a color cast. Even chroma 0.005–0.01 feels natural without reading as tinted.

## Dark Mode ≠ Inverted Light Mode

You cannot just swap colors. Different design decisions:

| Light | Dark |
|-------|------|
| Shadows for depth | Lighter surfaces for depth (no shadows) |
| Dark text on light | Light text on dark (**reduce** font weight slightly, e.g. 350 instead of 400) |
| Vibrant accents | Desaturate accents slightly |
| White backgrounds | Never pure black — use dark neutral (oklch 12–18% lightness) |

In dark mode, depth comes from surface **lightness**, not shadow. Build a 3-step surface scale (15% / 20% / 25% lightness) using the same hue+chroma as your brand color, varying only lightness.

## Theme Selection (Light vs Dark)

Theme is **derived** from audience and viewing context, not picked from a default.

| Product | Context | Theme |
|---------|---------|-------|
| Perp DEX during fast trading | Focused, low-light | Dark |
| Hospital portal, anxious patients on phones at night | Calm, trustworthy | Light |
| Children's reading app | Day, parental supervision | Light |
| Vintage motorcycle forum (garage, 9pm) | Atmospheric | Dark |
| SRE observability dashboard | Dark office | Dark |
| Wedding planning on Sunday morning | Bright, optimistic | Light |
| Music player for headphone listening at night | Immersive | Dark |

Do not default to light "to play it safe." Do not default to dark "to look cool." Both defaults are the lazy reflex.

## Tokens

Two layers: primitives (`--blue-500`) and semantic (`--color-primary: var(--blue-500)`). For dark mode, redefine only the semantic layer.

## Alpha Is a Design Smell

Heavy `rgba`/`hsla` usage usually signals an incomplete palette. Alpha creates unpredictable contrast, perf overhead, inconsistency. Define explicit overlay colors per context. Exception: focus rings and interactive states where see-through is required.

## Testing

Do not trust your eyes. Use WebAIM Contrast Checker, Chrome DevTools vision-deficiency emulation, Polypane.

## Rules Checklist

**DO**

- Use modern CSS color functions: `oklch`, `color-mix`, `light-dark`.
- Tint neutrals toward the brand hue.
- Design light and dark as distinct systems.

**DON'T**

- Use gray text on colored backgrounds.
- Use pure black (`#000`) or pure white (`#fff`) anywhere.
- Reach for the AI palette: cyan-on-dark, purple-to-blue gradients, neon on dark.
- Default to dark-with-glowing-accents. It looks "cool" without requiring design decisions.
- Default to light "to be safe." The point is to choose.

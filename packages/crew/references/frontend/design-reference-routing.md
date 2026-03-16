# Design Reference Routing

When the user provides an external design reference URL, route as follows:

## Figma URL

If the user provides a **Figma URL** (`figma.com/design/...` or `figma.com/file/...`), use `/design-extraction` to extract design tokens and layout structure. The Figma design becomes the single source of truth. Output: `design-spec.json`.

## Live Website URL

If the user provides a **live website URL** (any non-Figma URL), use `/design-extraction` which drives `agent-browser` CLI following `references/frontend/url-design-extraction.md`. Output: `design-spec.json`.

## Screenshot / Image

If the user provides a **screenshot or image file** (`.png`, `.jpg`, `.webp`), use `/design-extraction` with visual analysis. Output: `design-spec.json`.

## After Extraction

All extraction paths produce a `design-spec.json` conforming to `references/frontend/design-spec-schema.md`. The consuming skill uses it as follows:

| Consuming Skill                  | How It Uses the Spec                                           |
| -------------------------------- | -------------------------------------------------------------- |
| `/website` Mode B (spec-fed)     | Design system for a new site — skips discovery/design steps    |
| `/website` Mode C (replicate)    | Exact reproduction — skips discovery/design/content steps      |
| `/website-theme` + `/website-layout` | Apply extracted design to existing site — skips propositions   |
| `/website-theme`                 | Theme tokens only (colors, fonts, shadows) — match mode        |
| `/website-layout`                | Layout structure only (sections, grids, variants) — match mode |

**User confirmation:** Always ask the user whether to **match/replicate** the design exactly or use it as **inspiration** for propositions.

- **Match/Replicate** → skip proposition generation, apply spec directly
- **Inspiration** → use spec data to inform the 3 propositions (theme/layout/redesign skills)

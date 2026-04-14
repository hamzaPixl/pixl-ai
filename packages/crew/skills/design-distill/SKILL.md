---
name: design-distill
description: "Strip overdesign from a UI: remove redundant visual layers (nested cards, repeated headers, decorative gradients), consolidate color palette, reduce shadow/border decoration. The 'less is more' pass. Use when asked to simplify a UI, remove visual noise, distill a design, fix overdesign, or strip redundancy."
allowed-tools: Read, Edit, Glob, Grep, Bash
argument-hint: "[component-path | page-path]"
---

## Overview

Ruthless simplification pass. Removes decorative noise, flattens nested containers, consolidates color and elevation, and strips redundant headers/labels. Preserves information hierarchy, brand accent, and semantic color. Use before `/design-polish` when the UI is fundamentally over-decorated — polishing overdesigned UI just polishes the noise.

**How this differs**:
- `/design-polish` — adds craft (focus states, micro-interactions). This skill — removes noise.
- `/code-reduction` — removes unused code. This skill — removes unused visual weight.
- `/design-variants` — explores new directions. This skill — prunes the current direction.

## Required References

Read before starting:
- `references/frontend/design/anti-patterns.md` — overdesign tells
- `references/frontend/design/craft-process.md` — "what to keep" heuristics
- `references/frontend/design/spatial-design.md` — whitespace as a design element

## Principles

**Remove**:
- Decorative gradients (backgrounds, borders, text) with no semantic meaning
- Sparkline decorations, random dots, ambient floating elements
- Nested cards (card inside card inside card)
- Redundant headers (section header + card header + item header saying similar things)
- Excessive shadows (`shadow-2xl` stacked on `shadow-lg`, glow effects everywhere)
- Multi-layer borders (border + outline + ring all at once)
- More than 3 accent colors — consolidate to 1 brand + 1 accent + neutrals
- Icon-for-icon's-sake (decorative icons next to every label)
- Badges, pills, and chips added for visual weight, not information

**Keep**:
- Information hierarchy (H1 > H2 > body still reads clearly)
- Brand accent color (one, distinctive, consistent)
- Semantic colors (success/warn/error/info — never merge these)
- Functional borders (input borders, table cell separators)
- One shadow token for elevation (usually `shadow-sm` or `shadow-md`)
- Interactive affordances (hover/focus states — those are `/design-polish` territory)

## Step 1: Inventory Visual Weight

Scan the target files and count:

```bash
# Count decorative patterns
grep -rEn "gradient-to|shadow-(lg|xl|2xl)|ring-|border-[234]" <target>
grep -rEn "bg-gradient|from-.*to-" <target>
grep -rEn "<div class=.*card.*><div class=.*card" <target>  # nested cards
```

Build a weight inventory:
- Gradients: N occurrences
- Heavy shadows (`lg`+): N
- Nested containers: N
- Distinct accent colors: N
- Icons per section: avg N

## Step 2: Distill in Order

### 2.1 Flatten nesting

- Card inside card → remove outer card, keep inner content
- Section header + immediate sub-header saying the same thing → keep one
- Container > Container > Content → collapse to one container

### 2.2 Consolidate color

- Audit all accent colors used. If >2, pick one brand + one accent, migrate others to neutrals
- Replace decorative gradients with solid brand color
- Merge `bg-gray-50`, `bg-slate-50`, `bg-zinc-50` variants — pick one neutral scale

### 2.3 Reduce elevation

- Pick one shadow token for elevation. Remove all others.
- Remove ring+border+shadow stacks — keep one
- Replace glow effects with subtle shadow or remove entirely

### 2.4 Strip decoration

- Remove sparklines, floating orbs, random dots, gradient blobs with no purpose
- Remove icons that only exist for visual weight (e.g., icon next to every bullet when the list is already clear)
- Remove badges/pills that repeat information already in the heading

### 2.5 Reclaim whitespace

- Every removed element is a chance to increase whitespace
- After removals, widen padding on the remaining content
- Let hierarchy breathe — whitespace does the work decoration was doing

## Step 3: Before/After Example

Before (overdesigned card):
```tsx
<div className="p-1 bg-gradient-to-r from-purple-500 to-pink-500 rounded-xl">
  <div className="bg-white rounded-lg shadow-2xl p-6 ring-1 ring-gray-200">
    <div className="flex items-center gap-2 mb-4">
      <Sparkle className="text-purple-500" />
      <span className="text-xs font-bold text-purple-500 uppercase">New Feature</span>
    </div>
    <h3 className="text-xl font-bold bg-gradient-to-r from-purple-500 to-pink-500 bg-clip-text text-transparent">
      Ship Faster
    </h3>
    <p className="text-gray-600 mt-2">Deploy in one click.</p>
  </div>
</div>
```

After (distilled):
```tsx
<div className="bg-card rounded-lg shadow-sm p-6 border border-border">
  <span className="text-xs font-medium text-primary uppercase tracking-wide">New</span>
  <h3 className="mt-2 text-xl font-semibold text-foreground">Ship Faster</h3>
  <p className="mt-2 text-muted-foreground">Deploy in one click.</p>
</div>
```

Removed: outer gradient wrapper, sparkle icon, heavy shadow, ring, gradient text, redundant "Feature" label, color noise.
Kept: hierarchy, brand accent on eyebrow label, semantic elevation.

## Step 4: Verify

1. `git diff --stat` — expect net line reduction (distill removes more than it adds)
2. Visual check: does the page still communicate the same hierarchy?
3. Read it like a user — is the primary action still obvious?

Red flags that signal over-distillation:
- Primary CTA no longer visually distinct
- Sections blur into each other (no separation)
- Brand identity gone — site looks like unstyled Markdown

If any red flag, restore the specific signal that did the work.

## Step 5: Report

```
Distilled 4 components:
  Gradients removed:     7
  Nested cards flattened: 3
  Shadows consolidated:  12 → 1 token
  Accent colors:          5 → 2
  Net line reduction:    -84 lines

Next: run /design-polish to add craft to the simplified base.
```

## Gotchas

- **Don't strip brand identity** — if the brand IS a bold gradient logo, don't delete it. Context from `.design-context.md` matters.
- **Don't delete semantic color** — success green, error red, warn amber stay, even if you consolidate brand palette
- **Distill once, then polish** — running polish on overdesigned UI wastes effort. Order matters: distill → polish.
- **Test dark mode** — removing a border or shadow might break the element in dark mode. Verify both themes.
- **Keep motion removal separate** — `/design-polish` owns motion. This skill touches static visual weight only.

---
title: Craft Process
domain: frontend/design
source: adapted from impeccable (github.com/pbakaus/impeccable, Apache-2.0)
---

# Craft Process

A structured flow for building a feature with impeccable UX and UI: shape the design, load the right references, build, iterate visually, and present. The bar is not "it works" — the bar is "this delights."

## Step 1: Shape the Design

Produce a confirmed design brief before writing any code. The brief is your blueprint — every implementation decision should trace back to it. Include at minimum:

- Users and context of use.
- Job to be done.
- Brand personality (3 concrete words — not "modern" or "elegant").
- Aesthetic direction (committed, bold: brutalist, editorial, industrial, soft-pastel, maximalist, etc.).
- Theme (light / dark, derived from context — see `color-and-contrast.md`).
- Anti-references (what it must NOT look like).
- Recommended references (which of the files below to consult).

If a brief already exists (e.g. from `/design-extraction` or a `.design-context.md` file), use it. Do not redo the shape step.

## Step 2: Load References

From the brief's "Recommended References" section, read the relevant files. Always consult:

- `spatial-design.md` — layout and spacing.
- `typography.md` — type hierarchy and font selection.

Add conditionally:

| Brief need | Reference |
|------------|-----------|
| Complex interactions, forms, modals, dropdowns | `interaction-design.md` |
| Animation or transitions | `motion-design.md` |
| Color-heavy or themed | `color-and-contrast.md` |
| Mobile / responsive requirements | `responsive-design.md` |
| Heavy on copy, labels, errors | `ux-writing.md` |

Also read `anti-patterns.md` before starting — the AI Slop Test is the final gate.

## Step 3: Build

Implement the feature following the design brief. Work in this order:

1. **Structure** — HTML / semantic markup for the primary state. No styling yet.
2. **Layout and spacing** — establish spatial rhythm and visual hierarchy.
3. **Typography and color** — apply the type scale and color system.
4. **Interactive states** — hover, focus, active, disabled (see the 8-state list in `interaction-design.md`).
5. **Edge-case states** — empty, loading, error, overflow, first-run.
6. **Motion** — purposeful transitions. Skip it if it is not earning its place.
7. **Responsive** — adapt for different viewports. Redesign for the context; do not just shrink.

### Build Discipline

- Test with real (or realistic) data at every step, never placeholder lorem.
- Check each state as you build it, not all at the end.
- If you discover a design question mid-build, stop and ask rather than guessing.
- Every visual choice must trace back to something in the brief.

## Step 4: Visual Iteration

This step is critical. Do not stop after the first pass.

Open the result in a browser. If browser automation is available, use it. Otherwise, ask the user to open it and provide feedback.

Iterate through these checks:

1. **Does it match the brief?** Compare the live result against every section. Fix discrepancies.
2. **Does it pass the AI Slop Test?** If someone saw this and said "AI made this," would they believe it immediately? If yes, it needs more design intention. See `anti-patterns.md`.
3. **Check against the DON'T lists.** Fix any anti-pattern violations.
4. **Check every state.** Navigate empty, error, loading, overflow, first-run. Each should feel intentional, not like an afterthought.
5. **Check responsive.** Resize the viewport. Does it adapt well or just shrink?
6. **Check the details.** Spacing consistency, type hierarchy clarity, color contrast, interactive feedback, motion timing, optical alignment.

After each round of fixes, verify visually again. **Repeat until you would be proud to show this to the user.**

## Step 5: Present

Present the result:

- Show the feature in its primary state.
- Walk through key states (empty, error, responsive).
- Explain design decisions that connect back to the brief.
- Ask: "What is working? What is not?"

Iterate on feedback. Good design is rarely right on the first pass.

## Craft Cadence

- **Shape → Load → Build → Iterate → Present** — do not skip stages.
- **Shape once, iterate many.** The brief is cheap; reworking code because the brief was vague is expensive.
- **Commit after each logical unit.** Structure commit, layout commit, states commit, responsive commit. Makes review and revert surgical.
- **Match complexity to vision.** Maximalist designs demand elaborate code with extensive animation and effect. Minimalist designs demand restraint, precision, and careful attention to spacing, typography, and subtle details. Both are legitimate; indecision is not.
- **Never converge.** Vary between light and dark themes, different fonts, different aesthetics across projects. Repeated "safe" choices are the monoculture trap.

---
title: Design Context Protocol
domain: frontend/design
source: adapted from impeccable (github.com/pbakaus/impeccable, Apache-2.0)
---

# Design Context Protocol

Design work without project context produces generic output. Before doing any design work, a `.design-context.md` file MUST exist at the project root and contain audience, use cases, and brand personality.

**Critical**: you cannot infer this context by reading the codebase. Code tells you what was built, not who it is for or what it should feel like. Only the person who knows the brand can provide this. Do not skip straight to implementation.

## Gathering Order

1. **Check current instructions.** If the loaded CLAUDE.md or a skill prompt already includes a `Design Context` section, proceed immediately.
2. **Check `.design-context.md` at project root.** If it exists and contains the required sections, proceed.
3. **Run the 3-step protocol below.** If neither source has context, run it NOW before anything else. Do not attempt to infer context from the codebase.

## Step 1: Explore the Codebase

Before asking any question, scan the project for what you can discover:

- `README.md` and docs — stated purpose, target audience, goals.
- `package.json` / config files — tech stack, dependencies, existing design libraries.
- Existing components — current spacing, typography, patterns in use.
- Brand assets — logos, favicons, defined color values.
- Design tokens, CSS variables, style guides.

Note what you have learned and what remains unknown. Do not ask the user about anything you already know.

## Step 2: Ask UX-Focused Questions

Ask only what you could not infer. Skip any question already answered by the codebase scan.

### Users & Purpose

- Who uses this? What is their context when they use it (device, setting, time of day, emotional state)?
- What job are they trying to get done?
- What emotions should the interface evoke (confidence, delight, calm, urgency)?

### Brand & Personality

- How would you describe the brand personality in 3 concrete words — NOT "modern" or "elegant" (dead categories). Try pairs like "warm and mechanical and opinionated" or "calm and clinical and careful".
- Any reference sites or apps that capture the right feel? Specifically, which parts?
- What should this explicitly NOT look like? (Anti-references are as important as references.)

### Aesthetic Preferences

- Visual direction: minimal, bold, editorial, brutalist, organic, industrial, playful, refined, maximalist?
- Light mode, dark mode, or both? (Theme should derive from audience and viewing context — see `color-and-contrast.md`.)
- Any colors or fonts that must be used, or must be avoided?

### Accessibility & Inclusion

- WCAG target (AA or AAA)?
- Known user needs: reduced motion, high contrast, screen-reader usage, color-vision deficiency?

## Step 3: Write `.design-context.md`

Synthesize findings and user answers into the file at project root. If the file exists, update in place. Offer to also append the section to CLAUDE.md so it loads into every session.

### Template

```markdown
# Design Context

## Audience

[Who they are. Ages, roles, tech literacy.
 Context of use: device, setting, time of day, emotional state.
 What they want to accomplish here.]

## Use Cases

[Top 3-5 jobs to be done, ordered by frequency or importance.
 Note any constraints — e.g. "used one-handed on transit",
 "consumed in a dark office for 6+ hours", "accessed under time pressure".]

## Brand Personality

**Three words**: [word 1, word 2, word 3]
(Concrete pairs like "warm and mechanical and opinionated", NOT "modern" or "elegant".)

**Emotional goals**: [confidence / calm / urgency / delight / trust / focus / ...]

**Physical-object analogy**: [the brand as a tangible thing — typewriter ribbon,
museum caption, fabric label, mainframe manual, hand-painted shop sign.
This anchors font and material choices away from reflex defaults.]

## Voice & Tone

**Voice (constant)**: [describe how the brand always sounds —
e.g. "direct, human, mildly irreverent, never cute"]

**Tone shifts**:
- Success: [...]
- Error:   [empathetic, helpful, never humorous]
- Loading: [reassuring, specific]
- Destructive confirm: [serious, clear]

## Aesthetic Direction

**Committed direction**: [pick one — brutalist / editorial / industrial /
soft-pastel / maximalist / Swiss-modern / retro-futuristic / organic / ...]

**Theme**: [light | dark | both] — justified by audience and viewing context,
not by default.

**References**: [3-5 sites/apps/objects, with the specific part that inspires —
"Linear's command palette density", "Stripe Press's serif hierarchy",
"Teenage Engineering's industrial iconography".]

## Anti-References (what NOT to look like)

[Equally important. Name concrete targets:
 - "Not another glassmorphism SaaS landing page"
 - "Not another purple-to-blue gradient hero"
 - "Not a Notion/Linear clone"
 - "Not the hero-metric dashboard template"
 - "Not Inter + Fraunces + rounded icons"
 See anti-patterns.md for the full ban list.]

## Design Principles

[3-5 principles derived from the conversation that guide every decision.
 E.g.:
 1. Density over whitespace — power users read dashboards, not homepages.
 2. Typography does the heavy lifting, color is restrained.
 3. Every state is designed — empty, loading, error, first-run.
 4. Motion reinforces state change, never decorates.]

## Accessibility Baseline

- WCAG: [AA | AAA]
- Reduced motion: [supported / required / n/a]
- Color-vision: [no red/green pairing, tested with emulation]
- Keyboard: [all flows fully operable without pointer]
```

## After Writing

- Confirm completion with the user. Summarize the 3 brand words, the theme, and the 3–5 design principles.
- Ask whether they want the section also appended to `CLAUDE.md`. If yes, append or update in place.
- Re-run the protocol whenever the brand or audience changes. `.design-context.md` is living — update it, do not accumulate conflicting context.

## Why This Exists

Without this protocol, design skills converge on the same defaults across every project: Inter, Fraunces, purple-to-blue gradients, glass cards, hero-metric dashboards. The 3-word brand voice + physical-object analogy + anti-references together force the model out of its reflex patterns and onto a specific brand.

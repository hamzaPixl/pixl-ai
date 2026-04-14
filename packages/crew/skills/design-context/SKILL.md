---
name: design-context
description: "Interactive Q&A to capture brand voice, audience, personality, and anti-references, then write .design-context.md at project root. Required before any net-new design work. Use when starting a new design project, when no .design-context.md exists, or when asked to capture brand voice, audience, design personality, or set up design context."
allowed-tools: Read, Write, Bash, Glob, Grep
argument-hint: "[--force to overwrite existing .design-context.md]"
---

## Overview

Captures the brand, audience, and aesthetic constraints that every subsequent design decision depends on. Without this file, design skills (`/design-critique`, `/design-variants`, `/website-theme`, `/frontend-design`) work blind and produce generic AI-slop output. Run once per project; re-run when the brand pivots.

The output file `.design-context.md` is read by:
- `/design-critique` — scores originality against declared voice
- `/design-variants` — generates directions aligned with audience
- `/website-theme` — selects palette and font pairing
- `/frontend-design` — injects brand voice into copy and component style
- `/content-marketing` — enforces voice across written content

## Required References

Read before starting:
- `references/frontend/design/design-context-protocol.md` — the canonical schema and examples
- `references/frontend/design/anti-patterns.md` — so you can prompt for anti-references intelligently

## Step 1: Explore the Codebase

Before asking questions, gather signals from the project:

```bash
# Existing brand hints
ls public/ | grep -Ei "logo|brand|favicon"
grep -rEn "primary|brand|accent" tailwind.config.* src/styles 2>/dev/null | head -20

# Existing copy for tone inference
find . -name "*.tsx" -path "*/landing/*" -o -path "*/marketing/*" 2>/dev/null | head -5
grep -rEn "<h1|<h2" src/app src/pages 2>/dev/null | head -10

# Package.json name/description
cat package.json | grep -E '"name"|"description"' 2>/dev/null

# Check if .design-context.md already exists
test -f .design-context.md && echo "EXISTS" || echo "NONE"
```

Summarize findings as "what I already know" before asking questions. If `.design-context.md` exists and `--force` was not passed, offer to review/update instead of overwrite.

## Step 2: Interactive Q&A

Ask 5-7 questions. Use `AskUserQuestion` if available, else plain prompts. Keep each question short and specific — no walls of text.

### Q1. Audience
"Who is the primary user? Describe in one sentence (role, context, what they care about)."

Example answers: "Senior backend engineers evaluating infra tools during a procurement cycle" / "Indie makers building their first SaaS, price-sensitive, self-serve"

### Q2. Primary Use Case
"What's the one thing a user needs to do or feel within 10 seconds of landing?"

### Q3. Personality (3 words)
"Pick 3 personality words for the brand. (Examples: technical+trustworthy+calm, playful+bold+approachable, editorial+considered+quiet.)"

### Q4. Voice & Tone
"When the product talks, does it sound more like:
(a) an expert peer — direct, precise, no fluff
(b) an enthusiastic guide — warm, encouraging, clear
(c) a witty insider — confident, dry humor, opinionated
(d) a calm professional — formal, measured, authoritative
(e) something else — describe it"

### Q5. Anti-References
"What should the design explicitly NOT look like? (Name 1-3 specific sites/products/aesthetics to avoid. Examples: 'not another Stripe clone', 'not Linear's glass morphism', 'not 2020-era Notion clean-but-boring'.)"

This is the most important question — it eliminates entire design spaces from exploration.

### Q6. Sector References
"Name 1-3 designs you admire (any industry). What specifically do you admire about each? (e.g., 'Vercel: typography hierarchy. Arc: motion. Patagonia: editorial photography.')"

### Q7. Accessibility & Constraints
"Any non-negotiables? E.g., WCAG AA minimum, right-to-left support, dark mode required, must work on low-end mobile, brand colors already locked by parent company."

## Step 3: Write .design-context.md

Use this exact template at the project root:

```markdown
# Design Context

> Last updated: <YYYY-MM-DD>
> Read by: /design-critique, /design-variants, /website-theme, /frontend-design, /content-marketing

## Audience

**Primary**: <one-sentence user description>
**Context**: <when/where/how they encounter the product>
**Cares about**: <top 2-3 concerns>

## Primary Use Case

Within 10 seconds, a user must: <what they do or feel>

## Personality

Three words: **<word1>**, **<word2>**, **<word3>**

## Voice & Tone

<selected option + one-line elaboration>

Do say: <2-3 example phrases that sound right>
Don't say: <2-3 phrases that would feel off-brand>

## Anti-References (what this should NOT be)

- <site/style 1> — because <reason>
- <site/style 2> — because <reason>
- <site/style 3> — because <reason>

## Sector References (what good looks like)

- <ref 1> — admire: <specific quality>
- <ref 2> — admire: <specific quality>
- <ref 3> — admire: <specific quality>

## Constraints

- Accessibility: <WCAG level, any specific requirements>
- Locale/RTL: <languages, RTL support>
- Theme: <light only / dark only / both>
- Device: <primary target devices>
- Brand locks: <any fixed colors, fonts, or marks from parent brand>

## Implications for Design

(Auto-derived from the above — design skills read this section to inform decisions.)

- Typography: <suggestion based on personality + audience>
- Color: <suggestion based on personality + anti-refs>
- Motion: <suggestion based on tone>
- Density: <compact vs spacious based on audience>
```

Fill every field. If the user gave a thin answer, prompt for one more detail rather than leaving a field vague.

## Step 4: Confirm and Handoff

After writing, print:

```
Wrote .design-context.md (<N> lines).

Next steps:
- /design-variants  — generate 3 direction options aligned with this context
- /website-theme    — apply a theme informed by personality + anti-refs
- /design-critique  — critique existing UI against this context
```

## Gotchas

- **Anti-references > references** — what to avoid is more useful than what to copy. Push for specificity if the user says "just make it nice".
- **Three personality words is a hard limit** — more than three dilutes the brief
- **Don't auto-generate content** — this file is input from the human. If they won't answer, surface the gap rather than inventing brand voice.
- **Update, don't append** — re-running the skill should produce a coherent replacement, not a growing log
- **File lives at project root** — not in `.claude/` or `docs/`. Root so every agent sees it.

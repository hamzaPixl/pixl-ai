---
name: i18n-setup
description: "Add EN/FR/NL multi-language support to a Next.js application. Handles discovery, infrastructure, translation extraction, translation quality validation, component integration, and content migration through a 6-step AI workflow."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
argument-hint: "<locales to support, e.g. en,fr,nl>"
---

## Overview

Adds internationalization (i18n) to a Next.js application supporting EN/FR/NL. Covers infrastructure setup, translation extraction, component integration, and optional CMS/MDX content migration.

## Required References

Before starting, read `references/frontend/i18n-conventions.md` for locale file structure, key naming, and pluralization patterns.

## Step 1: Discovery

1. Analyze existing Next.js configuration (App Router vs Pages Router)
2. Identify all user-facing strings in the codebase
3. Check for existing i18n setup or library
4. Determine content sources (hardcoded, CMS, MDX)
5. Count translatable strings for scope estimation

## Step 2: Infrastructure

1. Install and configure i18n library (next-intl or similar)
2. Set up locale routing (`/en/...`, `/fr/...`, `/nl/...`)
3. Create translation file structure (`messages/en.json`, `messages/fr.json`, `messages/nl.json`)
4. Add locale detection and switching
5. Configure middleware for locale routing

## Step 3: Translation Extraction (Parallel — 3 Agents)

Spawn 3 Explore agents to scan the codebase in parallel:

1. Extract all hardcoded strings from components
2. Generate translation keys following a consistent naming convention
3. Create initial translation files with English as source

## Step 4: Translation Quality Pass

After generating English source strings, translate to each target locale with these **mandatory rules**:

### French (fr)

- **All diacritics are required** — never omit accents: é è ê ë à â ç ù û ô î ï œ æ
- Common mistakes to avoid:
  - "évenement" → **événement**, "parametre" → **paramètre**, "creer" → **créer**
  - "deja" → **déjà**, "a" (preposition) vs **à**, "ou" (or) vs **où** (where)
  - Past participles: "termine" → **terminé**, "supprime" → **supprimé**
- Sentence structure: French uses spaces before `:`, `!`, `?`, `;` (thin non-breaking space `\u202F` preferred)
- Use « guillemets » for quotes, not "English quotes"

### Dutch (nl)

- Preserve diacritics where applicable: ë, ï, é, ü (e.g. "geïnteresseerd", "één", "reëel")
- Use correct compound words (Dutch compounds are written as one word)

### Validation

After writing each locale file, re-read it and verify:

1. No unaccented French words that require accents
2. No English words left untranslated
3. Interpolation placeholders (`{name}`, `{count}`) are preserved exactly
4. Pluralization keys match the locale's plural rules

## Step 5: Component Integration

1. Replace hardcoded strings with `useTranslations()` calls
2. Handle pluralization and interpolation
3. Add locale-aware date/number formatting
4. Update forms and validation messages
5. Test language switching

## Step 6: Content Migration (Conditional)

**Only if CMS or MDX content exists.**

1. Add locale-specific content directories
2. Migrate MDX content to locale-aware structure
3. Set up locale-aware content fetching

## Verification

- [ ] App builds without errors (`npx tsc --noEmit`)
- [ ] All 3 locales load correctly (`/en`, `/fr`, `/nl`)
- [ ] Language switcher navigates to the correct locale variant of the current page
- [ ] No untranslated strings visible in any locale
- [ ] French text has all required diacritics (spot-check 5 strings)
- [ ] Interpolation placeholders render correctly (not literal `{name}`)

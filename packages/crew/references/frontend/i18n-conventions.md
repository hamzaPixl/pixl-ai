# i18n Conventions

Shared conventions for multi-language Next.js applications (EN/FR/NL).

## Translation Key Naming

Use `section.component.element` hierarchy:

```
hero.headline          # Section-level
hero.cta1              # Element within section
nav.home               # Navigation items
contactForm.submit     # Form elements
footer.footerLinks.home # Nested group
blogPage.readMore      # Page-specific
common.learnMore       # Shared across pages
```

Rules:
- camelCase for all keys
- Group by UI section, not by page
- `common.*` for strings used in 3+ places
- Keep nesting max 3 levels deep

## File Structure

Two supported patterns:

### TypeScript exports (studio default)
```
lib/translations/
├── en.ts    # Source of truth
├── fr.ts
└── nl.ts
```

### JSON messages (next-intl)
```
messages/
├── en.json
├── fr.json
└── nl.json
```

## Locale Routing

```
/en/...    # English (default)
/fr/...    # French
/nl/...    # Dutch
```

Middleware detects `Accept-Language` header and redirects. Default locale can optionally omit the prefix (`/about` → `/en/about`).

## French (fr) Rules

### Diacritics — mandatory, never omit

All French accents must be present: é è ê ë à â ç ù û ô î ï œ æ

Common mistakes:
| Wrong | Correct |
|-------|---------|
| evenement | **événement** |
| parametre | **paramètre** |
| creer | **créer** |
| deja | **déjà** |
| a (preposition) | **à** |
| ou (where) | **où** |
| termine | **terminé** |
| supprime | **supprimé** |
| regle | **règle** |
| systeme | **système** |

### Punctuation
- Space before `:` `!` `?` `;` (use thin non-breaking space `\u202F`)
- Use « guillemets » for quotes, not "English quotes"

### Formality
- Use formal "vous" (not "tu") in all UI text
- Exception: apps explicitly targeting young/casual audiences

## Dutch (nl) Rules

### Diacritics
Preserve where required: ë, ï, é, ü
- geïnteresseerd, één, reëel, café

### Compound words
Dutch compounds are written as one word:
- ~~klanten service~~ → **klantenservice**
- ~~project beheer~~ → **projectbeheer**

### Tone
- Use informal "je/jij" (not "u") unless targeting formal B2B

## Pluralization

### English
Two forms: `one` and `other`.
```json
{ "item": "{count, plural, one {# item} other {# items}}" }
```

### French
Two forms: `one` (0 and 1) and `other`.
Note: French treats 0 as singular (`0 élément`).

### Dutch
Two forms: `one` and `other`.
Same as English.

## Date & Number Formatting

| | English | French | Dutch |
|--|---------|--------|-------|
| Date | Jan 15, 2026 | 15 janv. 2026 | 15 jan. 2026 |
| Number | 1,234.56 | 1 234,56 | 1.234,56 |
| Currency | $1,234 | 1 234 € | € 1.234 |

Use `Intl.DateTimeFormat` and `Intl.NumberFormat` with the active locale — never format manually.

## Key Ordering

All locale files must match the key order of `en.ts` exactly. This makes diffing across locales trivial and prevents merge conflicts.

## Validation Checklist

After writing each locale file:
1. No unaccented French words that require accents
2. No English words left untranslated
3. Interpolation placeholders (`{name}`, `{count}`) preserved exactly
4. Pluralization keys match the locale's plural rules
5. Key count matches `en.ts` — no missing or extra keys

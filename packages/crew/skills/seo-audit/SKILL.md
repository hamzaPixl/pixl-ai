---
name: seo-audit
description: "Comprehensive SEO audit and auto-fix for any business website. Use when asked to audit SEO, improve search rankings, fix meta tags, add structured data, generate sitemaps, check OG tags, or optimize a site for search engines. Supports multi-language/i18n sites. Works across business types: SaaS, e-commerce, agency, consulting, local business, blog, portfolio."
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
argument-hint: "<optional: specific page or directory to audit, or business type hint>"
---

## Overview

Full SEO audit pipeline: discover, audit, score, fix, validate. Detects business type from site content and tailors structured data accordingly. Handles multi-language sites with per-locale metadata and hreflang.

## Required References

Before starting, read these files for lookup tables, scoring rules, code templates, and validation checklists:
- `references/frontend/seo-reference.md` — structured data schemas, JSON-LD templates, OG locale codes, Next.js metadata patterns
- `references/frontend/seo-checklist.md` — scoring deductions, validation checklist (40+ items), auto-fix code templates, business type mapping

## Step 1: Discovery

1. **Framework detection**: Check for `next.config.*`, `package.json` (Next.js, Astro, Remix, plain React, HTML). Detect App Router vs Pages Router if Next.js.
2. **i18n detection**: Check `next.config.*` for `i18n` config or `next-intl`/`next-i18next`/`@formatjs`. Check for `[locale]` segment, `messages/`/`locales/`/`translations/` dirs. List all detected locales.
3. **Page inventory**: Glob for page files by framework convention. For i18n sites, map each route x locale.
4. **Existing SEO infrastructure**: Grep for `metadata|generateMetadata|Head|next-seo|next/head`. Check for sitemap, robots.txt, manifest, existing JSON-LD, OG image generation routes.
5. **Business type detection**: Scan headings, hero text, about pages. Refer to `references/frontend/seo-checklist.md` for the keyword-to-business-type mapping table.

Output: Page inventory (with locale matrix if i18n), framework info, existing SEO setup, detected business type.

## Step 2: Technical SEO Audit

Audit every page. For i18n sites, audit every page x locale combination.

### 2a: Meta Tags (per page, per locale)
- `<title>` exists (50-60 chars), includes primary keyword, translated per locale
- `<meta name="description">` exists (150-160 chars), includes CTA, translated per locale
- `<meta name="viewport">` set correctly
- `<link rel="canonical">` set, points to correct locale URL
- No duplicate titles/descriptions across pages within same locale
- Title template uses site name suffix

### 2b: Open Graph & Social (per page, per locale)
- `og:title`, `og:description`, `og:image`, `og:url`, `og:type` present
- `og:image` at least 1200x630px (check file exists)
- `og:locale` and `og:locale:alternate` set correctly per language
- `twitter:card`, `twitter:title`, `twitter:description`, `twitter:image` present
- `og:site_name` set; OG descriptions translated per locale

### 2c: i18n / Hreflang (skip if single-language)
- `hreflang` alternates for each locale on every page
- `hreflang="x-default"` points to fallback locale
- Locale-specific canonical URLs
- `alternates.languages` set in Next.js metadata
- Sitemap includes locale variants with `xhtml:link` alternates

### 2d: Structured Data / JSON-LD
- At least one schema per page type matching detected business type. Refer to `references/frontend/seo-checklist.md` for the page-type-to-schema mapping table.
- Validate schemas at https://validator.schema.org

### 2e: Infrastructure Files
- `sitemap.xml`/`.ts` exists, includes all public pages (all locales for i18n)
- `robots.txt`/`.ts` exists with correct rules, references sitemap
- `manifest.json`/`site.webmanifest` exists
- Favicon set (`favicon.ico` + multiple sizes)

### 2f: Performance & Crawlability
- Images use `next/image` or have `loading="lazy"` + explicit dimensions
- No render-blocking resources in `<head>`
- Fonts preloaded or using `next/font`
- No orphan pages; URL structure: lowercase, hyphen-separated, max 3 levels

## Step 3: On-Page SEO Audit

For each page (per locale):
- Exactly one `<h1>` with primary keyword; sequential heading order
- Primary keyword in first 100 words
- Internal links (minimum 2 per content page)
- All images have descriptive `alt` text (translated per locale)
- Content length: blog 800+, product 300+, landing 500+ words
- CTA links are descriptive (not "click here")
- Navigation includes key pages; footer has secondary nav; no broken internal links
- Language switcher links to correct locale variant (not homepage)

## Step 4: Scoring

Generate a scorecard per category (Meta Tags, Open Graph, Structured Data, i18n, Infrastructure, On-Page) with X/100 scores and issue counts.

Refer to `references/frontend/seo-checklist.md` for the scoring deductions table and severity definitions.

## Step 5: Auto-Fix

Apply fixes in priority order. For each fix, explain what changed and why.

1. **Metadata**: Add/fix `metadata` or `generateMetadata` exports on all pages
2. **Structured Data**: Create reusable `JsonLd` component, add schemas per page type
3. **Sitemap**: Create `app/sitemap.ts` with all pages (including locale variants for i18n)
4. **Robots.txt**: Create `app/robots.ts` with correct rules
5. **Image Alt Texts**: Infer from context; use translation keys for i18n
6. **Heading Fixes**: Add missing `<h1>`, demote duplicate `<h1>` to `<h2>`, fix skipped levels
7. **SEO Translation Keys**: Create missing locale files, flag untranslated values

Refer to `references/frontend/seo-checklist.md` for auto-fix code templates.

## Step 6: Validation

Run through the full validation checklist in `references/frontend/seo-checklist.md` (META-01 through OP-04). Mark pass/fail for every item. Output the final report table with before/after scores. If any critical checks fail, list specific files and lines needing manual attention.

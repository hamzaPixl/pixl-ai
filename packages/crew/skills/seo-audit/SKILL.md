---
name: seo-audit
description: "Comprehensive SEO audit and auto-fix for any business website. Use when asked to audit SEO, improve search rankings, fix meta tags, add structured data, generate sitemaps, check OG tags, or optimize a site for search engines. Supports multi-language/i18n sites. Works across business types: SaaS, e-commerce, agency, consulting, local business, blog, portfolio."
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
argument-hint: "<optional: specific page or directory to audit, or business type hint>"
---

## Overview

Full SEO audit pipeline: discover → audit → score → fix → validate. Detects the business type from site content and tailors structured data (JSON-LD) schemas accordingly. Handles multi-language sites with per-locale metadata and hreflang. Outputs both a prioritized report AND applies auto-fixes to the codebase.

## Required References

Before starting, read `references/frontend/seo-reference.md` for structured data schemas, meta tag patterns, and business-type mappings.

## Step 1: Discovery

1. **Framework detection**:
   - Check for `next.config.*`, `package.json` (Next.js, Astro, Remix, plain React, HTML)
   - Detect App Router vs Pages Router if Next.js
2. **i18n detection**:
   - Check `next.config.*` for `i18n` config or `next-intl` / `next-i18next` / `@formatjs`
   - Check for `[locale]` dynamic segment in App Router
   - Check for `messages/`, `locales/`, `translations/` directories
   - List all detected locales (e.g., `en`, `fr`, `nl`, `de`)
3. **Page inventory**:
   - Next.js App Router: `glob app/**/page.{tsx,jsx,ts,js}` and `app/**/layout.{tsx,jsx,ts,js}`
   - Next.js Pages Router: `glob pages/**/*.{tsx,jsx,ts,js}`
   - Static: `glob **/*.html`
   - For i18n sites: map each route × locale combination
4. **Existing SEO infrastructure**:
   - `grep -r "metadata|generateMetadata|Head|next-seo|next/head"` across the project
   - Check for existing `sitemap.xml`, `sitemap.ts`, `robots.txt`, `robots.ts`, `manifest.json`
   - Check for existing structured data (`application/ld+json`)
   - Check for `opengraph-image.tsx` / `twitter-image.tsx` (Next.js image generation)
5. **Business type detection** (scan headings, hero text, about pages):
   - **SaaS**: pricing, features, signup, dashboard, API
   - **E-commerce**: products, cart, checkout, shop, catalog
   - **Agency**: services, portfolio, case studies, clients, work
   - **Consulting**: expertise, advisory, engagement, methodology
   - **Local business**: location, hours, directions, contact, map
   - **Blog**: posts, articles, categories, tags, author
   - **Portfolio**: projects, work, gallery, showcase
   - **Organization**: team, mission, about us, careers

Output: Page inventory (with locale matrix if i18n), framework info, existing SEO setup, detected business type.

## Step 2: Technical SEO Audit

Audit every page. For i18n sites, audit every page × locale combination.

### 2a: Meta Tags (per page, per locale)

- [ ] `<title>` exists, 50-60 chars, includes primary keyword, **translated per locale**
- [ ] `<meta name="description">` exists, 150-160 chars, includes CTA, **translated per locale**
- [ ] `<meta name="viewport">` is set correctly
- [ ] `<link rel="canonical">` is set — points to the correct locale URL
- [ ] No duplicate titles or descriptions across pages (within same locale)
- [ ] Title template uses site name suffix (e.g., `%s | Site Name` or via `metadata.title.template`)

### 2b: Open Graph & Social (per page, per locale)

- [ ] `og:title`, `og:description`, `og:image`, `og:url`, `og:type` present
- [ ] `og:image` is at least 1200×630px (check if referenced image file exists)
- [ ] `og:locale` is set correctly for each language (e.g., `en_US`, `fr_FR`, `nl_BE`)
- [ ] `og:locale:alternate` lists other available locales
- [ ] `twitter:card`, `twitter:title`, `twitter:description`, `twitter:image` present
- [ ] `og:site_name` is set
- [ ] OG descriptions are translated per locale (not hardcoded in one language)

### 2c: i18n / Hreflang (skip if single-language)

- [ ] `<link rel="alternate" hreflang="xx" href="...">` for each locale on every page
- [ ] `hreflang="x-default"` points to the default/fallback locale
- [ ] Canonical URLs are locale-specific (e.g., `/en/about`, `/fr/about`)
- [ ] `alternates.languages` is set in Next.js metadata for each locale
- [ ] Sitemap includes all locale variants with `xhtml:link` alternates
- [ ] No mixed-language content (page in locale X should not have untranslated blocks)

### 2d: Structured Data / JSON-LD (per page type)

- [ ] At least one schema per page type, matching the detected business type:

| Page Type    | Schema(s)                                                                 |
| ------------ | ------------------------------------------------------------------------- |
| Homepage     | `WebSite` + `Organization` (or `LocalBusiness`, `SoftwareApplication`)    |
| Product page | `Product` with `offers`, `aggregateRating`                                |
| Blog post    | `Article` or `BlogPosting` with `author`, `datePublished`, `dateModified` |
| Blog listing | `CollectionPage` or `Blog`                                                |
| Service page | `Service` or `ProfessionalService`                                        |
| Pricing page | `Product` or `SoftwareApplication` with `offers`                          |
| FAQ page     | `FAQPage` with `mainEntity` questions                                     |
| Contact page | `ContactPoint` with phone/email                                           |
| About page   | `AboutPage` + `Organization`                                              |
| Team page    | `Organization` with `member` list                                         |
| Case study   | `Article` with `about`                                                    |

- [ ] `WebSite` schema on homepage includes `SearchAction` (if site has search)
- [ ] `BreadcrumbList` on all inner pages
- [ ] `@context` is `https://schema.org`
- [ ] No validation errors (test schemas at https://validator.schema.org)
- [ ] For i18n: `inLanguage` field set correctly per locale

### 2e: Infrastructure Files

- [ ] `sitemap.xml` (or `sitemap.ts`) exists and includes ALL public pages
- [ ] For i18n: sitemap includes all locale variants with `alternates`
- [ ] `robots.txt` (or `robots.ts`) exists with correct `Allow`/`Disallow`
- [ ] `robots.txt` references sitemap URL
- [ ] `manifest.json` / `site.webmanifest` exists
- [ ] Favicon set (`favicon.ico` + `icon.tsx` or multiple sizes)

### 2f: Performance & Crawlability

- [ ] Images use `next/image` or have `loading="lazy"` + explicit `width`/`height`
- [ ] No render-blocking resources in `<head>`
- [ ] Fonts preloaded or using `next/font`
- [ ] No orphan pages (pages not linked from navigation or other pages)
- [ ] URL structure: lowercase, hyphen-separated, max 3 levels deep

## Step 3: On-Page SEO Audit

For each page (per locale):

### 3a: Heading Hierarchy

- [ ] Exactly one `<h1>` per page
- [ ] `<h1>` contains primary keyword for that page/locale
- [ ] Heading order is sequential (no skipping h1→h3)
- [ ] Subheadings use relevant secondary keywords

### 3b: Content Signals

- [ ] Primary keyword appears in first 100 words
- [ ] Internal links to other pages (minimum 2 per content page)
- [ ] All images have descriptive `alt` text (translated per locale)
- [ ] Content length appropriate: blog 800+, product 300+, landing 500+ words
- [ ] CTA links are descriptive (not "click here")

### 3c: Link Structure

- [ ] Navigation includes all key pages
- [ ] Footer has secondary navigation
- [ ] No broken internal links (href targets exist)
- [ ] Language switcher links to correct locale variant of current page (not homepage)

## Step 4: Scoring

Generate a scorecard:

| Category            | Score     | Issues                |
| ------------------- | --------- | --------------------- |
| Meta Tags           | X/100     | N critical, N warning |
| Open Graph / Social | X/100     | N critical, N warning |
| Structured Data     | X/100     | N critical, N warning |
| i18n / Hreflang     | X/100     | N critical, N warning |
| Infrastructure      | X/100     | N critical, N warning |
| On-Page SEO         | X/100     | N critical, N warning |
| **Overall**         | **X/100** | **N total issues**    |

Scoring deductions:

- Missing `<title>` or `<meta description>`: **-15** per page
- Missing canonical: **-10** per page
- Missing OG tags: **-5** per page
- Missing structured data: **-10** per page type
- No sitemap: **-20**
- No robots.txt: **-10**
- Missing hreflang (i18n site): **-10** per page
- Heading hierarchy issues: **-5** per page
- Missing image alt: **-3** per image
- Missing internal links: **-5** per page

Severity:

- **Critical**: Missing titles, no sitemap, no structured data, broken links, missing hreflang on i18n site
- **Warning**: Missing OG images, heading issues, thin content, missing alts, untranslated OG tags
- **Info**: URL suggestions, additional schema opportunities, performance hints

## Step 5: Auto-Fix

Apply fixes in priority order. For each fix, explain what changed and why.

### 5a: Metadata

Add/fix `metadata` exports on all pages. For i18n sites using `generateMetadata`:

```tsx
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "seo" });
  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://example.com";
  const url = `${baseUrl}/${locale}/page-slug`;

  return {
    title: t("page.title"),
    description: t("page.description"),
    alternates: {
      canonical: url,
      languages: {
        en: `${baseUrl}/en/page-slug`,
        fr: `${baseUrl}/fr/page-slug`,
        nl: `${baseUrl}/nl/page-slug`,
      },
    },
    openGraph: {
      title: t("page.title"),
      description: t("page.description"),
      url,
      siteName: t("site.name"),
      locale: locale,
      type: "website",
      images: [
        {
          url: `${baseUrl}/og/page.png`,
          width: 1200,
          height: 630,
          alt: t("page.ogAlt"),
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: t("page.title"),
      description: t("page.description"),
      images: [`${baseUrl}/og/page.png`],
    },
  };
}
```

For non-i18n, use static `metadata` export with the same fields.

### 5b: Structured Data / JSON-LD

Create a reusable component:

```tsx
// components/structured-data.tsx
export function JsonLd({ data }: { data: Record<string, unknown> }) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}
```

Add schemas per page type based on detected business type. See reference doc for full schema templates.

For i18n: set `"inLanguage": locale` in each schema.

### 5c: Sitemap

Create `app/sitemap.ts` with all pages. For i18n sites, include all locale variants:

```ts
import type { MetadataRoute } from "next";

const locales = ["en", "fr", "nl"];
const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://example.com";

export default function sitemap(): MetadataRoute.Sitemap {
  const pages = ["", "/about", "/services", "/contact", "/blog"];

  return pages.flatMap((page) =>
    locales.map((locale) => ({
      url: `${baseUrl}/${locale}${page}`,
      lastModified: new Date(),
      changeFrequency: "weekly" as const,
      priority: page === "" ? 1 : 0.8,
      alternates: {
        languages: Object.fromEntries(
          locales.map((l) => [l, `${baseUrl}/${l}${page}`]),
        ),
      },
    })),
  );
}
```

### 5d: Robots.txt

Create `app/robots.ts`:

```ts
import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://example.com";
  return {
    rules: [{ userAgent: "*", allow: "/", disallow: ["/api/", "/admin/"] }],
    sitemap: `${baseUrl}/sitemap.xml`,
  };
}
```

### 5e: Image Alt Texts

Scan `<img>` and `<Image>` tags. For missing `alt`:

- Infer from context (nearby heading, filename, parent component)
- For i18n: use translation keys instead of hardcoded strings

### 5f: Heading Fixes

- No `<h1>` → add one from page title/metadata
- Multiple `<h1>` → demote extras to `<h2>`
- Fix skipped heading levels

### 5g: SEO Translation Keys

For i18n sites, ensure SEO translation files exist for each locale:

```json
// messages/en/seo.json
{
  "home": {
    "title": "Company Name — Tagline",
    "description": "Compelling description with CTA.",
    "ogAlt": "Company Name hero image"
  },
  "about": {
    "title": "About Us — Company Name",
    "description": "Learn about our mission...",
    "ogAlt": "Our team"
  }
}
```

Create missing translation files and flag untranslated values.

## Step 6: Validation Checklist

After all fixes are applied, verify each item. **Mark pass/fail for every item. Do NOT skip any.**

### Technical Validation

- [ ] **META-01**: Every page has a unique `<title>` (50-60 chars)
- [ ] **META-02**: Every page has a unique `<meta description>` (150-160 chars)
- [ ] **META-03**: Every page has `<link rel="canonical">`
- [ ] **META-04**: Root layout has `metadata.title.template` or equivalent

### Open Graph Validation

- [ ] **OG-01**: Every page has `og:title`, `og:description`, `og:image`, `og:url`, `og:type`
- [ ] **OG-02**: `og:image` files exist (or generation route exists)
- [ ] **OG-03**: Every page has `twitter:card`, `twitter:title`, `twitter:description`
- [ ] **OG-04**: `og:site_name` is set in root layout

### Structured Data Validation

- [ ] **SD-01**: Homepage has `WebSite` + business-type schema (`Organization`/`LocalBusiness`/etc.)
- [ ] **SD-02**: Every content page type has appropriate schema (see Step 2d table)
- [ ] **SD-03**: All schemas have `@context: "https://schema.org"`
- [ ] **SD-04**: Blog posts have `author`, `datePublished`, `dateModified`
- [ ] **SD-05**: Inner pages have `BreadcrumbList`
- [ ] **SD-06**: `JsonLd` component exists and is reusable

### i18n Validation (skip if single-language)

- [ ] **I18N-01**: Every page has `hreflang` alternates for all locales
- [ ] **I18N-02**: `hreflang="x-default"` is set
- [ ] **I18N-03**: Canonical URLs are locale-specific
- [ ] **I18N-04**: `og:locale` and `og:locale:alternate` are set
- [ ] **I18N-05**: SEO translation keys exist for all locales
- [ ] **I18N-06**: No hardcoded strings in metadata (all use translation functions)
- [ ] **I18N-07**: Sitemap includes all locale variants with `alternates`

### Infrastructure Validation

- [ ] **INF-01**: `sitemap.xml` (or `.ts`) exists and lists all public pages
- [ ] **INF-02**: `robots.txt` (or `.ts`) exists and references sitemap
- [ ] **INF-03**: Favicon exists (`favicon.ico` or `icon.tsx`)
- [ ] **INF-04**: `NEXT_PUBLIC_SITE_URL` is used (not hardcoded URLs)

### On-Page Validation

- [ ] **OP-01**: Every page has exactly one `<h1>`
- [ ] **OP-02**: Heading hierarchy is sequential (no skipped levels)
- [ ] **OP-03**: All images have descriptive `alt` text
- [ ] **OP-04**: Content pages have internal links (minimum 2)

### Final Report

Output the validation results as a table:

```
CHECK       STATUS   NOTES
META-01     ✅/❌    [details]
META-02     ✅/❌    [details]
...
─────────────────────────────
PASSED: X/Y checks
SCORE:  X/100 (before) → X/100 (after)
```

If any critical checks fail, list the specific files and lines that need manual attention.

# SEO Audit Checklist — Scoring, Validation & Auto-Fix Templates

Companion to `skills/seo-audit/SKILL.md` (workflow) and `references/frontend/seo-reference.md` (structured data schemas).

## Structured Data Schema by Page Type

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

Additional rules:
- `WebSite` schema on homepage includes `SearchAction` (if site has search)
- `BreadcrumbList` on all inner pages
- `@context` is `https://schema.org`
- For i18n: `inLanguage` field set correctly per locale

## Business Type Detection Keywords

| Business Type  | Indicator Keywords                                         |
| -------------- | ---------------------------------------------------------- |
| SaaS           | pricing, features, signup, dashboard, API                  |
| E-commerce     | products, cart, checkout, shop, catalog                    |
| Agency         | services, portfolio, case studies, clients, work           |
| Consulting     | expertise, advisory, engagement, methodology               |
| Local Business | location, hours, directions, contact, map                  |
| Blog           | posts, articles, categories, tags, author                  |
| Portfolio      | projects, work, gallery, showcase                          |
| Organization   | team, mission, about us, careers                           |

## Scoring Deductions

| Issue                            | Deduction |
| -------------------------------- | --------- |
| Missing `<title>` or `<meta description>` | **-15** per page |
| Missing canonical                | **-10** per page |
| Missing OG tags                  | **-5** per page  |
| Missing structured data          | **-10** per page type |
| No sitemap                       | **-20**          |
| No robots.txt                    | **-10**          |
| Missing hreflang (i18n site)     | **-10** per page |
| Heading hierarchy issues         | **-5** per page  |
| Missing image alt                | **-3** per image |
| Missing internal links           | **-5** per page  |

### Severity Levels

- **Critical**: Missing titles, no sitemap, no structured data, broken links, missing hreflang on i18n site
- **Warning**: Missing OG images, heading issues, thin content, missing alts, untranslated OG tags
- **Info**: URL suggestions, additional schema opportunities, performance hints

## Validation Checklist

After all fixes are applied, verify each item. Mark pass/fail for every item. Do NOT skip any.

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
- [ ] **SD-02**: Every content page type has appropriate schema (see page type table above)
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

### Final Report Format

```
CHECK       STATUS   NOTES
META-01     pass/fail    [details]
META-02     pass/fail    [details]
...
---
PASSED: X/Y checks
SCORE:  X/100 (before) -> X/100 (after)
```

If any critical checks fail, list the specific files and lines that need manual attention.

## Auto-Fix Code Templates

### Metadata (i18n with generateMetadata)

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

### Structured Data Component

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

Add schemas per page type based on detected business type. See `references/frontend/seo-reference.md` for full JSON-LD templates.

For i18n: set `"inLanguage": locale` in each schema.

### Sitemap (i18n)

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

### Robots.txt

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

### SEO Translation Keys

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

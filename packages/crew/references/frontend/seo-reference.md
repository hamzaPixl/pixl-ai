# SEO Reference — Structured Data Schemas & Patterns

## Business Type → Schema Mapping

| Business Type  | Homepage Schema                        | Additional Schemas                               |
| -------------- | -------------------------------------- | ------------------------------------------------ |
| SaaS           | `Organization` + `SoftwareApplication` | `Product` (pricing), `FAQPage`, `Article` (blog) |
| E-commerce     | `Organization` + `WebSite`             | `Product`, `BreadcrumbList`, `CollectionPage`    |
| Agency         | `Organization` + `ProfessionalService` | `Service`, `Article` (case studies)              |
| Consulting     | `Organization` + `ProfessionalService` | `Service`, `AboutPage`                           |
| Local Business | `LocalBusiness`                        | `ContactPoint`, `FAQPage`, `Service`             |
| Blog           | `Organization` + `Blog`                | `Article`/`BlogPosting`, `Person` (author)       |
| Portfolio      | `Organization` + `ProfilePage`         | `CreativeWork`, `Article`                        |

## JSON-LD Templates

### Organization (default for most business sites)

```json
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "Company Name",
  "url": "https://example.com",
  "logo": "https://example.com/logo.png",
  "description": "What the company does",
  "sameAs": [
    "https://twitter.com/company",
    "https://linkedin.com/company/company",
    "https://github.com/company"
  ],
  "contactPoint": {
    "@type": "ContactPoint",
    "email": "hello@example.com",
    "contactType": "customer service"
  }
}
```

### LocalBusiness

```json
{
  "@context": "https://schema.org",
  "@type": "LocalBusiness",
  "name": "Business Name",
  "url": "https://example.com",
  "image": "https://example.com/storefront.jpg",
  "telephone": "+1-555-000-0000",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "123 Main St",
    "addressLocality": "City",
    "addressRegion": "State",
    "postalCode": "12345",
    "addressCountry": "US"
  },
  "openingHoursSpecification": [
    {
      "@type": "OpeningHoursSpecification",
      "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
      "opens": "09:00",
      "closes": "17:00"
    }
  ],
  "geo": {
    "@type": "GeoCoordinates",
    "latitude": 0.0,
    "longitude": 0.0
  }
}
```

### WebSite (homepage — enables Google sitelinks search box)

```json
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "Site Name",
  "url": "https://example.com",
  "potentialAction": {
    "@type": "SearchAction",
    "target": "https://example.com/search?q={search_term_string}",
    "query-input": "required name=search_term_string"
  }
}
```

### Article / BlogPosting

```json
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "Article Title",
  "description": "Article summary",
  "image": "https://example.com/article-image.jpg",
  "author": {
    "@type": "Person",
    "name": "Author Name",
    "url": "https://example.com/team/author"
  },
  "publisher": {
    "@type": "Organization",
    "name": "Site Name",
    "logo": { "@type": "ImageObject", "url": "https://example.com/logo.png" }
  },
  "datePublished": "2025-01-01",
  "dateModified": "2025-01-15",
  "mainEntityOfPage": "https://example.com/blog/article-slug",
  "inLanguage": "en"
}
```

### Product (SaaS pricing or e-commerce)

```json
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Product Name",
  "description": "Product description",
  "image": "https://example.com/product.jpg",
  "brand": { "@type": "Brand", "name": "Brand Name" },
  "offers": {
    "@type": "AggregateOffer",
    "lowPrice": "29",
    "highPrice": "299",
    "priceCurrency": "USD",
    "offerCount": "3",
    "availability": "https://schema.org/InStock"
  }
}
```

### SoftwareApplication (SaaS)

```json
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "App Name",
  "applicationCategory": "BusinessApplication",
  "operatingSystem": "Web",
  "offers": {
    "@type": "Offer",
    "price": "29",
    "priceCurrency": "USD"
  }
}
```

### Service / ProfessionalService

```json
{
  "@context": "https://schema.org",
  "@type": "ProfessionalService",
  "name": "Service Name",
  "description": "What the service provides",
  "provider": {
    "@type": "Organization",
    "name": "Company Name"
  },
  "areaServed": "Worldwide",
  "serviceType": "Consulting"
}
```

### FAQPage

```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "Question text?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Answer text."
      }
    }
  ]
}
```

### BreadcrumbList

```json
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    {
      "@type": "ListItem",
      "position": 1,
      "name": "Home",
      "item": "https://example.com"
    },
    {
      "@type": "ListItem",
      "position": 2,
      "name": "Blog",
      "item": "https://example.com/blog"
    },
    { "@type": "ListItem", "position": 3, "name": "Article Title" }
  ]
}
```

## OG Locale Codes

| Language            | og:locale |
| ------------------- | --------- |
| English (US)        | `en_US`   |
| English (UK)        | `en_GB`   |
| French              | `fr_FR`   |
| Dutch (Belgium)     | `nl_BE`   |
| Dutch (Netherlands) | `nl_NL`   |
| German              | `de_DE`   |
| Spanish             | `es_ES`   |
| Italian             | `it_IT`   |
| Portuguese          | `pt_BR`   |
| Japanese            | `ja_JP`   |
| Chinese             | `zh_CN`   |
| Korean              | `ko_KR`   |
| Arabic              | `ar_SA`   |

## Next.js Metadata Patterns

### Static metadata (single language)

```tsx
export const metadata: Metadata = {
  title: { default: "Site Name", template: "%s | Site Name" },
  description: "Site description",
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL || "https://example.com",
  ),
  openGraph: { siteName: "Site Name", type: "website", locale: "en_US" },
  twitter: { card: "summary_large_image" },
};
```

### Dynamic metadata (i18n)

```tsx
export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "seo" });
  return {
    title: t("page.title"),
    description: t("page.description"),
    alternates: {
      canonical: `/${locale}/page`,
      languages: { en: "/en/page", fr: "/fr/page", nl: "/nl/page" },
    },
    openGraph: { locale },
  };
}
```

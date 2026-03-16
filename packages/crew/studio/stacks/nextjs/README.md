# Studio Templates

Template files used by the scaffold skill to generate new website projects. The scaffold copies files from `studio/` into a new project directory, replacing `{{TOKEN}}` placeholders in `.tmpl` files with project-specific values.

---

## Quickstart

```bash
# 1. Copy the scaffold into a new project
cp -r studio/ my-project/

# 2. Replace tokens in all .tmpl files (the scaffold skill does this automatically)
#    Then rename .tmpl files (e.g. package.json.tmpl → package.json)

# 3. Install dependencies
cd my-project && npm install

# 4. Build to verify
npm run build
```

---

## Pages produced

The Build skill should create the following pages. The scaffold provides layout, shared components, hooks, types, and API routes — the Build skill creates each page's `page.tsx` and `page-client.tsx`.

| Route | Description |
|-------|-------------|
| `/` | Homepage — hero, stats, services overview, testimonials, CTA |
| `/about` | About — team, mission, values, process |
| `/services` | Services listing — grid of all services |
| `/services/[slug]` | Service detail — problem, methodology, deliverables, benefits |
| `/blog` | Blog listing — post cards with tag filtering |
| `/blog/[slug]` | Blog post detail — MDX content with post header |
| `/contact` | Contact form — name, email, phone, company, service, message |
| `/legal` | Legal notice |
| `/privacy` | Privacy policy |
| `/faq` | FAQ — accordion with common questions |

---

## Components inventory

### Shared components (`components/`)

| Component | Description |
|-----------|-------------|
| `shared-layout.tsx` | Main layout wrapper with header, navigation, and footer |
| `page-hero.tsx` | Animated hero section with label, headline, description |
| `logo.tsx` | SVG logo component |
| `language-switcher.tsx` | Locale dropdown (FR/NL/EN) |
| `theme-toggle.tsx` | Light/Dark/System theme toggle |
| `theme-provider.tsx` | Next-themes provider |
| `cookie-banner.tsx` | GDPR cookie consent banner |
| `analytics.tsx` | GA4 analytics with consent gating |
| `scroll-progress.tsx` | Reading progress bar |
| `wave-divider.tsx` | SVG wave section divider |
| `structured-data.tsx` | Schema.org Organization JSON-LD |
| `breadcrumb-schema.tsx` | Schema.org BreadcrumbList JSON-LD |
| `contact-form.tsx` | Contact form with validation |

### Blog components (`components/blog/`)

| Component | Description |
|-----------|-------------|
| `post-card.tsx` | Blog post card — title, description, date, tags, read time, link |
| `post-header.tsx` | Blog post detail header — title, author, date, tags, back link |
| `mdx-components.tsx` | MDX component overrides for styled headings, links, code, etc. |

### UI primitives (`components/ui/`)

| Component | Description |
|-----------|-------------|
| `accordion.tsx` | Radix UI Accordion |
| `badge.tsx` | Badge with variants |
| `button.tsx` | Button with variants and sizes |
| `card.tsx` | Card with header, title, description, content, footer |
| `dialog.tsx` | Radix UI Dialog (modal) |
| `dropdown-menu.tsx` | Radix UI Dropdown Menu |
| `input.tsx` | Text input |
| `label.tsx` | Form label |
| `separator.tsx` | Radix UI Separator |
| `sheet.tsx` | Radix UI Sheet (side drawer) |
| `tabs.tsx` | Radix UI Tabs |
| `textarea.tsx` | Textarea input |

---

## Hooks

| Hook | File | Description |
|------|------|-------------|
| `useTranslate` | `hooks/useTranslate.ts` | Returns `t(key)`, `tArray(key)`, `tRaw<T>(key)`, `currentLanguage`. Falls back to FR. |
| `useCounter` | `hooks/useCounter.ts` | Animated counter with IntersectionObserver start-on-view. Respects `prefers-reduced-motion`. Returns `{ count, ref, start }`. |
| `useLanguage` | `lib/language-context.tsx` | Language context provider and hook. Returns `{ currentLanguage, setLanguage }`. |

---

## Types (`lib/types/index.ts`)

| Type | Fields |
|------|--------|
| `PageSeoDTO` | title, description, keywords |
| `ServiceItem` | slug, icon, title, shortDescription, fullDescription, problem, methodology[], deliverables[], benefits[] |
| `TeamMember` | name, role, expertise, phone, linkedin, bio |
| `TestimonialItem` | name, role, company, rating, quote |
| `FAQItem` | question, answer |
| `ProcessStep` | number, title, description |
| `StatItem` | value, suffix, label |
| `BlogPost` | slug, title, description, date, author, tags[], image?, readTime, content |

---

## Quality standards

- **No hardcoded strings** — All user-visible text must go through `useTranslate` with translation keys.
- **Accessibility** — All interactive elements have ARIA attributes. Images have alt text. Form inputs have labels.
- **Reduced motion** — Components respect `prefers-reduced-motion`. `useCounter` skips animation. CSS keyframes are suppressed via `globals.css`.
- **Contrast** — WCAG AA (4.5:1) minimum for all text. Muted foreground is tuned per light/dark mode.
- **Premium CSS** — Use the custom utility classes below instead of raw Tailwind for visual consistency.

---

## CSS utility classes (`globals.css`)

| Class | Purpose |
|-------|---------|
| `hero-gradient` | Radial/linear mesh gradient for hero sections |
| `card-hover` | Card with hover elevation and primary-tinted shadow |
| `glass` | Glassmorphism panel (light + dark variants) |
| `glass-strong` | Stronger glass effect for overlays |
| `nav-pill` | Floating navigation bar style |
| `cta-gradient` | Full primary→secondary gradient for CTA banners |
| `service-icon` | Icon wrapper with gradient background |
| `section-label` | Uppercase tracking label above section headings |
| `section-divider` | Subtle fading horizontal rule |
| `link-underline` | Animated underline on hover |
| `animate-fade-in-up` | Fade-in + slide-up keyframe animation |

---

## API routes

### `POST /api/contact`

Contact form handler with Resend email integration.

**Environment variables:**

| Variable | Required | Description |
|----------|----------|-------------|
| `RESEND_API_KEY` | No | Resend API key. If absent, submissions are logged to console only. |
| `EMAIL_FROM` | No | Sender address. Defaults to `{{PROJECT_NAME}} <noreply@{{PROJECT_SLUG}}.com>`. |
| `EMAIL_TO` | No | Recipient address. Defaults to `{{CONTACT_EMAIL}}`. |

**Responses:**

| Status | Description |
|--------|-------------|
| 200 | `{ success: true }` |
| 400 | Validation failed (Zod errors in `details`) |
| 429 | Rate limited (5 requests/min per IP) |
| 500 | Internal server error |

### `POST /api/checkout` (Stripe)

Creates a Stripe Checkout session. Conditional on `features.stripe`.

**Environment variables:**

| Variable | Required | Description |
|----------|----------|-------------|
| `STRIPE_SECRET_KEY` | Yes | Stripe secret key |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | Yes | Stripe publishable key (client-side) |
| `STRIPE_WEBHOOK_SECRET` | Yes | Stripe webhook signing secret |

**Request body:** `{ priceId: string, successUrl?: string, cancelUrl?: string }`

**Responses:**

| Status | Description |
|--------|-------------|
| 200 | `{ url: string }` — Stripe Checkout URL to redirect to |
| 400 | Validation failed |
| 429 | Rate limited (10 requests/min per IP) |
| 500 | Internal server error |

### `POST /api/webhook` (Stripe)

Stripe webhook handler for payment events. Verifies webhook signature and processes `checkout.session.completed` and `payment_intent.succeeded` events.

---

## Supabase integration

Client and server Supabase clients in `lib/supabase/`. Conditional on `features.supabase`.

| File | Description |
|------|-------------|
| `lib/supabase/client.ts` | Browser client using `createBrowserClient()` from `@supabase/ssr` |
| `lib/supabase/server.ts` | Server client using `createServerClient()` with cookie-based sessions |

**Environment variables:**

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Yes | Supabase anon/public key |

---

## PWA support

The scaffold includes a `site.webmanifest` with `display: "standalone"` for installable PWA support. Add icon files (`icon-192x192.png`, `icon-512x512.png`) to `public/` and reference the manifest in `layout.tsx` metadata.

---

## Blog system

### Setup

Blog posts are MDX files in `content/blog/`. The `lib/blog.ts` utility reads and parses them using `gray-matter`.

### Frontmatter fields

```yaml
---
title: "Post title"
description: "Short description"
date: "2025-01-15"
author: "Author Name"
tags: ["tag1", "tag2"]
image: "/images/blog/post.jpg"  # optional
---
```

### Components

- `PostCard` — Used on the blog listing page. Pass `readMoreLabel` and `readTimeLabel` from translations.
- `PostHeader` — Used on the blog detail page. Pass `backLabel`, `publishedLabel`, `byLabel`, `readTimeLabel` from translations.
- `getMDXComponents()` — Returns styled MDX component overrides for rendering post content.

---

## Directory structure

| Directory | Purpose |
|-----------|---------|
| `base/` | Root-level config files: package.json, tsconfig, tailwind, eslint, etc. |
| `app/` | Next.js App Router files: layout, pages, globals.css, sitemap, API routes (contact, checkout, webhook) |
| `lib/` | Shared utilities, config, i18n, analytics, schemas, types, translations, supabase, stripe |
| `components/` | Reusable UI components (shared-layout, nav, footer, blog, etc.) |
| `hooks/` | Custom React hooks (useTranslate, useCounter) |
| `content/` | Static content (blog posts in MDX) |
| `deploy/` | Deployment configs (netlify.toml) |
| `public/` | Static assets (favicon, logo, images) |

---

## Token reference

| Token | Example | Description |
|-------|---------|-------------|
| `{{PROJECT_NAME}}` | `CloudSync` | Human-readable project name |
| `{{PROJECT_SLUG}}` | `cloud-sync` | URL/package-safe slug |
| `{{PROJECT_DESCRIPTION}}` | `Cloud sync platform` | Short project description |
| `{{BASE_URL}}` | `https://cloudsync.dev` | Production base URL |
| `{{PRIMARY_COLOR_HSL}}` | `171 77% 64%` | Primary brand color in HSL (no commas) |
| `{{SECONDARY_COLOR_HSL}}` | `0 100% 67%` | Secondary/accent color in HSL (no commas) |
| `{{FONT_SANS}}` | `Inter` | Sans-serif Google Font name |
| `{{FONT_SERIF}}` | `Playfair Display` | Serif Google Font name |
| `{{CONTACT_EMAIL}}` | `hello@cloudsync.dev` | Public contact email |
| `{{CONTACT_PHONE}}` | `+1234567890` | Contact phone (international format) |
| `{{GA_ID}}` | `G-XXXXXXXXXX` | Google Analytics measurement ID |
| `{{DEFAULT_LOCALE}}` | `en` | Default locale code (en, fr, nl) |

## Naming conventions

- **`.tmpl` files** contain one or more `{{TOKEN}}` placeholders and are rendered at scaffold time.
- **Non-`.tmpl` files** are copied as-is with no processing.
- Output file names have the `.tmpl` suffix stripped (e.g. `package.json.tmpl` becomes `package.json`).

## Adding new templates

1. Place the file in the appropriate directory (`base/`, `app/`, `lib/`, etc.).
2. If the file needs project-specific values, add the `.tmpl` extension and use `{{TOKEN}}` placeholders.
3. **Update `manifest.yaml`** — add an entry to the `files` list with `source`, `target`, `template`, `tokens`, and optional `condition`. The scaffold reads only the manifest; files not listed there will be ignored.
4. Update this README if you introduce a new token.

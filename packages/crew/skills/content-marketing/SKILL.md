---
name: content-marketing
description: "Content strategy and hands-on copywriting for business websites: audience analysis, content calendar, SEO-optimized copy, blog plans. Use for strategic content planning or writing individual pieces with human review. For batch-generating content across many pages automatically, use /content-pipeline instead."
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, WebSearch
argument-hint: "<business type or specific content request, e.g. 'SaaS blog strategy' or 'rewrite homepage copy'>"
---

## Overview

Content marketing pipeline: discover → strategize → create → optimize → validate. Analyzes the business type, target audience, and existing content to produce conversion-optimized copy, blog content plans, and content calendars. All output is actionable — written directly into the codebase or delivered as ready-to-use content files.

## Step 1: Discovery

1. **Business analysis**:
   - Read the site's homepage, about page, and service/product pages
   - Identify: business type, value proposition, target audience, tone of voice
   - Detect existing brand language patterns (formal/casual, technical/approachable)
   - Check for existing blog posts, case studies, or content sections
2. **Content inventory**:
   - List all pages with text content
   - Identify thin pages (< 300 words)
   - Identify pages without clear CTA
   - Check for duplicate or near-duplicate content
3. **i18n check**:
   - Are there multiple locales?
   - Which locales have content gaps?
4. **Competitor signals** (if user provides competitors or business context):
   - Use WebSearch to research common content topics in the industry
   - Identify content gaps the site could fill

Output: Business profile, content inventory, identified gaps, audience persona.

## Step 2: Content Strategy

Based on discovery, produce a strategy document. Choose the relevant business archetype:

### SaaS Content Strategy

- **Top of funnel**: Problem-awareness blog posts, comparison guides, "how to" tutorials
- **Middle of funnel**: Feature deep-dives, integration guides, use case pages
- **Bottom of funnel**: Case studies, ROI calculators, pricing comparison, free trial CTA
- **Retention**: Changelog, product updates, best practices, advanced tutorials

### E-commerce Content Strategy

- **Product descriptions**: Benefit-led, sensory language, size/spec tables
- **Category pages**: Buying guides, "best X for Y" content
- **Blog**: Styling guides, seasonal content, gift guides, care instructions
- **Trust content**: Reviews integration, shipping/return policy pages, FAQ

### Agency Content Strategy

- **Case studies**: Problem → Solution → Results format with metrics
- **Service pages**: Pain-point led, process explanation, deliverables list
- **Blog**: Industry insights, methodology articles, behind-the-scenes
- **Trust content**: Client logos, testimonials, team bios, awards

### Consulting Content Strategy

- **Thought leadership**: White papers, industry analysis, opinion pieces
- **Service pages**: Expertise-led, methodology explanation, engagement models
- **Blog**: Frameworks, best practices, trend analysis
- **Trust content**: Credentials, speaking engagements, publications

### Local Business Content Strategy

- **Service pages**: Local keywords, service area pages, pricing
- **Blog**: Local guides, community events, seasonal tips
- **Trust content**: Google Reviews integration, before/after galleries, FAQ
- **Local SEO**: Google Business Profile content alignment

### Portfolio Content Strategy

- **Project pages**: Context → Process → Outcome with visuals
- **Blog**: Process breakdowns, tool reviews, industry commentary
- **About**: Personal story, skills, timeline

Output: Content strategy document with funnel mapping, topic clusters, and content types.

## Step 3: Content Creation

Based on the strategy, create or improve content. The user specifies which content to produce. Common tasks:

### 3a: Homepage Copy

Structure:

1. **Hero**: Headline (6-12 words, benefit-led) + subheadline (1-2 sentences, expanding on value) + CTA
2. **Social proof bar**: Logos, metrics, or testimonial snippet
3. **Problem statement**: What pain does the audience face?
4. **Solution section**: How the product/service solves it (3-4 feature blocks)
5. **How it works**: 3-step process or visual flow
6. **Testimonials/Case studies**: 2-3 with name, role, company, quote
7. **FAQ section**: 4-6 common objections addressed
8. **Final CTA**: Restate value prop + action button

Guidelines:

- Write for scanning: short paragraphs, bullet points, bold key phrases
- Front-load benefits, not features
- Use the audience's language (match their vocabulary)
- Every section should have a micro-CTA or lead to the next section

### 3b: Service/Product Pages

Structure:

1. **H1**: Service/product name with primary keyword
2. **Value proposition**: 1-2 sentences on the outcome
3. **Key benefits**: 3-5 benefit blocks with icons
4. **Detailed description**: 200-400 words, keyword-rich
5. **Process/How it works**: Step-by-step
6. **Pricing** (if applicable): Clear tiers or "contact us"
7. **FAQ**: 3-5 service-specific questions
8. **CTA**: Next step (book call, get quote, buy now)

### 3c: Blog Content Plan

Create a 12-week content calendar:

```
WEEK  TOPIC                           TYPE        FUNNEL    KEYWORD TARGET
1     [topic]                         how-to      TOFU      [keyword]
2     [topic]                         comparison  MOFU      [keyword]
3     [topic]                         case-study  BOFU      [keyword]
...
```

For each blog post, provide:

- Title (60 chars, includes primary keyword)
- Meta description (155 chars)
- H2 outline (5-8 subheadings)
- Target word count
- Internal links to existing pages
- CTA at the end

### 3d: Landing Page Copy

For campaign-specific landing pages:

1. **Headline**: Benefit + urgency or specificity
2. **Subheadline**: Expand on the promise
3. **Hero image/video**: Description of what to show
4. **3 benefit blocks**: Icon + heading + 1-2 sentences
5. **Social proof**: Testimonial or metric
6. **Objection handling**: 3 common concerns addressed
7. **CTA section**: Form or button with urgency element
8. **Trust signals**: Guarantees, certifications, security badges

### 3e: About Page Copy

Structure:

1. **Mission statement**: Why the company exists
2. **Story**: Origin, journey, milestones
3. **Values**: 3-5 core values with explanations
4. **Team**: Bios with personality (not just credentials)
5. **CTA**: Join us / work with us / contact

### 3f: Email/Newsletter Copy Templates

For content distribution:

- Welcome email sequence (3-5 emails)
- Blog notification template
- Monthly newsletter template
- Product update template

## Step 4: SEO Optimization

For all created/edited content:

1. **Keyword integration**:
   - Primary keyword in: title, H1, first 100 words, meta description, URL
   - Secondary keywords in: H2s, body text, image alts
   - No keyword stuffing (natural density 1-2%)
2. **Readability**:
   - Short paragraphs (2-4 sentences)
   - Subheadings every 200-300 words
   - Bullet points for lists
   - Active voice preferred
   - Reading level: Grade 8-10 (depends on audience)
3. **Internal linking**:
   - Link to 2-3 related pages per content piece
   - Use descriptive anchor text (not "click here")
   - Link to conversion pages where natural
4. **Meta optimization**:
   - Title: 50-60 chars, primary keyword + brand
   - Description: 150-160 chars, includes CTA verb
   - URL: lowercase, hyphenated, includes keyword

## Step 5: i18n Content (if multi-language site)

For each locale:

1. **Translation strategy**: Decide between translation vs. localization vs. transcreation
   - **Translation**: Direct translation (suitable for technical content)
   - **Localization**: Adapted for local culture, idioms, currency, date formats
   - **Transcreation**: Rewritten for local market (suitable for marketing copy, headlines, CTAs)
2. **Per-locale adaptation**:
   - Adjust CTAs for cultural norms (direct vs. indirect)
   - Use local social proof (testimonials from that market)
   - Adapt examples and case studies for relevance
   - Check number/date/currency formatting
3. **SEO per locale**:
   - Research local keywords (not just translated keywords)
   - Adapt meta descriptions for local search intent
   - Local structured data where applicable

## Step 6: Validation Checklist

After all content is created/edited, verify each item. **Mark pass/fail for every item. Do NOT skip any.**

### Copy Quality

- [ ] **CQ-01**: Every page has a clear, benefit-led headline
- [ ] **CQ-02**: Every page has at least one CTA (above the fold preferred)
- [ ] **CQ-03**: No pages with < 300 words of content (except utility pages)
- [ ] **CQ-04**: All copy uses active voice predominantly
- [ ] **CQ-05**: No jargon without explanation (unless technical audience)
- [ ] **CQ-06**: Social proof present on key conversion pages (home, pricing, services)
- [ ] **CQ-07**: FAQ section exists on service/product pages

### SEO Integration

- [ ] **SEO-01**: Primary keyword in title, H1, first 100 words, and meta description
- [ ] **SEO-02**: Secondary keywords in H2 subheadings
- [ ] **SEO-03**: Internal links present (minimum 2 per content page)
- [ ] **SEO-04**: Image alt texts are descriptive and keyword-relevant
- [ ] **SEO-05**: URLs are clean, lowercase, hyphenated, keyword-inclusive
- [ ] **SEO-06**: Meta descriptions include a CTA verb (discover, learn, get, try, start)

### Content Structure

- [ ] **CS-01**: Heading hierarchy is correct (H1 → H2 → H3, no skips)
- [ ] **CS-02**: Paragraphs are 2-4 sentences max
- [ ] **CS-03**: Lists/bullet points used for 3+ items
- [ ] **CS-04**: Content follows the funnel stage (TOFU=educational, MOFU=comparative, BOFU=conversion)

### Conversion Optimization

- [ ] **CO-01**: Homepage has hero CTA above the fold
- [ ] **CO-02**: Service/product pages end with a CTA
- [ ] **CO-03**: Blog posts have a CTA (related content, newsletter signup, or product link)
- [ ] **CO-04**: Pricing page has clear tier differentiation
- [ ] **CO-05**: Contact page has multiple channels (form + email + phone/social)

### i18n Content (skip if single-language)

- [ ] **I18N-01**: All marketing copy uses translation keys (no hardcoded strings)
- [ ] **I18N-02**: CTAs are localized (not just translated)
- [ ] **I18N-03**: Social proof is locale-relevant where possible
- [ ] **I18N-04**: Keywords are locally researched (not just translated)
- [ ] **I18N-05**: Date/number/currency formats match locale

### Final Report

Output the validation results:

```
CHECK       STATUS   NOTES
CQ-01       ✅/❌    [details]
CQ-02       ✅/❌    [details]
...
─────────────────────────────
PASSED: X/Y checks
CONTENT PIECES CREATED: N
PAGES IMPROVED: N
CONTENT GAPS REMAINING: [list]
```

List any items that need manual follow-up (e.g., "need real client testimonials for FR locale", "pricing needs to be confirmed by business owner").

---
name: blog
description: "Build a blog with MDX content, listing pages, RSS feed, and SEO. Uses the Next.js studio stack. Use when asked to create a blog, add a blog to an existing site, or build a content-driven site."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
argument-hint: "<blog description or content topics>"
disable-model-invocation: true
---

## Overview

Builds a blog using Next.js with MDX content, category/tag navigation, RSS feed, and SEO optimization. Scaffolds from the nextjs studio stack.

## Studio Stack

Scaffold from: `studio/stacks/nextjs/` (75 templates)

## Suggested Team

- **frontend-engineer** — Blog components, MDX setup, styling
- **qa-engineer** — Testing, SEO verification

## Process

### Phase 1: Setup

1. Scaffold from nextjs stack (or add to existing Next.js project)
2. Install MDX dependencies (`next-mdx-remote` or `velite`)
3. Create blog content directory structure
4. Define blog post metadata schema (title, date, author, tags, excerpt)

### Phase 2: Build

5. Create blog listing page with pagination
6. Create blog post template with MDX rendering
7. Add category and tag pages
8. Create author pages (if multi-author)
9. Add search functionality (optional)

### Phase 3: Content & SEO

10. Run `/content-pipeline` for initial blog posts
11. Add RSS feed (`/feed.xml`)
12. Add sitemap entries for all posts
13. Add Open Graph and Twitter Card metadata per post
14. Add JSON-LD structured data (Article schema)

### Phase 4: Polish

15. Responsive typography for reading experience
16. Code syntax highlighting for technical posts
17. Table of contents for long posts
18. Related posts section
19. Run `/self-review-fix-loop` for quality check

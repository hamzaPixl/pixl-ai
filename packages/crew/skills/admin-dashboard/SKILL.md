---
name: admin-dashboard
description: "Build an admin dashboard with data tables, forms, RBAC UI, and charts. Orchestrates Next.js scaffolding with backend API integration. Use when asked to create an admin panel, back-office, or management interface."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
argument-hint: "<dashboard scope and entities to manage>"
disable-model-invocation: true
---

## Overview

Builds an admin dashboard with data tables, forms, role-based access control UI, and optional charts/analytics. Uses Next.js with shadcn/ui for the frontend and integrates with a backend API.

## Suggested Team

- **architect** — Data model, page structure, RBAC design
- **frontend-engineer** — Data tables, forms, dashboard layout
- **backend-engineer** — API endpoints for CRUD and analytics
- **qa-engineer** — Testing, accessibility

## Process

### Phase 1: Discovery

1. Identify entities to manage (users, orders, products, etc.)
2. Define RBAC roles and what each can see/do
3. Determine dashboard metrics and charts needed
4. Plan navigation structure (sidebar, breadcrumbs)

### Phase 2: Scaffold

5. Scaffold from `studio/stacks/nextjs/` or existing Next.js project
6. Install shadcn/ui data table, form, dialog, and chart components
7. Create layout with sidebar navigation, header, and main content area

### Phase 3: Build

8. Build data table pages for each entity (list, filter, sort, paginate)
9. Build form pages (create, edit) with Zod validation
10. Build detail pages with related data
11. Add RBAC-aware navigation (hide/show based on role)
12. Add dashboard overview with metrics and charts

### Phase 4: Quality

13. Run `/self-review-fix-loop` for quality assurance
14. Run `/agent-browser` to verify critical admin flows on the running app
15. Test with different RBAC roles (admin, member, viewer)

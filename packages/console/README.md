# pixl-console

> React console for Pixl Platform — real-time session viewer, project dashboard, and billing management.

## Overview

pixl-console is a modern React SPA that provides a real-time interface for managing AI agent sessions, viewing project workflows, and handling billing. Built with React 19, TanStack Router, and shadcn/ui components.

## Features

- **Real-time session viewer** — SSE-powered live streaming of agent execution
- **Project dashboard** — Manage features, epics, roadmaps, and workflows
- **Billing & usage** — Plan display, usage progress bars, Stripe upgrade flow
- **35+ file-based routes** — TanStack Router with automatic code splitting
- **40+ components** — Built on shadcn/ui (Radix primitives) with Tailwind CSS
- **Dark mode** — Theme switching via `next-themes`
- **Data tables** — TanStack Table with sorting, filtering, pagination
- **Charts** — Recharts-powered analytics and metrics
- **Drag & drop** — dnd-kit for sortable interfaces

## Quick Start

```bash
# Install dependencies
make console-install
# or: cd packages/console && pnpm install

# Dev server (port 5173)
make console-dev

# Production build
make console-build
```

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | React 19 |
| Language | TypeScript 5.9 |
| Build | Vite 7 |
| Router | TanStack Router v1 (file-based) |
| Data fetching | TanStack Query v5 |
| Tables | TanStack Table v8 |
| State | Zustand v5 |
| UI | shadcn/ui + Radix UI |
| Styling | Tailwind CSS 3.4 |
| Charts | Recharts |
| Animations | Framer Motion |
| Code highlight | Shiki |
| E2E tests | Playwright |

## Testing

```bash
pnpm test:e2e            # Run Playwright tests
pnpm test:e2e:ui         # Interactive Playwright UI
pnpm test:e2e:install    # Install browser deps
```

## Structure

```
src/
├── routes/          # 35+ file-based TanStack routes
├── components/      # 40+ React components (shadcn/ui)
├── lib/             # API client, hooks, utilities
├── stores/          # Zustand state stores
└── types/           # TypeScript type definitions
```

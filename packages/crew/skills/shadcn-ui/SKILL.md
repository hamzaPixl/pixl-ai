---
name: shadcn-ui
description: "Install, compose, and theme shadcn/ui components and blocks using the CLI and registry. Use when asked to add UI components, build forms, create data tables, install blocks, or theme an interface with shadcn/ui."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, WebFetch
argument-hint: "<component or UI feature to build>"
---

## Overview

Install, compose, and theme shadcn/ui components. Supports interactive use, programmatic invocation, and orchestrated workflows. Uses the shadcn CLI for registry search, component docs, and installation.

## Prerequisites

- `components.json` must exist in the project root (Next.js with Tailwind CSS)
- `npx shadcn@latest` CLI available

## Step 1: Discovery

1. Read `components.json` to understand the project's shadcn configuration
2. Identify which components are already installed
3. Determine what new components are needed for the requested feature
4. Use the shadcn CLI to search the registry and browse available components/blocks
5. Check for custom registry or extended components

## Step 2: Search & Plan

1. Use the shadcn CLI to search for required components and read their docs
2. Identify component dependencies (e.g., Dialog needs Button)
3. Plan installation order (dependencies first)
4. Check for conflicts with existing components

## Step 2.5: Blocks & External Registry

Before installing primitives, check if a pre-built **block** covers the feature:
- **shadcn blocks:** login (01-05), dashboard (01-07), sidebar (01-16), charts, calendar — `npx shadcn@latest add <block> --yes`
- **Magic UI:** 150+ animated components — `npx shadcn@latest add "https://magicui.design/r/<name>" --yes`
- **Aceternity:** 100+ decorative components — copy from https://ui.aceternity.com

See `references/frontend/block-sources.md` for archetype affinity and section-to-block mappings.

## Step 3: Install

1. Install components using `npx shadcn@latest add <component>` (CLI is still the install mechanism)
2. Verify each component is added correctly
3. Check that imports resolve

## Step 4: Compose

1. Build the requested feature by composing installed components
2. Follow project's component file structure
3. Add proper TypeScript types and props
4. Ensure accessibility (keyboard nav, aria labels, focus management)

## Step 5: Theme (Conditional)

**Only if theme changes are requested.**

1. Update CSS custom properties in `globals.css`
2. Adjust component variants to match the design system
3. Add dark mode support if configured
4. Verify visual consistency across components

## Verification

- [ ] All installed components render without console errors
- [ ] `npx tsc --noEmit` passes (no type errors from new components)
- [ ] Keyboard navigation works (Tab, Enter, Escape) on interactive components
- [ ] Dark mode toggle works if configured
- [ ] Component imports resolve correctly in consuming files

---
name: react-doctor
description: "Run after making React changes to catch issues early. Use when reviewing code, finishing a feature, or fixing bugs in a React project. Checks for common anti-patterns, performance issues, accessibility gaps, and hook misuse."
allowed-tools: Read, Glob, Grep, Bash
argument-hint: "<optional: specific component or directory to check>"
---

## Overview

React health check that catches common issues after making changes. Scans for anti-patterns, performance problems, accessibility gaps, hook misuse, and state management issues.

## Required References

Before starting, read `references/frontend/react-performance.md` for performance patterns and anti-pattern catalog.

## Step 1: Scope

1. Identify changed React files (`git diff --name-only` filtered to `.tsx`, `.jsx`)
2. If no diff, scan the provided directory or entire `src/` for React components
3. Build a list of components to check

## Step 2: Anti-Pattern Check

Scan for common React anti-patterns:

1. **Unnecessary `useEffect`** — Effects that could be derived state or event handlers
2. **Missing dependencies** — `useEffect`/`useMemo`/`useCallback` with incomplete dep arrays
3. **Prop drilling** — Props passed through 3+ levels without consumption
4. **Inline object/array creation** — Objects/arrays created in render causing re-renders
5. **Index as key** — Using array index as React key in dynamic lists
6. **Direct DOM manipulation** — Using `document.querySelector` instead of refs

## Step 3: Performance Check

Scan for performance issues:

1. **Large component re-renders** — Components that re-render on every parent render
2. **Missing memoization** — Expensive computations without `useMemo`
3. **Bundle size** — Large imports that could be lazy-loaded
4. **Image optimization** — Images not using `next/image` (in Next.js)
5. **Unnecessary client components** — Components marked `'use client'` that don't need it

## Step 4: Accessibility Check

Scan for accessibility gaps:

1. **Missing alt text** — Images without `alt` attributes
2. **Missing labels** — Form inputs without associated labels
3. **Missing button text** — Buttons without visible text or `aria-label`
4. **Color contrast** — Hardcoded colors that may have insufficient contrast
5. **Keyboard navigation** — Interactive elements not reachable via Tab

## Step 4.5: Design anti-patterns

Scan for "AI slop" visual anti-patterns. These are banned by `references/frontend/design/anti-patterns.md` — flag each hit with the file:line reference and the corrective token/pattern.

Run these greps across `components/`, `app/`, and any JSX/TSX:

| Pattern (regex) | Violation | Fix |
|---|---|---|
| `bg-gradient-to-.*bg-clip-text\|text-transparent.*bg-clip-text` | Gradient text on headings — banned everywhere | Use solid text color from the design tokens |
| `border-l-[2-9]\|border-r-[2-9]` with a color class (`border-(blue\|red\|green\|primary)-\d+`) | Side-stripe accent borders (classic AI "callout" cliche) | Replace with full border + token color, or remove border and use indent |
| `font-mono` occurrences > 3 across non-code contexts | Monospace as "technical shorthand" | Restrict mono to actual code / metadata / timestamps. Body and UI must use the display/body font |
| `#000\b\|#fff\b\|text-black\b\|bg-white\b` (hardcoded) | Pure black/white — banned | Use OKLCH near-extremes via design tokens (e.g. `#111` / `#F9FAFB` or `var(--background)` / `var(--foreground)`) |
| `text-gray-\d+` inside a JSX element whose class also contains `bg-(blue\|red\|green\|purple\|orange)-\d+` | Gray text on colored background — banned contrast pattern | Use `text-white` / `text-foreground` or re-pick the background |

For each hit, report: file:line, the matched snippet, the violated rule, and the recommended replacement. Reference `references/frontend/design/anti-patterns.md` for the full rationale and the complete AI Slop Test.

## Step 5: Report

Generate a health report:

- **Critical** (must fix): Bugs, crashes, data loss risks
- **Warning** (should fix): Performance issues, accessibility gaps
- **Info** (nice to fix): Style improvements, minor optimizations

Include file:line references for every finding.

---
name: svg-icon-creation
description: "Custom SVG icon pipeline: discovery → design → optimize → component. Use when creating SVG icons, converting icon concepts to React components, or optimizing existing SVGs for accessibility."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
argument-hint: "<icon concept or description>"
---

## Overview

Creates custom SVG icons from concept to production React components. Covers icon design, SVG optimization, and React component wrapping with accessibility.

## Step 1: Discovery

1. Understand the icon concept and intended use
2. Review existing icon style in the project (stroke vs fill, size, weight)
3. Determine icon sizes needed (16, 20, 24, 32px)
4. Check for existing icon component patterns

## Step 2: Design

1. Design the SVG icon following the project's icon style
2. Use a consistent grid (24x24 default)
3. Ensure visual clarity at smallest target size
4. Apply consistent stroke width and corner radius

## Step 3: Optimize

1. Remove unnecessary attributes and metadata
2. Simplify paths where possible
3. Use `currentColor` for fill/stroke (inherits text color)
4. Minimize file size while maintaining visual fidelity
5. Validate SVG markup

## Step 4: Component

1. Create a React component wrapping the SVG
2. Add proper TypeScript types (size, color, className props)
3. Include `aria-label` or `aria-hidden` for accessibility
4. Export from the project's icon index file
5. Add usage example

## Verification

- [ ] SVG renders correctly at all target sizes (16, 20, 24, 32px)
- [ ] `currentColor` inherits text color correctly (test in light and dark contexts)
- [ ] Component TypeScript types are correct (`npx tsc --noEmit`)
- [ ] Accessibility: decorative icons have `aria-hidden="true"`, meaningful icons have `aria-label`
- [ ] SVG file size is under 1KB after optimization

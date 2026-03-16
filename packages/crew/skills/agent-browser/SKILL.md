---
name: agent-browser
description: "Browser automation for AI agents using the agent-browser CLI (Vercel). Use when you need to navigate pages, fill forms, click elements, take screenshots, verify UI behavior, or run end-to-end verification of a running web app."
allowed-tools: Bash, Read, Write
argument-hint: "<URL or feature to verify>"
disable-model-invocation: true
---

## Overview

Live browser verification using [agent-browser](https://github.com/vercel-labs/agent-browser) — a fast Rust CLI wrapping Playwright. Drives a real Chromium instance through shell commands — no test files, no framework setup, no CI configuration required.

Use for:

- Verifying a running app against acceptance criteria
- Checking critical user flows after a feature is built
- Taking screenshots for visual review
- Debugging UI issues that only appear in a real browser
- Form and interaction testing during development

## Prerequisites

Install globally once:

```bash
npm install -g agent-browser
agent-browser install   # downloads Chromium
```

## Core Commands

### Navigation

| Command                    | What It Does              |
| -------------------------- | ------------------------- |
| `agent-browser open <url>` | Navigate to a URL         |
| `agent-browser back`       | Go back in history        |
| `agent-browser reload`     | Reload current page       |
| `agent-browser close`      | Close the browser session |

### Interaction

| Command                                   | What It Does                   |
| ----------------------------------------- | ------------------------------ |
| `agent-browser click <selector>`          | Click an element               |
| `agent-browser fill <selector> <text>`    | Clear and type into an input   |
| `agent-browser type <selector> <text>`    | Type into an element           |
| `agent-browser select <selector> <value>` | Choose a dropdown option       |
| `agent-browser hover <selector>`          | Hover over an element          |
| `agent-browser check <selector>`          | Check a checkbox               |
| `agent-browser press <key>`               | Press a key (Enter, Tab, etc.) |
| `agent-browser scroll <dir> [px]`         | Scroll up/down/left/right      |

### Semantic Locators (preferred)

| Command                                                | What It Does                   |
| ------------------------------------------------------ | ------------------------------ |
| `agent-browser find role <role> click`                 | Find by ARIA role and click    |
| `agent-browser find text "<text>" click`               | Find by visible text and click |
| `agent-browser find label "<label>" fill "<value>"`    | Find by label and fill         |
| `agent-browser find testid <id> click`                 | Find by data-testid and click  |
| `agent-browser find placeholder "<ph>" fill "<value>"` | Find by placeholder and fill   |

### Information & State

| Command                               | What It Does                             |
| ------------------------------------- | ---------------------------------------- |
| `agent-browser snapshot`              | Get accessibility tree with element refs |
| `agent-browser snapshot -i`           | Interactive elements only                |
| `agent-browser screenshot [path]`     | Take screenshot                          |
| `agent-browser screenshot --full`     | Full-page screenshot                     |
| `agent-browser screenshot --annotate` | Screenshot with numbered labels          |
| `agent-browser get text <sel>`        | Get text content                         |
| `agent-browser get url`               | Get current URL                          |
| `agent-browser get title`             | Get page title                           |
| `agent-browser get value <sel>`       | Get input value                          |
| `agent-browser eval "<js>"`           | Run JavaScript in page context           |

### Viewport & Device

| Command                              | What It Does                       |
| ------------------------------------ | ---------------------------------- |
| `agent-browser set viewport <w> <h>` | Set viewport dimensions            |
| `agent-browser set device "<name>"`  | Emulate device (e.g., "iPhone 14") |
| `agent-browser set media dark`       | Emulate dark mode                  |

### Wait

| Command                                 | What It Does                |
| --------------------------------------- | --------------------------- |
| `agent-browser wait <selector>`         | Wait for element visibility |
| `agent-browser wait <ms>`               | Wait milliseconds           |
| `agent-browser wait --text "<text>"`    | Wait for text to appear     |
| `agent-browser wait --load networkidle` | Wait for network idle       |

### Comparison & Diff

| Command                                             | What It Does                     |
| --------------------------------------------------- | -------------------------------- |
| `agent-browser diff snapshot`                       | Compare current vs last snapshot |
| `agent-browser diff url <url1> <url2>`              | Compare two URLs                 |
| `agent-browser diff url <url1> <url2> --screenshot` | Visual diff of two URLs          |

### Debug

| Command                         | What It Does          |
| ------------------------------- | --------------------- |
| `agent-browser errors`          | View page errors      |
| `agent-browser console`         | View console messages |
| `agent-browser highlight <sel>` | Highlight an element  |

## Step 1: Identify What to Verify

From the task context, determine:

- The base URL of the running app (local dev or staging)
- The critical flows to verify (auth, main feature, key forms)
- Any specific elements or states to check

## Step 2: Navigate and Verify

For each flow:

1. `agent-browser open <url>` to navigate
2. `agent-browser screenshot` to confirm the page loaded
3. `agent-browser snapshot -i` to see interactive elements
4. Interact with elements (`click`, `fill`, `find`) to drive the flow
5. `agent-browser screenshot` at key checkpoints
6. `agent-browser eval "<js>"` to read DOM state when visual inspection isn't enough

## Step 3: Report Results

After verification:

- List each flow tested with pass / fail status
- Attach screenshots for any failed or unexpected states
- Note specific selectors or elements that behaved unexpectedly
- Recommend fixes with file:line references when possible

## Asset Extraction Patterns

Ready-to-use eval snippets for extracting downloadable assets from a page. Used by `/design-extraction` Phase 8 and Mode C replication pipelines.

### All `<img>` src/srcset URLs

```bash
agent-browser eval "JSON.stringify([...document.querySelectorAll('img')].flatMap(img => {
  const urls = [];
  if (img.src && !img.src.startsWith('data:')) urls.push({url: img.src, alt: img.alt, type: 'image'});
  if (img.srcset) img.srcset.split(',').forEach(s => {
    const u = s.trim().split(/\\s+/)[0];
    if (u && !u.startsWith('data:')) urls.push({url: u, alt: img.alt, type: 'image'});
  });
  return urls;
}))"
```

### CSS background-image URLs

```bash
agent-browser eval "JSON.stringify([...new Set([...document.querySelectorAll('*')].flatMap(el => {
  const bg = getComputedStyle(el).backgroundImage;
  if (!bg || bg === 'none') return [];
  return (bg.match(/url\\(['\"]?([^'\"\\)]+)['\"]?\\)/g) || [])
    .map(u => u.replace(/url\\(['\"]?/, '').replace(/['\"]?\\)/, ''))
    .filter(u => !u.startsWith('data:') && !u.includes('gradient'));
}))])"
```

### Inline SVG markup extraction

```bash
agent-browser eval "JSON.stringify([...document.querySelectorAll('svg')].slice(0, 20).map((svg, i) => ({
  index: i,
  viewBox: svg.getAttribute('viewBox'),
  width: svg.getAttribute('width'),
  height: svg.getAttribute('height'),
  isIcon: svg.closest('button, a, nav') !== null,
  markup: svg.outerHTML.substring(0, 2000)
})))"
```

### @font-face font URLs

```bash
agent-browser eval "(() => {
  const fonts = [];
  try {
    [...document.styleSheets].forEach(sheet => {
      try {
        [...sheet.cssRules].forEach(rule => {
          if (rule.cssText && rule.cssText.includes('@font-face')) {
            const family = (rule.cssText.match(/font-family:\\s*['\"]?([^'\";}]+)/) || [])[1];
            (rule.cssText.match(/url\\(['\"]?([^'\"\\)]+)['\"]?\\)/g) || []).forEach(u => {
              fonts.push({url: u.replace(/url\\(['\"]?/, '').replace(/['\"]?\\)/, ''), family: family || 'unknown', type: 'font'});
            });
          }
        });
      } catch(e) {}
    });
  } catch(e) {}
  return JSON.stringify(fonts);
})()"
```

## Selector Strategy

Prefer semantic locators (in this order):

1. `find testid <id>` — stable, intent-clear
2. `find role <role>` / `find label "<label>"` — accessible and semantic
3. `find text "<text>"` — visible text matching
4. CSS selectors as last resort

## Verification Checklist

For each page or flow, check:

- [ ] Page renders without errors (`agent-browser errors`)
- [ ] Key elements are visible and in expected state (`agent-browser snapshot -i`)
- [ ] Forms accept input and submit correctly
- [ ] Navigation links work
- [ ] Responsive layout at mobile and desktop (`agent-browser set viewport 375 812` then `agent-browser set viewport 1280 800`)
- [ ] No broken images or missing assets (`agent-browser eval "document.querySelectorAll('img[src]').length"`)

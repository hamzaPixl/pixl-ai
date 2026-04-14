---
name: caveman-help
description: >
  Show a quick-reference card listing all caveman modes, skills, and commands. One-shot display, not a persistent mode change. Use when the user says "caveman help", "what caveman commands", "how do I use caveman", or invokes /caveman-help.
---

<!-- Vendored from https://github.com/JuliusBrussee/caveman (MIT). Frontmatter description rewritten for pixl-crew routing. -->

# Caveman Help

Display this reference card when invoked. One-shot — do NOT change mode, write flag files, or persist anything. Output in caveman style.

## Modes

| Mode | Trigger | What change |
|------|---------|-------------|
| **Lite** | `/caveman lite` | Drop filler. Keep sentence structure. **pixl-crew default.** |
| **Full** | `/caveman full` | Drop articles, filler, pleasantries, hedging. Fragments OK. |
| **Ultra** | `/caveman ultra` | Extreme compression. Bare fragments. Tables over prose. |
| **Wenyan-Lite** | `/caveman wenyan-lite` | Classical Chinese style, light compression. |
| **Wenyan-Full** | `/caveman wenyan` | Full 文言文. Maximum classical terseness. |
| **Wenyan-Ultra** | `/caveman wenyan-ultra` | Extreme. Ancient scholar on a budget. |

Mode stick until changed or session end. Off: `/caveman off` or "normal mode".

## Skills

| Skill | Trigger | What it do |
|-------|---------|-----------|
| **caveman** | `/caveman [level]` | Switch response compression level |
| **caveman-commit** | `/caveman-commit` | Terse commit messages. Conventional Commits. ≤50 char subject. |
| **caveman-review** | `/caveman-review` | One-line PR comments: `L42: bug: user null. Add guard.` |
| **caveman-compress** | `/caveman-compress <file>` | Compress .md files to caveman prose. Saves ~46% input tokens. Auto-backup `FILE.original.md`. |
| **caveman-help** | `/caveman-help` | This card. |

## pixl-crew defaults

- Default mode: **lite** (via `.claude/rules/caveman-activate.md`)
- Downstream parsers (`/cartographer`, `/spec-review`, `/pr-creation`) tested safe at lite
- Disable globally: remove or rename `.claude/rules/caveman-activate.md`

## Deactivate

Say "stop caveman" or "normal mode". Resume anytime with `/caveman`.

## More

Upstream docs: https://github.com/JuliusBrussee/caveman

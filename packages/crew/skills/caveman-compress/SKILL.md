---
name: caveman-compress
description: >
  Compress natural-language memory files (CLAUDE.md, rules, references, todos) into caveman-speak to save input tokens on every session. Preserves code, URLs, file paths, commands, markdown structure, and headings exactly. Original saved as FILE.original.md for rollback. Uses a vendored Python CLI that calls Claude to compress, then validates structure preservation. Use when the user says "compress memory file", "caveman compress", or invokes /caveman-compress. Different from /strategic-compact (which summarizes conversation context).
---

<!-- Vendored from https://github.com/JuliusBrussee/caveman (MIT). Frontmatter description rewritten for pixl-crew routing; disambiguated from /strategic-compact. -->

# Caveman Compress

## Purpose

Compress natural-language files into caveman-speak to reduce input tokens. Compressed version overwrites original. Human-readable backup saved as `<filename>.original.md`.

## Trigger

`/caveman-compress <filepath>` or when user asks to compress a memory file.

## Safety

- Skips non-natural-language files (code, JSON, YAML) automatically via `detect.py`
- Aborts if `<filename>.original.md` backup already exists (prevents overwrite)
- 500KB file-size cap
- Validates headings, code blocks, URLs, file paths preserved exactly — retries up to 2 times with targeted fixes, restores original on final failure

## Process

1. Scripts live in `skills/caveman-compress/scripts/` (adjacent to this SKILL.md).

2. Run:
   ```bash
   cd path/to/pixl-crew/skills/caveman-compress && python3 -m scripts <absolute_filepath>
   ```
   Or from the project root, pointing at the vendored copy under `packages/crew/skills/caveman-compress/`.

3. The CLI will:
   - detect file type (no tokens)
   - call Claude via `ANTHROPIC_API_KEY` env var OR the `claude --print` CLI (falls back)
   - validate output (no tokens) — headings, code blocks, URLs, paths must match
   - if errors: cherry-pick fix with Claude (targeted fixes only, no recompression)
   - retry up to 2 times
   - if still failing after 2 retries: restore original file, delete backup, report error

4. Return result to user.

## Environment

- `ANTHROPIC_API_KEY` (optional): direct API call — requires `pip install anthropic`
- Fallback: `claude --print` CLI (uses Claude Code desktop auth)
- `CAVEMAN_MODEL` (optional): override model, default `claude-sonnet-4-5`

## Compression Rules

### Remove
- Articles: a, an, the (except in lite mode)
- Filler: just, really, basically, actually, simply, essentially, generally
- Pleasantries: "sure", "certainly", "of course", "happy to", "I'd recommend"
- Hedging: "it might be worth", "you could consider", "it would be good to"
- Redundant phrasing: "in order to" → "to", "make sure to" → "ensure"
- Connective fluff: "however", "furthermore", "additionally"

### Preserve EXACTLY (never modify)
- Code blocks (fenced ``` and indented)
- Inline code (`backtick content`)
- URLs and links (full URLs, markdown links)
- File paths (`/src/components/...`, `./config.yaml`)
- Commands (`npm install`, `git commit`, `docker build`)
- Technical terms (library names, API names, protocols, algorithms)
- Proper nouns (project names, people, companies)
- Dates, version numbers, numeric values
- Environment variables (`$HOME`, `NODE_ENV`)
- All markdown headings (exact heading text)

## Recommended targets in pixl-crew

Safe to compress:
- Top-level `CLAUDE.md` files (root, `ai/`, `ai/pixl/`)
- `.claude/rules/*.md` files — one at a time, review each diff
- `packages/crew/references/**/*.md` — prose only, skip CLI-reference files

Do NOT compress:
- `packages/crew/CLAUDE.md` — contains routing tables, env vars, exact command strings
- `packages/crew/skills/*/SKILL.md` bodies — templates, exact strings
- `packages/crew/agents/*.md` frontmatter

## Rollback

```bash
mv path/to/FILE.original.md path/to/FILE.md
```

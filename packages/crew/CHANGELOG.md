# Changelog

All notable changes to the pixl-crew plugin.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer](https://semver.org/).

## [12.1.0] - 2026-04-15

Minor: vendor the [caveman](https://github.com/JuliusBrussee/caveman) token-compression plugin into the crew. Cuts output tokens ~30% on every response at the default lite level while preserving full technical accuracy. Auto-activates via a new project rule; opt-out via `/caveman off`.

### Added

- **5 new skills** under `skills/` (vendored from caveman, MIT; frontmatter rewritten for pixl-crew semantic routing):
  - `/caveman` — switch response style to token-compressed mode. Levels: `lite` (default), `full`, `ultra`, `wenyan-lite`, `wenyan-full`, `wenyan-ultra`
  - `/caveman-commit` — generate ultra-terse Conventional Commits messages (≤50 char subject, body only when "why" is non-obvious). Style override for commit messages; does NOT replace `/commit-commands:commit`
  - `/caveman-review` — one-line PR review comments (`L42: 🔴 bug: user null. Add guard.`). Style override; does NOT replace `/code-review`
  - `/caveman-compress` — Python CLI that rewrites `.md` memory files in caveman-speak, auto-saves `FILE.original.md` backup. Validates code blocks, URLs, headings, file paths preserved exactly; retries up to 2 times; restores original on final failure
  - `/caveman-help` — quick-reference card for all caveman modes and skills
- **Project rule** `.claude/rules/caveman-activate.md` — auto-activates caveman-lite as the default response style with safety carve-outs (security warnings, irreversible-action confirmations, commit/PR messages stay verbose)
- **Routing** — new "Output Style / Token Optimization" section in `skills/ROUTING.md` with disambiguation notes (`/caveman-commit` vs `/commit-commands:commit`, `/caveman-compress` vs `/strategic-compact`)
- **Skill count**: 88 → 93

### Changed

- `packages/crew/CLAUDE.md` — added "Token optimization" entry to skills list
- `packages/crew/.claude-plugin/plugin.json` — `token-optimization`, `caveman` added to keywords
- Description updated to reflect caveman suite inclusion

### Safety

- Vendored `caveman-compress` Python scripts audited: no network exfiltration (only calls Claude API via `ANTHROPIC_API_KEY` env or `claude --print` CLI fallback), writes only to target file + sibling `.original.md` backup, 500KB file-size cap, aborts if backup already exists
- Frontmatter `description:` fields rewritten in normal English to protect semantic routing from being hijacked by caveman-speak
- Agent and skill BODIES not touched — caveman changes response STYLE, not stored instructions. Zero risk to existing workflows, templates, or command strings
- Lite mode keeps sentence structure, so downstream parsers (`/cartographer`, `/spec-review`, `/pr-creation`) and the `pixl knowledge` FTS5 BM25 index stay unaffected

### Migration notes

This release is **additive only**. To disable caveman per session: `/caveman off`. To disable globally: remove or rename `.claude/rules/caveman-activate.md`. To roll back entirely:

```bash
rm -rf packages/crew/skills/caveman*/
rm .claude/rules/caveman-activate.md
git checkout packages/crew/skills/ROUTING.md packages/crew/CLAUDE.md packages/crew/.claude-plugin/plugin.json
```

## [12.0.0] - 2026-04-15

Major: design vocabulary overhaul. Adopts impeccable's anti-pattern catalog and AI Slop Test, plus taste-skill aesthetic packs, so the crew produces meaningfully better UI by default.

### Added

- **10 design references** under `references/frontend/design/` adapted from [impeccable](https://github.com/pbakaus/impeccable) (Apache-2.0):
  - `typography.md` — modular scales (1.25× min ratio), 4-step font selection heuristic, OpenType, fluid vs fixed type
  - `color-and-contrast.md` — OKLCH over HSL, tinted neutrals, dark-mode as surface elevation, WCAG ratios
  - `spatial-design.md` — 4pt scale, `gap` over margins, `auto-fit minmax(280px,1fr)` grids, container queries
  - `motion-design.md` — exponential easing, high-impact moments, reduced-motion mandate
  - `interaction-design.md` — optimistic UI, focus-visible states, empty states that teach
  - `responsive-design.md` — mobile-first, container queries, content-driven breakpoints
  - `ux-writing.md` — verb+object buttons, error formula (what/why/how), translation expansion budgets
  - `craft-process.md` — structured build order (structure → layout → type → states → motion → responsive)
  - `anti-patterns.md` — banned fonts (Inter, Roboto, DM Sans, Playfair, …), banned patterns (gradient text, side-stripe borders >1px, glassmorphism, nested cards, gray-on-colored), the AI Slop Test
  - `design-context-protocol.md` — 3-step protocol for capturing brand voice into `.design-context.md`
- **4 new steering skills** for incremental design improvement:
  - `/design-critique` — independent UI review scoring 6 axes (typography, color, spacing, motion, interaction, originality) 1–10 against anti-patterns
  - `/design-polish` — surgical micro-improvements (type scale, spacing rhythm, focus states); never refactors structure
  - `/design-distill` — strip overdesign; consolidate palette, flatten nested cards, reduce decoration
  - `/design-context` — interactive Q&A → writes `.design-context.md` at project root (required before net-new design work)
- **4 new archetypes** in `references/frontend/design-archetypes.md` from [taste-skill](https://github.com/Leonxlnx/taste-skill):
  - `Industrial Brutalist`, `Minimalist (Editorial Utility)`, `Soft (Awwwards-tier)`, `Stitch (Taste Standard)`
- **Design Quality Gate** section in `frontend-engineer` agent — mandatory consult of `anti-patterns.md` and AI Slop Test before declaring UI complete

### Changed

- **`/website`** — design-system step now requires reading typography, color-and-contrast, spatial-design, anti-patterns; AI Slop Test runs before scaffolding
- **`/website-theme`** — extended archetype list with the 4 new packs; theme propositions must avoid banned fonts/patterns
- **`/design-variants`** — each variant must map to a distinct archetype and pass the anti-patterns check; report labels each variant's archetype
- **`/react-doctor`** — added Step 4.5 "Design anti-patterns" scan (gradient text, side-stripe borders, font-mono overuse, hardcoded `#000`/`#fff`, gray-on-colored)
- **`frontend-engineer`** agent — added `design-critique`, `design-polish`, `design-distill`, `design-context` to skill list; new Design Quality Gate + Design Context Protocol sections
- **`references/INDEX.md`** — new "Design Vocabulary" section indexing all 10 design references
- **Skill count**: 84 → 88

### Migration notes

This release is **additive only**. No existing skills were removed or renamed. Existing projects continue to work unchanged. To benefit from the new vocabulary on existing sites:

1. Run `/design-context` to capture brand voice into `.design-context.md`
2. Run `/design-critique` to score current UI
3. Run `/design-polish` (or `/design-distill`) to apply auto-fixes

The major version bump signals the meaningful quality shift in default UI output, not a breaking API change.

### Sources

- impeccable by [pbakaus](https://github.com/pbakaus) — Apache-2.0
- taste-skill by [Leonxlnx](https://github.com/Leonxlnx) — referenced for archetype packs

## Earlier versions

See git history (`git log --oneline -- packages/crew/`) for releases prior to 12.0.0.

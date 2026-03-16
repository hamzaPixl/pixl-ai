---
name: vision-advisory
description: "Full advisory vision package for client projects: intake company docs, deep market research, vision synthesis, functional architecture, business model design, and implementation roadmap. Use when producing a strategic vision document, advisory deliverable, or consulting package for a company."
allowed-tools: WebSearch, WebFetch, Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion
argument-hint: "<company docs path(s) + brief — e.g. '/path/to/deck.pdf — Speos wants to become the citizen digital mailbox'>"
---

# Vision Advisory Package

Full advisory workflow: document intake → deep research → vision synthesis → functional architecture → business model → roadmap. Produces a multi-document advisory package ready for client delivery.

Read `references/vision-template.md` for the slide-ready section format used in the vision document.

## Phase 1: Intake & Discovery

Parse provided documents and gather project context.

### 1a: Document Ingestion

Read all provided files (PDF, markdown, text) using the Read tool:
- Extract company identity, current products, stated ambitions
- Extract constraints (regulatory, technical, organizational)
- Note any existing vision elements, strategic priorities, or KPIs

### 1b: Gap Filling

Use `AskUserQuestion` to clarify:

| Question | Why |
|----------|-----|
| Target market / geographic scope | Scopes research in Phase 2-3 |
| Timeline horizon (3-year, 5-year, 10-year) | Shapes roadmap ambition |
| Budget envelope (order of magnitude) | Grounds investment estimates |
| Output language (FR / EN / NL) | All deliverables in this language |
| Key stakeholders / decision-makers | Tone and framing of the document |
| Known competitors to analyze | Seeds competitive research |

### 1c: Persist

Write intake summary to `.context/advisory-intake.md`:
- Company name, one-liner description
- Stated ambition / problem to solve
- Constraints and parameters
- Output language
- Source documents referenced

## Phase 2: Company Deep-Dive

Research the company deeply using parallel `WebSearch` calls.

Launch these searches concurrently:

### 2a: Core Identity
- What the company does (products, services, solutions)
- Size (employees, revenue, offices, countries)
- Ownership structure (public, private, subsidiary)
- History (founding, key milestones, acquisitions)

### 2b: Asset Mapping

| Asset Type | What to find |
|---|---|
| **Products/Solutions** | Full portfolio with names, descriptions, target markets |
| **Client base** | Named clients, industries served, reference projects |
| **Partnerships** | Technology partners, channel partners, certifications |
| **Geographic presence** | Offices, markets, regions of strength |
| **Technical expertise** | Core competencies, patents, certifications |
| **Brand/Trust** | Government contracts, enterprise clients, industry recognition |

### 2c: Current Positioning
- How the market perceives them (analyst reports, press mentions, awards)
- Brand strengths and weaknesses
- Net Promoter Score or customer sentiment if findable

### 2d: Recent Moves
- Press releases (last 12 months)
- Acquisitions, partnerships, product launches
- Leadership changes, strategy announcements

Write `.context/company-profile.md` with all findings, citing sources.

## Checkpoint 1

Use `AskUserQuestion` to validate:
- "Here is my understanding of the company and its assets. Is this accurate? Anything to add or correct?"
- Present the key facts, asset map, and stated ambition
- Confirm which sectors/verticals to deep-dive in Phase 4

## Phase 3: Market & Competitive Intelligence

Research the relevant markets using parallel `WebSearch` calls.

### 3a: Market Sizing
For each relevant market:
- Current market size (global + relevant region)
- Growth rate (CAGR)
- Key growth drivers
- Regulatory tailwinds or headwinds

Use searches like:
```
"<market name> market size 2025 2026 forecast"
"<market name> Europe growth CAGR"
"<regulation name> compliance deadline requirements"
```

### 3b: Regulatory Landscape
- EU/national regulations creating forced demand
- Upcoming compliance deadlines and their impact
- Funding programs (EU Digital Europe, Horizon, national grants)
- Government procurement budgets and tenders

### 3c: Technology Trends
- Technologies being adopted in the company's markets
- Table stakes capabilities vs. differentiators
- Emerging standards and protocols
- AI/automation adoption patterns in the sector

### 3d: Competitor Analysis

For 3-5 key competitors:

| Dimension | What to find |
|---|---|
| Name + size | Revenue, employees, market position |
| Product offering | What they sell, pricing model |
| Recent moves | Launches, acquisitions, partnerships |
| Innovation | What they're doing with new technology |
| Weakness | Where they're vulnerable |
| vs. Subject company | Head-to-head comparison |

Write `.context/market-intelligence.md` with all findings, citing sources.

## Checkpoint 2

Use `AskUserQuestion` to validate:
- "Here is the market landscape and competitive analysis. Does the focus look right?"
- Present market sizing, top competitors, regulatory drivers
- Confirm sector priorities before deep-dive work

## Phase 4: Sector Deep-Dives

Identify the 2-4 most relevant verticals based on company assets + market opportunity. Use parallel Agent calls (one per sector) for speed.

For each sector, research and document:

### Sector Analysis Template

| Section | Content |
|---------|---------|
| **Why this sector** | Strategic fit with company assets |
| **Citizen/end-user pain points** | What problems exist today |
| **B2B/enterprise pain points** | What organizations struggle with |
| **Differentiating use cases** | 3-5 concrete use cases the company could deliver |
| **Competitive positioning** | Who else serves this sector, gaps to exploit |
| **Immediate value potential** | Quick wins vs. long-term plays |

### Sector Scoring Matrix

Score each sector on these dimensions (1-5):

| Dimension | What it measures |
|-----------|-----------------|
| **Volume** | Size of addressable market / number of potential users |
| **Regulatory complexity** | Regulations creating forced demand or barriers to entry |
| **Emotional anchoring** | How much end-users care (daily life impact) |
| **Ease of entry** | How quickly the company can enter (assets, partnerships) |
| **Revenue potential** | Monetization opportunity (willing to pay, budget exists) |

Write `.context/sector-analysis.md` with analysis and scoring matrix.

## Phase 5: Vision Synthesis

Synthesize all research into a coherent vision narrative. This is the creative core — transform data into strategy.

### 5a: Paradigm Shift
Frame the transition from current state to future state:
- **From**: What the company/market does today (status quo)
- **To**: What the future looks like (the vision)
- **The shift**: What fundamental change makes this possible (technology, regulation, behavior)

### 5b: Core Value Proposition
- **Problem**: The core problem being solved (specific, quantified)
- **Solution**: What the company will build/become
- **Strategic objective**: The measurable goal (market share, users, revenue)

### 5c: "Why This Company?"
Articulate the competitive moat — 5-7 unique advantages:
- Existing assets that competitors lack
- Regulatory positioning (certifications, contracts)
- Technical capabilities
- Client relationships and trust
- Geographic or market access
- Brand and reputation

### 5d: Vision Statement
Write a compelling 2-3 sentence vision statement that:
- Names the company
- States the transformation
- Quantifies the ambition
- Sets the timeline

## Phase 6: Functional Architecture

Design the product/service architecture that delivers the vision.

### 6a: Feature Foundation
Define the functional tiers:

| Tier | Purpose | Monetization |
|------|---------|-------------|
| **Free base** | Adoption driver, network effects | Free / freemium |
| **Paid premium** | Value-added services | Subscription |
| **Enterprise** | Custom / regulated needs | Per-seat or per-org |

### 6b: Feature Categories
Based on the vision and sector analysis, define functional categories. Each category maps to a section of the product:

For each category:
- **Name and description**
- **Key features** (3-5 per category)
- **User benefit** (why they'd use it)
- **Business value** (how it drives revenue or adoption)
- **Tier** (free / premium / enterprise)

### 6c: Business Model Design
- Revenue streams (subscription, transaction, licensing, data)
- Pricing strategy (freemium, tiered, usage-based)
- Unit economics (CAC, LTV, margin targets)
- Network effects and moats

## Phase 7: Strategic Roadmap

Build a phased implementation plan.

### 7a: Phased Trajectory

Define 3-4 phases with clear milestones:

For each phase:

| Element | Content |
|---------|---------|
| **Name** | Short, descriptive phase name |
| **Duration** | Months or quarters |
| **Objective** | What this phase achieves |
| **Key milestones** | 3-5 measurable milestones |
| **KPIs** | How to measure success |
| **Investment estimate** | Team size, budget range |
| **Dependencies** | What must be true before this phase starts |

### 7b: Go-to-Market Strategy
- Channel strategy (direct, partner, platform)
- First movers (which clients/segments to target first and why)
- Adoption levers (regulatory mandate, cost savings, network effects)
- Marketing approach (thought leadership, events, partnerships)

### 7c: Risk Analysis

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| [Name] | High/Med/Low | High/Med/Low | [Strategy] |

Cover at minimum: regulatory risk, competitive risk, adoption risk, technical risk, funding risk.

## Phase 8: Package Assembly

Write all deliverables to `advisory-<company>-<date>/` directory.

### Deliverable Files

| File | Content | Length |
|------|---------|--------|
| `00-executive-summary.md` | 1-page overview: vision, key numbers, top 3 arguments, call to action | ~2 pages |
| `01-vision-document.md` | Full vision document with slide-ready sections (use `references/vision-template.md` structure) | ~30-50 pages |
| `02-market-intelligence.md` | Market sizing, competitors, regulations, sector deep-dives | ~15-25 pages |
| `03-implementation-roadmap.md` | Phased roadmap with milestones, KPIs, investment, risks | ~10-15 pages |
| `04-task-breakdown.md` | Actionable tasks — invoke `/task-plan` on the roadmap to generate this | ~5-10 pages |
| `sources.md` | All cited sources with URLs, organized by section | — |

### Vision Document Structure (01-vision-document.md)

Follow the slide-ready format from `references/vision-template.md`. Each section should:
- Have a clear title that works as a slide header
- Include a "key message" line (the one thing the audience should remember)
- Use tables and bullet points for scanability
- Include data points with source citations

### Assembly Checklist

Before writing deliverables:
1. Verify all `.context/` research files are complete
2. Ensure all source URLs are collected
3. Confirm output language matches intake specification
4. Cross-reference sector analysis scores with roadmap priorities

Write all files in the output language specified during intake. Use professional, advisory tone — authoritative but accessible.

## Guidelines

- **Produce all deliverables in the specified language** (FR/EN/NL) — ask in Phase 1, apply everywhere
- **Name real companies**: Don't say "a large retailer" — say "Carrefour". Specificity makes it actionable.
- **Cite everything**: Every market size, growth rate, and trend must have a source URL
- **Be conservative on projections**: Under-promise. Use "conservative" estimates for revenue and adoption.
- **Slide-ready sections**: Each section in the vision doc should map to a presentation slide
- **Quantify everything**: market sizes in currency, growth in %, timelines in months, teams in FTEs
- **Use parallel execution**: Phases 2-3 use parallel WebSearch calls; Phase 4 uses parallel agents per sector
- **Two checkpoints**: After Phase 2 and after Phase 3 — validate direction before heavy synthesis work
- **Advisory tone**: Write as a strategic advisor, not a technical spec. Frame everything in business value.

## Related Skills

- **`/strategic-intel`** — Lighter-weight single-document business intelligence report
- **`/task-plan`** — Invoked in Phase 8 to produce the task breakdown deliverable
- **`/content-marketing`** — After vision is produced, create content strategy to support go-to-market
- **`/prd-pipeline`** — If the vision leads to a product build, feed the roadmap into the PRD pipeline

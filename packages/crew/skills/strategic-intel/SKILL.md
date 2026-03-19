---
name: strategic-intel
description: "Strategic business intelligence report: company profiling, market research, competitor analysis, and go-to-market roadmap. Use when analyzing a company's position, finding business opportunities, or preparing a management pitch. For a full multi-document advisory package with architecture and roadmap, use /vision-advisory instead."
allowed-tools: WebSearch, WebFetch, Read, Write, Edit, Bash, Agent, AskUserQuestion
argument-hint: "<company name or URL + problem/opportunity — e.g. 'Zetes needs new AI projects' or 'https://acme.com wants to enter the EU market'>"
---

# Strategic Intelligence Report

Deep business intelligence analysis: company profiling → market research → opportunity mapping → client targeting → roadmap with revenue projections. Produces an actionable strategic document that can be used as a management pitch or go-to-market plan.

## Step 1: Briefing

Gather context from the user's request or argument:

1. **Company**: name, URL, or description
2. **Problem/Opportunity**: what they're trying to solve (e.g. "no new projects", "entering new market", "launching AI offering")
3. **Constraints**: budget, team size, timeline, geographic scope
4. **Output format**: internal pitch, client proposal, strategic plan, or full report

If any of these are unclear, use `AskUserQuestion` to clarify. Don't assume — the quality of the analysis depends on understanding the real problem.

## Step 2: Company Profiling

Research the company deeply using `WebSearch` and `WebFetch`:

### 2a: Core Identity
- What the company does (products, services, solutions)
- Size (employees, revenue, offices, countries)
- Ownership structure (public, private, subsidiary, PE-backed)
- History (founding, key milestones, acquisitions)

### 2b: Asset Mapping
This is critical — map everything the company already has:

| Asset Type | What to find |
|---|---|
| **Products/Solutions** | Full product portfolio with names, descriptions, target markets |
| **Client base** | Named clients, industries served, reference projects |
| **Partnerships** | Technology partners, channel partners, certifications |
| **Geographic presence** | Offices, markets, regions of strength |
| **Technical expertise** | Core competencies, patents, certifications |
| **Brand/Trust** | Government contracts, enterprise clients, industry recognition |

Use the company's website (references page, about page, solutions page), LinkedIn, Crunchbase, Wikipedia, and press releases.

### 2c: Revenue Model
- How does the company make money? (project-based, SaaS, licensing, hardware, consulting)
- Recurring vs one-time revenue split
- Average deal size (if inferable)
- Sales cycle (direct sales, tenders, channel)

Output: Structured company profile with all assets cataloged.

## Step 3: Market Analysis

Research the relevant markets based on the company's assets and the stated problem/opportunity.

### 3a: Market Sizing
For each relevant market, find:
- Current market size (global + relevant region)
- Growth rate (CAGR)
- Key drivers of growth
- Regulatory tailwinds or headwinds

Use searches like:
```
"<market name> market size 2025 2026 forecast"
"<market name> Europe growth CAGR"
"<regulation name> compliance deadline requirements"
```

### 3b: Regulatory Opportunities
Regulations create forced demand — the best kind of business opportunity. Search for:
- New EU/national regulations requiring compliance
- Upcoming deadlines that create urgency
- Funding programs (EU Digital Europe, Horizon, national grants)
- Government procurement budgets

### 3c: Technology Trends
- What technologies are being adopted in the company's markets?
- What are buyers asking for that the company doesn't offer yet?
- What are the "table stakes" capabilities vs. differentiators?

### 3d: Competitor Analysis

For each major competitor (3-5):
| Dimension | What to find |
|---|---|
| Name + size | Revenue, employees, market position |
| Recent moves | Product launches, acquisitions, partnerships |
| AI/Innovation | What they're doing with new technology |
| Weakness | Where they're vulnerable |
| vs. Subject company | Head-to-head comparison |

Output: Market analysis with sizing, trends, regulations, and competitive landscape.

## Step 4: Opportunity Mapping

Cross-reference company assets (Step 2) with market opportunities (Step 3) to identify concrete business propositions.

For each opportunity, evaluate:

| Criteria | Question |
|---|---|
| **Asset fit** | Does the company already have the skills/clients/tech to address this? |
| **Market timing** | Is there a deadline, regulation, or trend creating urgency? |
| **Competition** | How crowded is this space? Can the company differentiate? |
| **Revenue potential** | How big could this be in 1-3 years? |
| **Effort to launch** | How much investment (time, money, people) to start? |
| **Risk** | What could go wrong? |

Score each opportunity as: **High / Medium / Low** priority.

Only present the top 3-4 opportunities — quality over quantity.

## Step 5: Proposition Design

For each selected opportunity, produce a complete proposition:

### 5a: Value Proposition
| Element | Content |
|---|---|
| **Name** | Short, memorable name for the offering |
| **One-liner** | What it does in one sentence |
| **Target customer** | Who buys this, by name/segment |
| **Problem solved** | What pain it addresses |
| **Value delivered** | Quantified benefits (%, €, time saved) |
| **Why this company** | Unique advantage vs. competitors |
| **Why now** | Urgency driver (regulation, market shift, competitor moves) |

### 5b: Client Targeting
Name specific potential clients:

| Client | Segment | Why them | How to reach | Deal size estimate |
|---|---|---|---|---|
| [Name] | [Industry] | [Specific reason] | [Channel] | [€ range] |

For each segment, provide 3-10 named targets. Prefer:
- Existing clients (easiest to convert)
- Companies affected by regulation (forced demand)
- Companies in the company's geographic stronghold

### 5c: Acquisition Strategy
How to actually get these clients:

**Existing clients** → Upsell motion:
1. Identify the commercial/account manager
2. Provide them with a specific pitch: "Your client needs X because of Y regulation"
3. Offer a free audit/assessment as door opener
4. Convert assessment into paid implementation

**New clients via regulation** → Thought leadership + RFP:
1. Publish content (whitepaper, webinar) on the regulation
2. Attend relevant industry events/salons
3. Monitor procurement portals (TED Europa, national platforms)
4. Pre-position by responding to RFIs 3-6 months before RFP
5. Form consortiums with local partners for geographic reach

**New clients via channel** → Partner leverage:
1. Identify parent company / partner channels
2. Package the offering for the partner's sales team
3. Create co-branded materials
4. Revenue share model

### 5d: Pricing Model
| Component | Range | Model |
|---|---|---|
| Setup/Implementation | €X-Y | One-time |
| Monthly SaaS/Service | €X-Y/month | Recurring |
| Per-transaction | €X-Y/unit | Usage-based |

## Step 6: Roadmap

Create a phased roadmap with 4 phases:

### Phase 0: Foundation (Month 1-2)
- Internal pitch (this report = the base)
- Form core team
- Build POC/MVP for top 1-2 propositions
- Cost: estimate in € and FTEs

### Phase 1: First Clients (Month 3-5)
- Pilot with 1-2 existing clients (lowest friction)
- Respond to 2-3 relevant tenders/RFPs
- Attend 1 industry event
- Expected outcome: 2-3 pilots running

### Phase 2: Scale (Month 6-9)
- Convert pilots to paid contracts
- Launch marketing (content, events, partnerships)
- Hire/upskill team for delivery capacity
- Expected outcome: 5-10 contracts signed

### Phase 3: Growth (Month 10-18)
- Full product catalogue launch
- Channel partnerships active
- Expansion to adjacent markets
- Expected outcome: significant revenue line

### Revenue Projections (Conservative)

| Year | Proposition 1 | Proposition 2 | Proposition 3 | Total |
|---|---|---|---|---|
| Year 1 | €X | €X | €X | **€X** |
| Year 2 | €X | €X | €X | **€X** |
| Year 3 | €X | €X | €X | **€X** |

### Investment vs. Return
| Item | Amount |
|---|---|
| Total investment (Phase 0-1) | €X |
| Revenue Year 1 | €X |
| ROI | Xx |

## Step 7: Pitch Package

Produce the final deliverables:

### 7a: One-liner (for elevator pitch)
> "We have [asset], [regulation/market] forces [target clients] to need [solution], and it's worth €[amount] in [timeframe]. Cost to start: €[amount]."

### 7b: Three Killer Arguments
1. **The market pull**: [regulation/trend] creates forced demand
2. **The unfair advantage**: [company asset] that competitors lack
3. **The cost of inaction**: what happens if they don't move

### 7c: Report Output

Write the complete report to a markdown file in the working directory:

```
strategic-intel-<company>-<date>.md
```

Structure:
1. Executive Summary (1 page)
2. Company Profile & Assets
3. Market Analysis & Opportunities
4. Propositions (with client targets)
5. Roadmap & Revenue Projections
6. Pitch Arguments
7. Sources

## Guidelines

- **Name real companies**: Don't say "a large retailer" — say "Marks & Spencer". Specificity is what makes this actionable.
- **Cite everything**: Every market size, growth rate, and trend must have a source.
- **Be conservative on projections**: Under-promise, over-deliver. Use "conservative" estimates.
- **Focus on forced demand**: Regulations, compliance deadlines, and industry shifts > nice-to-have innovation.
- **Map assets to opportunities**: The best opportunities leverage what the company already has.
- **Quantify everything**: €, %, headcount, timeline. Vague advice is useless.
- **Iterate with the user**: Use `AskUserQuestion` after Step 2 (confirm company understanding) and Step 4 (validate opportunity priorities) to avoid going down the wrong path.
- **Use parallel agents**: For Step 2 and Step 3, launch multiple web searches in parallel for speed.

## Related Skills

- **`/content-marketing`** — After identifying propositions, create content (whitepapers, landing pages) to generate leads
- **`/task-plan`** — Break the roadmap into sprint-sized tasks for execution
- **`/benchmark`** — Compare the company's technical implementation against competitors

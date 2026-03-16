# Analysis Categories

Templates for the 8 structural categories used by `/prd-analysis`. Each category defines what to extract, how to infer when the PRD is silent, and the exact output format.

## 1. Project Overview

### What to Extract
- **Elevator pitch**: 1-2 sentence summary of what the project does and for whom
- **Goals**: Top 3-5 business/product goals
- **Success metrics**: Quantifiable KPIs (user counts, conversion rates, performance targets)
- **Target users**: User personas or segments with their primary needs

### Inference Rules
- If no elevator pitch: synthesize from the first paragraph + feature list
- If no success metrics: mark as `[inferred]` and derive from goals (e.g., goal "increase signups" → metric "signup conversion rate")
- If no target users: infer from feature descriptions (e.g., "admin dashboard" implies admin users)

### Output Format
```markdown
## 1. Project Overview

**Elevator Pitch**: {1-2 sentences}

**Goals**:
1. {Goal with measurable outcome}
2. {Goal with measurable outcome}

**Success Metrics**:
| Metric | Target | Baseline |
|--------|--------|----------|
| {metric} | {target value} | {current or N/A} |

**Target Users**:
- **{Persona}**: {primary need} — {how the product serves them}
```

## 2. Domain Model

### What to Extract
- **Entities**: Core domain objects (User, Order, Invoice, etc.)
- **Relationships**: How entities relate (1:N, N:M, composition, aggregation)
- **Bounded contexts**: Logical groupings of related entities and behaviors
- **Key domain events**: State transitions that matter (OrderPlaced, PaymentProcessed)

### Inference Rules
- If no explicit entities: extract nouns from feature descriptions
- If no bounded contexts: group entities by feature area (auth, billing, content, etc.)
- If no relationships: infer from feature descriptions ("user creates an order" → User 1:N Order)

### Output Format
```markdown
## 2. Domain Model

**Entities**:
| Entity | Description | Key Attributes |
|--------|-------------|----------------|
| {Entity} | {what it represents} | {important fields} |

**Relationships**:
- {Entity A} → {Entity B}: {cardinality} ({description})

**Bounded Contexts**:
- **{Context Name}**: {entities included} — {responsibility}

**Domain Events**:
- `{EventName}`: {trigger} → {consequence}
```

## 3. Architecture Overview

### What to Extract
- **Components**: Frontend, backend, database, external services
- **Integrations**: Third-party APIs, services, webhooks
- **Tech stack**: Languages, frameworks, databases, infrastructure
- **Deployment**: Cloud provider, containerization, CI/CD

### Inference Rules
- If no tech stack specified: do NOT assume — mark as `[to be decided]`
- If no deployment: mark as `[to be decided]`
- If integrations mentioned without detail: list them with `[details needed]`

### Output Format
```markdown
## 3. Architecture Overview

**Components**:
- **Frontend**: {framework, hosting}
- **Backend**: {framework, runtime}
- **Database**: {engine, hosting}
- **External Services**: {list}

**Integrations**:
| Service | Purpose | Direction |
|---------|---------|-----------|
| {service} | {what it does} | inbound/outbound/bidirectional |

**Tech Stack**: {language(s)}, {framework(s)}, {database(s)}, {infra}

**Deployment**: {strategy or [to be decided]}
```

## 4. Milestones

### What to Extract
- **Phases**: Named delivery milestones in chronological order
- **Objectives**: What each phase delivers (user-facing value)
- **Dependencies**: What must be complete before a phase can start
- **Timeline**: Relative sizing if absolute dates aren't given

### Inference Rules
- If no explicit milestones: create 3 phases — Foundation, Core Features, Polish/Launch
- If no timeline: assign relative T-shirt sizes (S/M/L) to phases
- Foundation phase always includes: project setup, auth, core data model

### Output Format
```markdown
## 4. Milestones

| Phase | Name | Objectives | Dependencies | Size |
|-------|------|------------|--------------|------|
| 1 | {name} | {bullet list of deliverables} | — | {S/M/L} |
| 2 | {name} | {bullet list of deliverables} | Phase 1 | {S/M/L} |
```

## 5. Feature Breakdown

### What to Extract
- **Epics**: High-level feature groups (Authentication, Dashboard, Billing, etc.)
- **Features**: Specific capabilities within each epic
- **Priority**: MoSCoW classification (must/should/could)
- **User stories**: "As a {user}, I want to {action}, so that {benefit}" (if present)

### Inference Rules
- If no priority scheme: classify by dependency order — foundational = must, dependent = should, nice-to-have = could
- If features listed without epics: group by domain area
- Map P0/P1/P2 → must/should/could if the PRD uses numbered priorities

### Output Format
```markdown
## 5. Feature Breakdown

### Epic: {Epic Name}

| Feature | Priority | Description |
|---------|----------|-------------|
| {feature} | must/should/could | {1-line description} |

**User Stories** (if available):
- As a {user}, I want to {action}, so that {benefit}
```

## 6. Technical Requirements

### What to Extract
- **Performance**: Response times, throughput, page load targets
- **Security**: Authentication, authorization, data protection, compliance
- **Scalability**: Expected load, growth projections, scaling strategy
- **Accessibility**: WCAG level, assistive technology support
- **Browser/device support**: Minimum supported browsers, mobile requirements

### Inference Rules
- If no performance targets: use sensible defaults — API < 200ms, page load < 3s, FCP < 1.5s
- If no security requirements: infer from feature set (auth features → JWT, RBAC; payments → PCI awareness)
- If no accessibility: default to WCAG 2.1 AA
- Mark all inferences as `[inferred — industry default]`

### Output Format
```markdown
## 6. Technical Requirements

**Performance**:
| Metric | Target | Notes |
|--------|--------|-------|
| {metric} | {target} | {source or [inferred]} |

**Security**:
- {requirement with rationale}

**Scalability**:
- Expected load: {concurrent users, requests/sec}
- Growth: {projection}

**Accessibility**: {WCAG level}

**Browser/Device Support**: {list}
```

## 7. Risks & Assumptions

### What to Extract
- **Risks**: Technical, business, and operational risks
- **Probability**: High/Medium/Low likelihood of occurring
- **Impact**: High/Medium/Low severity if it occurs
- **Mitigation**: Strategy to reduce probability or impact
- **Assumptions**: Things assumed to be true but not verified

### Inference Rules
- If no risks listed: identify common risks based on feature set:
  - Third-party integrations → API availability risk
  - User-generated content → moderation/abuse risk
  - Payment processing → compliance risk
  - Tight timeline → scope creep risk
- Always include: "Requirements may change as user feedback is gathered" as a baseline assumption

### Output Format
```markdown
## 7. Risks & Assumptions

**Risks**:
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| {risk description} | H/M/L | H/M/L | {strategy} |

**Assumptions**:
- {assumption — what would change if this is wrong}
```

## 8. Open Questions

### What to Extract
- **Blocking**: Questions that must be answered before implementation can start
- **Informational**: Questions that would improve the plan but aren't blockers
- **Category**: Which analysis category the question relates to

### Inference Rules
- If the PRD is vague on technical decisions (DB choice, hosting) → blocking question
- If the PRD is vague on nice-to-have features → informational question
- Always check for: unclear user roles, undefined edge cases, missing error handling requirements

### Output Format
```markdown
## 8. Open Questions

### Blocking
| # | Category | Question | Impact |
|---|----------|----------|--------|
| 1 | {category} | {question} | {what's blocked} |

### Informational
| # | Category | Question | Default if Unanswered |
|---|----------|----------|-----------------------|
| 1 | {category} | {question} | {reasonable default} |
```

## Common Patterns

### PRD Styles

Different PRDs require different parsing strategies:

| PRD Style | Strategy |
|---|---|
| **User-story based** | Map stories to features, extract acceptance criteria directly |
| **Feature list** | Group into epics, generate stories and acceptance criteria |
| **Narrative/prose** | Extract entities and actions, reconstruct as structured features |
| **Technical spec** | Architecture-heavy — focus on extracting user-facing features |
| **One-pager** | High-level — more inference needed, more open questions |

### Requirement ID Convention

Requirements use `R-NNN` format with sequential numbering:
- `R-001` through `R-099`: functional requirements
- `R-100` through `R-149`: non-functional requirements
- `R-150` through `R-199`: constraints

This matches the format used by `/spec-review` for coverage scanning.

# Skill Routing Guide

Decision tree: "I want to build X" → use skill Y.

## Build Something New

### Websites & Frontend

| I want to...                             | Use                                        |
| ---------------------------------------- | ------------------------------------------ |
| Build a full website from scratch        | `/website` (Mode A — discovery workflow)   |
| Build a website from a design spec       | `/website` (Mode B — spec-fed)             |
| Replicate an existing website            | `/website` (Mode C — replicate from URL)   |
| Build a multi-agent website project      | `/website-project` (orchestrated pipeline) |
| Extract design from Figma/URL/screenshot | `/design-extraction`                       |
| Add/compose shadcn/ui components         | `/shadcn-ui`                               |
| Create custom SVG icons                  | `/svg-icon-creation`                       |
| Add i18n (EN/FR/NL)                      | `/i18n-setup`                              |
| Build an admin dashboard                 | `/admin-dashboard`                         |
| Build a blog                             | `/blog`                                    |

### Backend & APIs

| I want to...                                       | Use                      |
| -------------------------------------------------- | ------------------------ |
| Build a standalone Python API from scratch         | `/fastapi-api`           |
| Add a Python service to an existing monorepo       | `/fastapi-service`       |
| Add a CRUD endpoint to an existing FastAPI service | `/pydantic-api-endpoint` |
| Build a TypeScript SaaS service with DDD           | `/saas-microservice`     |
| Build a fullstack app (frontend + backend)         | `/fullstack-app`         |

### Infrastructure

| I want to...                    | Use                    |
| ------------------------------- | ---------------------- |
| Dockerize + deploy to Cloud Run | `/docker-cloudrun`     |
| Set up Docker + Prisma          | `/docker-prisma-setup` |
| Set up PM2 process management   | `/pm2`                 |
| Create a Makefile               | `/makefile`            |

## Modify Something Existing

### Website Modifications

| I want to...                                     | Use                 |
| ------------------------------------------------ | ------------------- |
| Change only the theme (colors, fonts, shadows)   | `/website-theme`    |
| Change only the layout (sections, grids, shapes) | `/website-layout`   |
| Change both theme + layout                       | `/website-theme` then `/website-layout` |

### Code Quality

| I want to...                                  | Use                     |
| --------------------------------------------- | ----------------------- |
| Run a self-review and fix loop                | `/self-review-fix-loop` |
| Reduce code (dedup, dead code, consolidation) | `/code-reduction`       |
| Diagnose React issues                         | `/react-doctor`         |
| Run an SEO audit                              | `/seo-audit`            |
| Apply DDD patterns to existing code           | `/ddd-pattern`          |
| Get a CTO-level architectural review          | `/cto-review`           |
| Decompose a PR into feature components        | `/cartographer`         |
| Run Python tests with smart discovery         | `/test-runner`          |
| Verify a running app in the browser           | `/agent-browser`        |
| Review a PR before merge                      | `/code-review`          |
| Compare code against open-source examples     | `/benchmark`            |
| Audit database schema                         | `/schema-audit`         |
| Catalog and standardize error handling         | `/error-catalog`        |
| Audit API endpoints for consistency            | `/api-audit`            |
| Review dependencies for CVEs/outdated/licenses | `/dependency-review`    |
| Eliminate dead code with static analysis       | `/code-reduction` (quick mode) |
| Investigate production incident or generate runbook | `/runbook`          |

## Plan & Strategize

| I want to...                         | Use                     |
| ------------------------------------ | ----------------------- |
| Analyze and structure a PRD          | `/prd-analysis`         |
| Execute a full PRD autonomously      | `/prd-pipeline`         |
| Break a feature into tasks           | `/task-plan`            |
| Validate implementation against spec | `/spec-review`          |
| Update plan after spec changes       | `/task-plan` (drift mode) |
| Plan a sprint                        | `/sprint-planning`      |
| Create a content strategy            | `/content-marketing`    |
| Automate content generation pipeline | `/content-pipeline`     |
| Plan a safe database/code migration  | `/migration-plan`       |
| Build a multi-agent LLM pipeline     | `/multi-agent-pipeline` |
| Run same change across many files/modules | `/batch`           |

## Plugin Development

| I want to...                         | Use                    |
| ------------------------------------ | ---------------------- |
| Create or scaffold a plugin          | `/plugin-structure`    |
| Create an agent                      | `/agent-development`   |
| Create, detect, or improve a skill   | `/skill-factory`       |
| Create a slash command               | `/command-development` |
| Create a hook                        | `/hook-development`    |
| Configure plugin settings            | `/plugin-settings`     |

## Workflow & Utilities

| I want to...                     | Use                        |
| -------------------------------- | -------------------------- |
| Create a PR                      | `/pr-creation`             |
| Generate or improve a CLAUDE.md  | `/claude-md`               |
| Initialize crew for a project    | `/crew-init`               |
| Parse a PDF/text/JSON file       | `/file-parser`             |
| Run a persistent autonomous loop | `/ralph-loop-crew`         |
| Explore the studio stacks        | `/studio-guide`            |
| Export a session summary         | `/session-export`          |
| Persist tasks across sessions    | `/task-persist`            |
| Create a context packet          | `/context-packet-template` |
| Capture session decisions        | `/session-retrospective`   |
| Onboard a new client project     | `/client-project-setup`    |

## Swift / iOS

| I want to...                           | Use                |
| -------------------------------------- | ------------------ |
| Build SwiftUI views + state management | `/swift-patterns` (topic: swiftui) |
| Implement Swift 6.2 concurrency        | `/swift-patterns` (topic: concurrency) |
| Add actor-based persistence            | `/swift-patterns` (topic: actors) |
| Write testable Swift with DI           | `/swift-patterns` (topic: testing) |

## Security & Evaluation

| I want to...                             | Use              |
| ---------------------------------------- | ---------------- |
| Scan for secrets, CVEs, OWASP issues     | `/security-scan` |
| Evaluate a skill or agent's quality      | `/eval-harness`  |
| Learn from session patterns              | `/continuous-learning` |
| Manage context before compaction         | `/strategic-compact` |

## Best Practices (Reference Skills)

| Topic                 | Use                                 |
| --------------------- | ----------------------------------- |
| Stripe integration    | `/stripe-best-practices`            |
| Postgres optimization | `/supabase-postgres-best-practices` |

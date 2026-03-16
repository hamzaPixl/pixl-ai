# References Index

Shared domain knowledge auto-loaded by agents and skills via `references/` in CLAUDE.md.

## Agent Routing

| File                    | Purpose                                                  |
| ----------------------- | -------------------------------------------------------- |
| `AGENT-REGISTRY.md`    | Machine-readable agent index: model, memory, skills, delegation graph |

## Backend

| File                            | Purpose                                                                  |
| ------------------------------- | ------------------------------------------------------------------------ |
| `backend/api-design.md`         | REST API design conventions, endpoint naming, error formats              |
| `backend/database-patterns.md`  | Database access patterns, repository layer, migrations                   |
| `backend/ddd-patterns.md`       | Domain-Driven Design: entities, value objects, aggregates, domain events |
| `backend/media-patterns.md`     | Presigned URL flow, image processing, CDN integration                    |
| `backend/content-versioning.md` | Copy-on-write versioning, draft/published lifecycle                      |
| `backend/python-patterns.md`        | Pydantic entities, FastAPI patterns, Python service conventions      |
| `backend/schema-audit-checklist.md` | Index, constraint, naming, N+1, and migration safety checklists     |
| `backend/migration-safety.md`       | Expand-migrate-contract pattern, safe/dangerous operations, rollback |

## DevOps

| File                              | Purpose                                               |
| --------------------------------- | ----------------------------------------------------- |
| `devops/ci-cd-patterns.md`        | GitHub Actions, Cloud Run deployment, pipeline stages |
| `devops/docker-best-practices.md` | Multi-stage builds, layer caching, security hardening |

## Frontend

| File                                     | Purpose                                                            |
| ---------------------------------------- | ------------------------------------------------------------------ |
| `frontend/component-variants.md`         | 920-line map of JSX patterns to 12 design archetypes               |
| `frontend/design-archetypes.md`          | Visual archetype definitions (Corporate, Startup, Editorial, etc.) |
| `frontend/design-reference-routing.md`   | How to route design references to extraction pipelines             |
| `frontend/design-resources.md`           | Font stacks, icon sets, color palettes, image sources              |
| `frontend/design-spec-schema.md`         | JSON schema for `design-spec.json` output                          |
| `frontend/i18n-conventions.md`           | EN/FR/NL translation conventions, key naming                       |
| `frontend/react-performance.md`          | Memoization, lazy loading, bundle optimization                     |
| `frontend/sector-design-intelligence.md` | Industry-specific design patterns (SaaS, e-commerce, etc.)         |
| `frontend/seo-reference.md`              | Meta tags, structured data, sitemap, OG tags                       |
| `frontend/ui-constraints.md`             | Layout constraints, responsive breakpoints, spacing system         |
| `frontend/url-design-extraction.md`      | Extracting design tokens from live website URLs                    |

## Methodology

| File                                | Purpose                                          |
| ----------------------------------- | ------------------------------------------------ |
| `methodology/parallel-execution.md` | Multi-agent parallelism patterns                 |
| `methodology/refactor-planning.md`  | Safe refactoring strategies, dependency analysis |
| `methodology/tdd.md`                | Test-driven development workflow                 |
| `methodology/verification.md`       | Self-verification and quality gates              |
| `methodology/vertical-slice.md`     | Vertical slice architecture for feature delivery |
| `methodology/client-onboarding.md`  | Client project onboarding checklist and CLAUDE.md template |

## Orchestration

| File                               | Purpose                                                |
| ---------------------------------- | ------------------------------------------------------ |
| `orchestration/context-packet.md`  | Standard format for passing data between agents        |
| `orchestration/memory-protocol.md` | Cross-session memory: decision logs, session summaries |
| `orchestration/model-routing.md`   | Cost-optimized model selection for agents              |

## Go

| File                    | Purpose                                                |
| ----------------------- | ------------------------------------------------------ |
| `go/patterns.md`        | Project layout, error handling, DI, concurrency, HTTP  |
| `go/testing.md`         | Table-driven tests, integration tests, benchmarks      |

## Intel

| File                              | Purpose                                              |
| --------------------------------- | ---------------------------------------------------- |
| `intel/pixl-cli-reference.md`     | pixl CLI commands for AST search, artifacts, events  |

## Standards

| File                              | Purpose                                             |
| --------------------------------- | --------------------------------------------------- |
| `standards/code-review.md`        | Code review checklist and quality criteria          |
| `standards/commit-conventions.md` | Conventional commits (feat:, fix:, refactor:, etc.) |
| `standards/pr-best-practices.md`  | PR title, description, review workflow              |
| `standards/security-audit.md`     | OWASP Top 10 audit checklist                        |

## Swift

| File                           | Purpose                                              |
| ------------------------------ | ---------------------------------------------------- |
| `swift/coding-style.md`        | Swift naming, optionals, error handling, value types  |
| `swift/testing.md`             | Swift Testing, XCTest, protocol DI for testability   |
| `swift/concurrency.md`         | Swift 6.2 concurrency, actors, Sendable, async/await |

## Writing

| File                       | Purpose                                |
| -------------------------- | -------------------------------------- |
| `writing/humanizer.md`     | Making AI-generated text sound natural |
| `writing/writing-plans.md` | Structured writing workflow templates  |

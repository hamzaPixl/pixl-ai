# Sprint Workflow

Structured development cycle: Think → Plan → Build → Review → Test → Ship → Reflect.

Each phase maps to specific pixl-crew skills. Phases execute sequentially — each feeds the next.

## Phase 1: Think

**Goal**: Understand what to build and why. Clarify requirements before any planning.

| Skill | When |
|-------|------|
| `/prd-analysis` | Parse and structure a PRD or requirements doc |
| `/vision-advisory` | Full advisory package for strategic decisions |
| `/strategic-intel` | Business intelligence and market research |

**Output**: Structured requirements with clear scope and acceptance criteria.

## Phase 2: Plan

**Goal**: Decompose work into ordered, atomic tasks with dependencies.

| Skill | When |
|-------|------|
| `/task-plan` | Decompose a feature into dependency-ordered tasks |
| `/sprint-planning` | Break tasks into sprint-sized iterations |
| `/migration-plan` | Plan safe database or code migrations |

**Output**: Ordered task list with acceptance criteria and agent assignments.

## Phase 3: Build

**Goal**: Implement the planned tasks using specialist agents.

| Agent / Skill | When |
|---------------|------|
| `frontend-engineer` | React/Next.js components, pages, styling |
| `backend-engineer` | API endpoints, domain models, database |
| `fullstack-engineer` | Cross-boundary features (API + UI) |
| `devops-engineer` | Docker, CI/CD, deployment configs |
| `/website` | Full website build |
| `/saas-microservice` | New backend service with DDD |

**Output**: Working code, committed in atomic units.

## Phase 4: Review

**Goal**: Validate code quality before shipping.

| Skill | When |
|-------|------|
| `/code-review` | PR-level review (3 or 8 reviewers) |
| `/cross-review` | Multi-model review for critical changes |
| `/cto-review` | Architectural critique of the full branch |
| `/self-review-fix-loop` | Iterative review-and-fix cycle |
| `/security-scan` | Security-focused audit |

**Output**: Review report with findings classified as AUTO-FIX or ASK.

## Phase 5: Test

**Goal**: Verify correctness and catch regressions.

| Skill | When |
|-------|------|
| `/test-runner` | Run targeted test subsets |
| `/test-writer` | Generate test suites from source |
| `/health` | Full quality dashboard (types, lint, tests, dead code) |
| `/spec-review` | Compare implementation against requirements |

**Output**: All tests passing, health score at target level.

## Phase 6: Ship

**Goal**: Commit, push, create PR, verify deployment.

| Skill | When |
|-------|------|
| `/commit` | Create conventional commit |
| `/commit-push-pr` | Full commit → push → PR flow |
| `/ship-milestone` | End-to-end milestone shipping |
| `/deploy-verify` | Post-merge canary checks |
| `/changelog` | Generate release notes |

**Output**: Merged PR, verified deployment.

## Phase 7: Reflect

**Goal**: Learn from the cycle and improve.

| Skill | When |
|-------|------|
| `/retro` | Engineering retrospective from git history |
| `/continuous-learning` | Record patterns and instincts |
| `/health --trend` | Track quality trends over time |

**Output**: Retrospective report, updated instincts.

## Quick Reference

```
/prd-analysis → /task-plan → build → /code-review → /test-runner → /commit-push-pr → /retro
```

For critical changes, expand the review phase:
```
/code-review --full → /cross-review → /security-scan → /self-review-fix-loop
```

For releases, expand the ship phase:
```
/ship-milestone → /deploy-verify → /changelog → /retro
```

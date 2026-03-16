# Client Project Onboarding

Reference for the `/client-project-setup` skill and `onboarding-agent`.

## Onboarding Checklist

- [ ] Project directory accessible
- [ ] Git repository initialized
- [ ] Dependencies installable
- [ ] Dev server starts
- [ ] Tests pass (if any)
- [ ] CLAUDE.md generated
- [ ] Context packet created
- [ ] Team briefed on conventions

## CLAUDE.md Template for Client Projects

```markdown
# {project-name}

{one-line description}

## Structure

\`\`\`
{annotated directory tree — top 2 levels, key files noted}
\`\`\`

## Setup

\`\`\`bash
{install command}     # install dependencies
{dev command}         # start dev server
{test command}        # run tests
{build command}       # production build
\`\`\`

## Key Patterns

- **Architecture**: {layer-based / feature-based / DDD / monolith / microservices}
- **Naming**: {conventions for files, components, routes}
- **State management**: {approach — Redux, Zustand, server state, etc.}
- **API pattern**: {REST / GraphQL / tRPC — how endpoints are structured}
- **Auth**: {strategy — JWT, session, OAuth provider}

## Rules

- {critical rule 1 — e.g., "Always use the shared Button component, never html button"}
- {critical rule 2 — e.g., "All API routes must use the withAuth middleware"}
- {critical rule 3}

## Common Tasks

### Add a new page/route
1. {step 1}
2. {step 2}

### Add a new API endpoint
1. {step 1}
2. {step 2}

### Deploy
1. {step 1}
```

## Context Packet Structure

The context packet (`.context/project-overview.md`) should contain:

1. **Stack Summary**: Framework, language, database, hosting — in one paragraph
2. **Architecture Overview**: How components relate, data flow, key boundaries
3. **External Dependencies**: Third-party services, APIs, databases
4. **Development Workflow**: Branch strategy, PR process, deployment pipeline
5. **Risk Register**: Known technical debt, security concerns, missing infrastructure

## Project Type Detection

| Signal | Project Type | Recommended Skills |
|--------|-------------|-------------------|
| `next.config.*` | Next.js website/app | `/website`, `/seo-audit`, `/react-doctor` |
| `fastify` in deps | Node.js API | `/ddd-pattern`, `/api-audit`, `/schema-audit` |
| `fastapi` in deps | Python API | `/fastapi-service`, `/api-audit`, `/schema-audit` |
| `prisma/` directory | Database-backed | `/schema-audit`, `/migration-plan` |
| Multiple services | Monorepo/microservices | `/task-plan`, `/ddd-pattern` |
| `stripe` in deps | Payment integration | `/stripe-best-practices` |
| `supabase` in deps | Supabase backend | `/supabase-postgres-best-practices` |

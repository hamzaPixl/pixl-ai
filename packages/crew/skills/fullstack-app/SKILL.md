---
name: fullstack-app
description: "Build a fullstack application combining Next.js frontend with SaaS backend. Orchestrates both studio stacks, API integration, and end-to-end testing. Use when asked to create a full application with both frontend and backend."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Task
argument-hint: "<application description>"
context: fork
disable-model-invocation: true
---

## Overview

Combines the nextjs and saas studio stacks to build a complete fullstack application. Scaffolds both frontend and backend, implements the API contract between them, and verifies the end-to-end flow.

## Studio Stacks

- Frontend: `studio/stacks/nextjs/` (75 templates)
- Backend: `studio/stacks/saas/` (17 foundation packages + service template)

## Suggested Team

- **architect** — System design, API contract, data model
- **fullstack-engineer** — Cross-boundary implementation
- **qa-engineer** — E2E testing, review loops
- **devops-engineer** — Docker, CI/CD for both services

## Process

### Phase 1: Architecture

1. Define the domain model and API contract
2. Decide on data flow (REST API, server actions, or tRPC)
3. Plan authentication flow (JWT from backend, session on frontend)

### Phase 1.5: API Contract Specification

3.5. Define shared Zod schemas for all request/response types
3.6. Document endpoints in OpenAPI format (method, path, body, response)
3.7. Agree on error response format: `{ error: { code, message } }`
3.8. Write the API contract to `.context/api-contract.json` (type: architecture, see `references/orchestration/context-packet.md`)
3.9. Write architecture decisions and component tree to `.context/architecture.md`

### Phase 2 + 3: Parallel Backend & Frontend Build

You MUST spawn the following 2 agents in parallel via the `Task` tool. Do NOT run these sequentially — the backend and frontend can be built simultaneously because both receive the API contract from Phase 1.5.

#### Pre-wave: Context Packet

Before spawning agents, compile a **context packet** containing:

- The full API contract from `.context/api-contract.json` (Zod schemas, OpenAPI endpoint definitions, error format)
- The domain model from Phase 1
- Authentication flow design (JWT structure, session strategy)

#### Parallel Wave — Backend + Frontend (2 parallel Task agents)

| Agent | Role              | Directory         | Responsibility                                                                                                                                                                                                                                                                                                                                                      |
| ----- | ----------------- | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A     | backend-engineer  | `<service-dir>/`  | Read `.context/api-contract.json` before scaffolding. Run `/saas-microservice` — scaffold and implement all backend endpoints from the API contract. Verify API endpoints are working and documented (Swagger). **File ownership:** the service directory ONLY. DO NOT create or modify any files in `<frontend-dir>/`.                                             |
| B     | frontend-engineer | `<frontend-dir>/` | Read `.context/api-contract.json` for API client generation. Run `/website` — scaffold the frontend, create typed fetch wrappers from the endpoint definitions, build pages that fetch and display data, add forms that create/update data through the API. **File ownership:** the frontend directory ONLY. DO NOT create or modify any files in `<service-dir>/`. |

Each agent prompt MUST include:

- The full context packet (API contract, domain model, auth flow)
- Its assigned directory path
- Explicit anti-conflict guard: "You MUST NOT create or modify any files outside `<your-directory>/`"

### Phase 4: Integration

After both agents complete:

10. Test the full flow end-to-end
11. Set up CORS configuration between services
12. Configure authentication flow (login → JWT → API calls)
13. Run `/agent-browser` to verify critical flows on the running app
14. Run `/self-review-fix-loop` for final quality check

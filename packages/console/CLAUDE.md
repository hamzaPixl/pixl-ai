# pixl-console

React SPA dashboard — TanStack Router, React Query, Zustand, shadcn/ui.

## Structure

```
src/
├── routes/             # TanStack Router file-based routing (~40 pages)
│   ├── __root.tsx      # Root layout (error boundary, token refresh)
│   ├── index.tsx       # Home with project auto-redirect
│   ├── auth.tsx        # Login/signup
│   ├── project.$projectId.*  # Project-scoped pages
│   └── settings.*      # User/workspace settings
├── components/         # ~193 files
│   ├── ui/             # shadcn/ui primitives + custom icons
│   ├── insights/       # KpiCard, ActivityChart, ArtifactsTab
│   └── session/        # NeedsAttentionRail, NodeRow, SessionStatsStrip
├── hooks/              # React Query hooks
│   ├── queries/        # Domain-scoped: use-sessions, use-features, use-epics, etc.
│   ├── use-event-stream.ts  # WebSocket SSE with batched invalidation
│   └── use-kanban-dnd.ts    # Drag-and-drop state (dnd-kit)
├── lib/
│   ├── api/            # Typed HTTP client (12 domain modules)
│   │   ├── core.ts     # get/post/put/patch/del helpers, ApiRequestError
│   │   └── *.ts        # auth, sessions, events, work-items, agents, run, etc.
│   ├── query.ts        # QueryClient singleton (staleTime: 30s, gcTime: 5m)
│   └── query-keys.ts   # Project-scoped key factory
├── stores/             # Zustand
│   ├── auth.ts         # User, isAuthenticated, workspaceId (persisted)
│   ├── project.ts      # currentProjectId, projects (persisted)
│   └── ui.ts           # Theme, sidebar, view preferences (persisted)
└── types/              # TypeScript interfaces per domain
```

## Key Routes

| URL Pattern | Page |
|---|---|
| `/` | Project selection, auto-redirect to last project |
| `/auth` | Login/signup |
| `/project/$projectId` | Project dashboard |
| `/project/$projectId/sessions` | Session list + detail |
| `/project/$projectId/features` | Kanban/list/table views |
| `/project/$projectId/epics` | Epic list + feature tree |
| `/project/$projectId/agents` | Agent config + model selection |
| `/project/$projectId/workflows` | Workflow definitions |
| `/project/$projectId/artifacts` | Artifact gallery |
| `/project/$projectId/gates` | Gate approval interface |
| `/project/$projectId/insights` | Cost, metrics, activity |
| `/project/$projectId/settings/*` | General, GitHub, DNS, environment |
| `/settings/*` | Profile, workspace, members, sandboxes |

## API Client

`lib/api/core.ts` — all requests go through typed helpers:
- Base URL: `/api` (proxied to `localhost:8420` in dev)
- Auth: cookie-based (`credentials: "include"`)
- `X-Workspace-ID` header auto-set from store
- 401 → auto-logout (except auth routes)
- `ApiRequestError` for non-2xx with status/detail/body

Project context: routes call `setApiProjectContext(projectId)` in `beforeLoad`.

## Real-Time Updates

`use-event-stream.ts` — WebSocket connection to `/api/ws/events/{projectId}`:
- Batched query invalidation (1.5s window) to prevent thundering herd
- Auto-reconnect with exponential backoff (1s → 30s)
- Selective cache invalidation based on event type
- Active sessions refetch every 3-5s; completed sessions don't

## State Management

| Store | Persisted Keys | Purpose |
|---|---|---|
| `auth` | workspaceId | User session, JWT lifecycle |
| `project` | currentProjectId | Active project selection |
| `ui` | theme, featuresViewMode, featuresGroupBy | UI preferences |

## Development

```bash
pnpm install                    # install deps
pnpm dev                        # dev server at :5173
pnpm build                      # tsc -b && vite build
pnpm lint                       # ESLint
pnpm test:e2e                   # Playwright tests
pnpm test:e2e:install           # install browsers first
```

Vite proxies `/api` → `localhost:8420` and `/api/ws` with WebSocket support.

## Patterns

- **shadcn/ui** for all UI primitives — run `pnpm shadcn` to add components
- **Lucide React** for icons (primary), **React Icons** for fallbacks
- **Framer Motion** for animations
- **Recharts** for charts
- **Shiki** for syntax highlighting
- Path alias: `@/*` → `./src/*`
- Dark mode via CSS class + CSS variables (managed by next-themes + Zustand)
- Query keys are project-scoped: `[projectId, "domain", "action", ...params]`

## Gotchas

- Routes must call `setApiProjectContext(projectId)` in `beforeLoad` — forgetting this breaks all API calls
- WebSocket batches invalidations at 1.5s — UI updates may lag slightly after events
- Auth store only persists `workspaceId` — user object is re-fetched on mount via `/auth/me`
- Feature view mode (kanban/list/table) persisted in localStorage — survives page refresh
- `pnpm test:e2e:install` must run before first Playwright test

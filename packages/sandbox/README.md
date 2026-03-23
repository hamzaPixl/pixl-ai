# pixl-sandbox

Cloudflare Sandbox containers for pixl — isolated project runtimes with git, pixl CLI, and Claude Code.

## Architecture

```
pixl CLI (sandbox commands)
  ↓ httpx
Hono Router (Cloudflare Worker)
  ↓ getSandbox()
@cloudflare/sandbox SDK
  ↓
Container (Python 3.12 + pixl + Claude Code + git)
  ↓
pixl.db (events, sessions, artifacts)
```

Each project gets an isolated container (Cloudflare Durable Object) with:
- Python 3.12, uv, pixl CLI + engine + crew
- Claude Code CLI
- Git (with push support via token auth)
- SQLite-backed pixl.db for workflow tracking

## Setup

```bash
make setup    # npm install
make dev      # local dev server (wrangler)
make deploy   # deploy to Cloudflare
```

### Secrets

| Secret | Required | Purpose |
|--------|----------|---------|
| `ANTHROPIC_API_KEY` | Yes | Claude API access inside containers |
| `JWT_SECRET` | Yes | HS256 secret for JWT auth (preferred) |
| `SANDBOX_API_KEY` | No | Static bearer token fallback (legacy) |
| `OPENAI_API_KEY` | No | OpenAI access inside containers |
| `ALLOWED_ORIGINS` | No | CORS origins (comma-separated) |

```bash
npx wrangler secret put ANTHROPIC_API_KEY
npx wrangler secret put JWT_SECRET
```

### Authentication

JWT tokens with scoped access (preferred over static API keys):

| Scope | Access |
|-------|--------|
| `read` | GET endpoints only |
| `write` | GET + POST (except destroy) |
| `admin` | All operations including destroy |

The CLI generates scoped JWTs automatically when `PIXL_SANDBOX_JWT_SECRET` is set. Static API key fallback grants `admin` scope for backwards compatibility.

Rate limiting: 60 requests/minute per IP. Audit logging on POST/DELETE.

## API Reference

### Lifecycle

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/sandboxes` | Create sandbox — single-call: env vars, git clone/init, pixl init |
| `DELETE` | `/sandboxes/:id` | Destroy sandbox |

**Create request:**
```json
{
  "projectId": "acme-landing",
  "repoUrl": "https://github.com/user/acme-landing",
  "branch": "main",
  "envVars": { "GITHUB_TOKEN": "ghp_xxx" }
}
```

### Observability

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/sandboxes/:id/status` | Versions, git info, project state, env key names |
| `GET` | `/sandboxes/:id/events` | Workflow events from container pixl.db |
| `GET` | `/sandboxes/:id/sessions` | Workflow sessions |
| `GET` | `/sandboxes/:id/sessions/:sid/export` | Export session bundle (session + nodes + events) |
| `POST` | `/sandboxes/:id/sessions/import` | Import session bundle |
| `GET` | `/sandboxes/:id/export` | Bulk export (events + sessions + artifacts) |
| `GET` | `/sandboxes/:id/usage` | Operation stats |
| `POST` | `/sandboxes/:id/env` | Update env vars at runtime |

### Execution

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/sandboxes/:id/exec` | Execute command (JSON response) |
| `POST` | `/sandboxes/:id/exec/stream` | Execute command (SSE stream) |
| `POST` | `/sandboxes/:id/workflow` | Run pixl workflow (JSON response) |
| `POST` | `/sandboxes/:id/workflow/stream` | Run pixl workflow (SSE stream) |
| `POST` | `/sandboxes/:id/workflow/cancel` | Cancel running workflow (SIGINT) |

### Git

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/sandboxes/:id/git` | Git status, log, branch, remote |
| `POST` | `/sandboxes/:id/git/push` | Push to remote |
| `POST` | `/sandboxes/:id/git/config` | Set user.name, user.email, remote URL |

### Files

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/sandboxes/:id/files` | Write file |
| `GET` | `/sandboxes/:id/files/*` | Read file |

### Processes

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/sandboxes/:id/process/start` | Start background process |
| `DELETE` | `/sandboxes/:id/process/:pid` | Kill background process |

## CLI Usage

```bash
# Configure
pixl config set sandbox.url https://pixl-sandbox.account.workers.dev
pixl config set sandbox.api_key <key>

# Create project (clones repo, sets env, inits pixl)
pixl sandbox create acme-landing --repo-url https://github.com/user/repo --env GITHUB_TOKEN=ghp_xxx

# Run workflow
pixl sandbox workflow acme-landing --prompt "Build a landing page" --yes

# Monitor
pixl sandbox status acme-landing
pixl sandbox events acme-landing
pixl sandbox sessions acme-landing

# Git operations
pixl sandbox git acme-landing status
pixl sandbox git acme-landing log
pixl sandbox git acme-landing push

# Cleanup
pixl sandbox destroy acme-landing
```

## Docker Image

Base: `cloudflare/sandbox:0.7.18`

| Tool | Version |
|------|---------|
| Python | 3.12 |
| uv | 0.6.0 |
| pixl | 9.0.2 |
| Claude Code | latest |

## Verification

```bash
make typecheck    # tsc --noEmit
make docker-test  # build + smoke test
make test-e2e     # full E2E suite (requires running worker)
```

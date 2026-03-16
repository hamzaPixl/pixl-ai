---
name: pm2
description: "Set up PM2 process management for local development and production — ecosystem config with multi-service orchestration (Node.js, Python, Docker), Makefile shortcuts, and monitoring. Use when asked to set up PM2, configure local dev environment, manage multiple services, or create process management for an application."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
argument-hint: "<application or project to manage with PM2>"
---

## Overview

Configures PM2 process management for multi-service projects: ecosystem file, Makefile shortcuts, service orchestration (Node.js + Python + Docker), and monitoring.

## Step 1: Discovery

1. Detect application types in the project (Node.js, Python, Docker services)
2. Identify entry points and start commands for each service
3. Check for existing PM2 config, Makefile, docker-compose.yml
4. Identify dependencies between services (e.g., API depends on DB)
5. Check available package managers (npm/bun/pnpm, pip/uv)

## Step 2: Ecosystem Config

Create `ecosystem.config.cjs` at project root.

### Patterns by service type:

**Node.js apps** (Next.js, Express, etc.):

```js
{
  name: "my-web",
  cwd: "./web",
  script: "npm",
  args: "run dev",
  watch: false,
  env: { NODE_ENV: "development" },
}
```

**Python apps** (FastAPI, Django, Flask):

> PM2 can't run `python -m ...` directly. Use a shell script wrapper.

1. Create `scripts/start-<service>.sh`:

```bash
#!/usr/bin/env bash
cd "$(dirname "$0")/.."
exec python3 -m uvicorn myapp.main:app --host 0.0.0.0 --port 8080 --reload
```

2. `chmod +x scripts/start-<service>.sh`
3. Reference in ecosystem config:

```js
{
  name: "my-api",
  script: "./scripts/start-api.sh",
  watch: false,
  env: { ENVIRONMENT: "local" },
}
```

**Docker-managed services** (databases, Redis, etc.):

```js
{
  name: "my-db",
  script: "docker",
  args: "compose up postgres --no-log-prefix",
  autorestart: false,
  watch: false,
}
```

### Environment variables

- Reference `.env` file via `dotenv` in the app code — don't hardcode secrets in ecosystem config
- Use `env` block only for service-level overrides (ports, hosts, feature flags)

## Step 3: Makefile

Create a `Makefile` with standard targets:

```makefile
.PHONY: dev stop logs status install test

dev:        ## Start all services via PM2
	pm2 start ecosystem.config.cjs

stop:       ## Stop all services
	pm2 stop all
	docker compose down

logs:       ## Tail PM2 logs
	pm2 logs

status:     ## Show PM2 status
	pm2 status

restart:    ## Restart all services
	pm2 restart all

install:    ## Install all dependencies
	pip install -r requirements.txt
	cd web && npm install

test:       ## Run tests
	python -m pytest tests/ -v

help:       ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'
```

Adapt targets to the project's actual stack and commands.

## Step 4: Production Config (optional)

For production deployments, add clustering and restart policies:

```js
{
  name: "my-api",
  script: "./dist/server.js",
  instances: "max",          // cluster mode
  exec_mode: "cluster",
  max_memory_restart: "500M",
  env_production: {
    NODE_ENV: "production",
    PORT: 3000,
  },
}
```

For Python production, use gunicorn instead of uvicorn --reload.

## Step 5: Verify

- [ ] `make dev` (or `pm2 start ecosystem.config.cjs`) launches all services
- [ ] `pm2 status` shows all services as "online" after 5 seconds
- [ ] Each service responds (health check, curl, browser)
- [ ] `make stop` cleanly stops everything including Docker
- [ ] `pm2 logs <service>` shows meaningful output

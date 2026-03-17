---
name: docker-cloudrun
description: "Containerize an application and create a complete Cloud Run deployment pipeline with Docker, docker-compose, and GitHub Actions. Use when asked to dockerize, containerize, or deploy to Cloud Run."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
argument-hint: "<application to containerize>"
disable-model-invocation: true
---

## Overview

Containerizes an application with Docker and creates a complete Cloud Run deployment pipeline including multi-stage Dockerfile, docker-compose for local development, and GitHub Actions CI/CD.

**Why multi-stage builds**: Separating build and runtime stages reduces image size by 60-80% (no compiler, dev deps) and shrinks the attack surface. Running as a non-root user prevents container escape exploits from gaining host-level access.

## Required References

Before starting, read these files:

- `references/devops/docker-best-practices.md` — Dockerfile patterns, layer caching, security
- `references/devops/ci-cd-patterns.md` — CI/CD pipeline patterns and deployment strategies

## Step 1: Discovery

1. Detect application language, framework, and build system
2. Identify environment variables and secrets needed
3. Check for existing Docker configuration
4. Determine Cloud Run requirements (CPU, memory, scaling)

## Step 2: Dockerfile

1. Create multi-stage Dockerfile (deps → build → production)
2. Optimize for layer caching
3. Pin base image versions
4. Run as non-root user
5. Add `.dockerignore`

## Step 3: Docker Compose

1. Create `docker-compose.yaml` for local development
2. Add service dependencies (database, Redis, etc.)
3. Configure health checks
4. Mount source for hot reload in development

## Step 4: Cloud Run Deployment

1. Create GitHub Actions workflow for Cloud Run
2. Configure GCP authentication
3. Set up environment variables and secrets
4. Configure auto-scaling, min/max instances
5. Add staging and production environments

## Gotchas

- Cloud Run requires the container to listen on the `PORT` environment variable (not hardcoded ports) — the service will fail health checks and never become healthy if the port is hardcoded
- Multi-stage builds must copy only production dependencies — copying `devDependencies` or test files into the runtime stage bloats the image and leaks build tooling
- Cloud Run cold starts are proportional to image size — keep the container image under 500MB and avoid heavy initialization logic (eager DB connections, large file reads at startup)
- `.dockerignore` must exclude `.git`, `node_modules`, `.env`, and test directories — a missing or incomplete `.dockerignore` can bloat images 10x and leak secrets into layers
- GitHub Actions needs Workload Identity Federation for keyless auth to GCP — service account JSON keys are a security risk and should not be stored as repository secrets

## Step 5: Verify

- [ ] Docker build succeeds locally
- [ ] `docker-compose up` starts all services
- [ ] Application responds to health checks
- [ ] CI pipeline passes (if GitHub Actions configured)

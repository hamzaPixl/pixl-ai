---
name: fastapi-service
description: "Scaffold a single FastAPI microservice within an EXISTING monorepo. Use when adding a Python service alongside existing ones. Generates domain layer, API endpoints, infrastructure wiring, Dockerfile, and CI/CD. Routing: for a STANDALONE Python API from scratch → /fastapi-api. For a TypeScript SaaS service with DDD → /saas-microservice."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
argument-hint: "<service name and primary entity>"
---

## Overview

Scaffolds a complete FastAPI microservice following monorepo conventions: domain layer (entities, repositories), API endpoints (Pydantic schemas, routes), infrastructure (database, config), Dockerfile, and CI/CD.

## Step 1: Discovery

1. Detect monorepo structure and conventions
2. Identify existing services for pattern reference
3. Determine the service's domain (name, entities, relationships)
4. Check for shared libraries and utilities

## Step 2: Domain Layer

1. Create domain entities with Pydantic models
2. Define repository interfaces
3. Add domain events if cross-service communication needed

## Step 3: API Layer

1. Create Pydantic request/response schemas
2. Build CRUD route handlers with dependency injection
3. Add authentication and authorization middleware
4. Wire up OpenAPI documentation

## Step 4: Infrastructure

1. Create SQLAlchemy/database models
2. Implement repository with database backend
3. Add configuration loading (environment variables)
4. Create database migrations

## Step 5: Dockerfile

1. Multi-stage build optimized for Python/uv
2. Pin base image versions
3. Non-root user in production

## Step 6: CI/CD

1. GitHub Actions workflow for the new service
2. Test, lint, typecheck, build stages
3. Deploy job template for Cloud Run

## Step 7: Verify

- [ ] Service starts and responds to health checks
- [ ] CRUD endpoints work correctly
- [ ] Tests pass
- [ ] Typecheck passes
- [ ] Docker build succeeds

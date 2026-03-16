---
name: pydantic-api-endpoint
description: "Add a complete CRUD endpoint to an existing FastAPI service. Use when asked to create a new API resource, add CRUD routes, scaffold an endpoint, or build a REST API for a new entity. Generates Pydantic schemas, route handlers, repository, and tests."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
argument-hint: "<entity name to add CRUD for>"
---

## Overview

Adds a complete CRUD endpoint to an existing FastAPI service: Pydantic schemas for validation, route handlers, repository implementation, and tests.

## Step 1: Discovery

1. Analyze existing service structure and conventions
2. Identify the entity to add (name, fields, relationships)
3. Check for existing repository layer pattern
4. Determine authentication/authorization requirements

## Step 2: Pydantic Schemas

1. Create request schemas (Create, Update, Filter)
2. Create response schemas (Detail, List, Summary)
3. Add field validators and custom types
4. Follow existing schema conventions

## Step 3: Repository (Conditional)

**Only if the service has a repository layer.**
1. Define repository interface
2. Implement database-backed repository
3. Add pagination and filtering support

## Step 4: Route Handlers

1. Create CRUD routes (GET list, GET detail, POST, PATCH, DELETE)
2. Add dependency injection for repository/service
3. Wire authentication and permission checks
4. Add OpenAPI metadata (tags, descriptions, examples)

## Step 5: Wire & Verify

1. Register routes in the service's router
2. Write tests for each endpoint
3. Verify: tests pass, typecheck passes, service starts

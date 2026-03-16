---
name: ddd-pattern
description: "Apply Domain-Driven Design patterns to an existing codebase: bounded contexts, entities, value objects, aggregates, repositories, domain events. Use when asked to refactor toward DDD, extract domain models, define aggregate boundaries, add domain events, or separate domain from infrastructure."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
argument-hint: "<domain area or entity to refactor>"
---

## Overview

This skill applies Domain-Driven Design (DDD) tactical and strategic patterns to an existing codebase. It starts with domain discovery — analyzing existing code to identify implicit domain concepts, relationships, and bounded context boundaries. It then models the domain explicitly, separates the domain layer from infrastructure, optionally adds domain events, and verifies the result.

The skill adapts to the target project's language (Python or TypeScript), framework, and existing architecture.

**Why DDD matters**: Bounded contexts prevent coupling by giving each concept one authoritative home — when "User" means different things in Auth vs Billing, separate models prevent changes in one from breaking the other. Private constructors on entities enforce domain invariants at the creation boundary, making invalid states unrepresentable.

## Required References

Before starting, read `references/backend/ddd-patterns.md` for tactical patterns (entities, value objects, aggregates, repositories, domain events).

## Step 1: Discovery

Analyze existing code to identify domain concepts, map relationships between entities, detect implicit bounded contexts, and catalog business rules buried in service or controller code.

**If the user provides a domain analysis or explicit model, parse it into discovery format and skip to Step 2.**

Actions:

1. Scan the codebase for entity-like classes, service classes, and data models
2. Identify implicit domain concepts from naming, relationships, and business logic
3. Map relationships between entities (associations, dependencies, event flows)
4. Detect bounded context boundaries (where concepts change meaning)
5. Catalog business rules currently embedded in controllers/services

## Step 2: Model

Define bounded contexts with clear boundaries, model entities with identity and lifecycle, extract value objects for descriptive concepts, define aggregates with invariants and consistency boundaries.

Key patterns (see `reference.md` for details):

- **Entity**: Has identity, lifecycle, mutable state. Private constructor + static factory.
- **Value Object**: Immutable, identified by attributes. Use `Object.freeze()`.
- **Aggregate**: Consistency boundary. External access only through aggregate root.
- **Repository Interface**: Defined in domain layer, implemented in infrastructure.

## Step 3: Layer Separation

Extract the domain layer from infrastructure concerns:

1. Create a `domain/` directory with entities, value objects, and repository interfaces
2. Move business logic out of controllers/services into domain entities
3. Create repository interfaces in the domain layer
4. Implement repositories in the infrastructure layer
5. Domain layer must NOT import Prisma, Fastify, or any framework

## Step 4: Domain Events (Conditional)

**Only run if cross-context communication is needed.**

Add domain event publishing:

1. Define event types as constants (e.g., `entity.created`, `entity.updated`)
2. Use the transactional outbox pattern for reliable delivery
3. Events are published within `unitOfWork.execute()` — never directly
4. Define handlers for events that trigger cross-context side effects

## Step 5: Verify

Validate the DDD implementation:

- [ ] Aggregate boundaries are correct (no cross-aggregate transactions)
- [ ] Invariants are enforced within aggregates
- [ ] No domain layer leakage (domain must not depend on infrastructure)
- [ ] Repository interfaces match their implementations
- [ ] Entity factories validate business rules
- [ ] Value objects are immutable
- [ ] Tests pass, typecheck passes, lint passes

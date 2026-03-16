# SaaS Studio Stack — Future Enhancements

Issues discovered during real-world usage (CMS backend build). Tracked here for future implementation.

## High Priority

### #1 — Multi-entity scaffolding

Template only scaffolds 1 entity. Should accept a comma-separated list and generate per-entity files (routes, schemas, repository, domain entity, events) for each.
**Status**: Implemented in `scaffold.sh` — supports `ENTITIES=Article,Category:Categories,Tag` with `Name:Plural` syntax for irregular plurals.

### #3 — Foundation deps are hardcoded

`package.json.tmpl` hardcodes all 17 `workspace:*` deps. Should use `{{FOUNDATION_DEPS}}` token to include only what's needed based on the dependency graph in `manifest.yaml`.
**Status**: Implemented — `package.json.tmpl` uses `{{FOUNDATION_DEPS}}` token. Agent writes the full deps block post-scaffold for multi-line JSON.

### #10 — Broken symlinks during setup

Copying foundation packages with `cp -r` breaks `node_modules` symlinks. Use `rsync --exclude node_modules` instead.
**Status**: Documented in `/saas-microservice` skill (Phase 2, Step 4).

## Medium Priority

### #2 — No GraphQL support

Foundation only supports REST (Fastify). Adding GraphQL would require a new `graphql-factory` package parallel to `api-factory`.

### #5 — No package versioning strategy

All packages are `0.1.0`. Need a versioning strategy (independent vs lockstep) and changesets integration.

### #6 — Singleton services pattern

Some services (config, logger) should be singletons across the monorepo. Currently each service instantiates its own.

### #11 — SCAN cache missing

No caching layer in foundation. Need a `cache` package wrapping Redis with tenant-scoped key prefixing.

## Low Priority

### #4 — No i18n support

Foundation has no internationalization. Would need a `i18n` package with tenant-scoped locale management.

### #7 — No API key authentication

Only JWT auth is supported. API key auth needed for service-to-service and external integrations.

### #8 — No media upload infrastructure

No file upload handling in foundation. Need a `storage` package abstracting S3/GCS with tenant isolation.

### #9 — No public submission support

All routes require authentication. Need an `anonymous-submission` pattern for public forms (e.g., contact forms).

# Studio — Template Stacks

Studio provides pre-built template stacks for scaffolding new projects. Each stack contains production-ready code templates, configuration files, and a manifest that drives the scaffolding process.

## Concept

A **stack** is a self-contained collection of templates, code, and configuration that can be used to bootstrap a new project. Stacks are organized under `stacks/` and each has a `manifest.yaml` that describes:

- **Tokens**: Variables that get replaced during scaffolding (e.g., `{{PROJECT_NAME}}`, `{{SERVICE_PORT}}`)
- **Sections**: Ordered groups of files — either copied as-is or processed through token replacement
- **Pruning rules**: Logic for excluding unused components based on project requirements

## Available Stacks

| Stack | Description | Templates |
|-------|-------------|-----------|
| `nextjs` | Next.js website with shadcn/ui, i18n, SEO | 75 files |
| `saas` | SaaS microservice monorepo with DDD foundation | 17 packages + 4 reference services |

## Token System

Tokens are defined in `core/tokens/registry.yaml` with three namespaces:

- **universal**: Project-level tokens shared across all stacks
- **frontend**: Next.js/React-specific tokens (colors, fonts, locale)
- **backend**: Service-specific tokens (entity names, ports, database provider)

Tokens use `{{TOKEN_NAME}}` syntax in `.tmpl` files and are replaced during scaffolding.

## Manifest Format

Each stack's `manifest.yaml` must conform to `manifest.schema.yaml`. See the schema for full specification.

# Project Name — Go Microservice

## Overview

Go microservice following standard project layout conventions.

## Stack

- **Language**: Go 1.22+
- **HTTP**: `net/http` + chi router (or echo/gin)
- **Database**: PostgreSQL via `pgx` or `sqlc`
- **Config**: Environment variables via `envconfig` or `viper`
- **Testing**: `testing` package + `testify`

## Structure

```
cmd/
└── server/
    └── main.go              # Entrypoint
internal/
├── handler/                 # HTTP handlers
├── service/                 # Business logic
├── repository/              # Database access
├── model/                   # Domain models
└── middleware/               # Auth, logging, recovery
pkg/                          # Public libraries (if any)
migrations/                   # SQL migrations
```

## Commands

```bash
go run cmd/server/main.go    # Dev server
go test ./...                 # Run all tests
go build -o bin/server cmd/server/main.go  # Build
golangci-lint run            # Lint
```

## Conventions

- **Error handling**: Return errors, don't panic. Wrap with `fmt.Errorf("context: %w", err)`
- **Interfaces**: Define at point of use, not at point of implementation
- **Naming**: Short, clear names. Exported = PascalCase, unexported = camelCase
- **Testing**: Table-driven tests with `t.Run()` subtests
- **Context**: Pass `context.Context` as first parameter

## Key Patterns

- Dependency injection via constructor functions
- Repository pattern for database access
- Middleware chain for cross-cutting concerns
- Structured logging via `slog`
- Graceful shutdown with signal handling

## Crew

| Skill | When to use |
|-------|-------------|
| `/code-review` | PR review before merge |
| `/cto-review` | Architectural critique |
| `/self-review-fix-loop` | Auto-fix quality issues |
| `/api-audit` | Check API endpoint consistency |
| `/security-scan` | OWASP + dependency CVE scan |
| `/benchmark` | Compare against open-source Go patterns |
| `/changelog` | Generate release notes |

## Don't

- Don't use `init()` functions — explicit initialization in main
- Don't use global variables — inject dependencies
- Don't ignore errors — handle or propagate every error
- Don't use `interface{}` / `any` without type assertions

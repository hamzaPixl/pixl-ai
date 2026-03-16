# Go Patterns

## Project Layout

Follow the standard Go project layout:

```
cmd/           # Main applications (one directory per binary)
internal/      # Private application code (not importable)
pkg/           # Public library code (importable by other projects)
api/           # API definitions (OpenAPI, protobuf)
migrations/    # Database migrations
```

## Error Handling

- Always check and handle errors — never ignore with `_`
- Wrap errors with context: `fmt.Errorf("fetch user %s: %w", id, err)`
- Define sentinel errors with `errors.New()` for expected failure modes
- Use `errors.Is()` and `errors.As()` for error checking (not string matching)

```go
var ErrNotFound = errors.New("not found")

func FindUser(id string) (*User, error) {
    user, err := repo.Get(id)
    if err != nil {
        return nil, fmt.Errorf("find user %s: %w", id, err)
    }
    return user, nil
}
```

## Dependency Injection

Use constructor functions with interface parameters:

```go
type UserService struct {
    repo   UserRepository
    logger *slog.Logger
}

func NewUserService(repo UserRepository, logger *slog.Logger) *UserService {
    return &UserService{repo: repo, logger: logger}
}
```

Define interfaces at point of use, not at point of implementation.

## Concurrency

- Use `context.Context` for cancellation and timeouts
- Prefer channels for communication, mutexes for state protection
- Use `sync.WaitGroup` for goroutine coordination
- Use `errgroup.Group` for concurrent error-handling goroutines
- Always `defer cancel()` after `context.WithCancel/Timeout`

```go
g, ctx := errgroup.WithContext(ctx)
g.Go(func() error { return fetchA(ctx) })
g.Go(func() error { return fetchB(ctx) })
if err := g.Wait(); err != nil {
    return err
}
```

## HTTP Handlers

Use `http.Handler` interface pattern:

```go
func (s *Server) handleCreateUser() http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        var input CreateUserRequest
        if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
            http.Error(w, "invalid request", http.StatusBadRequest)
            return
        }
        // ...
    }
}
```

## Testing

- Table-driven tests with `t.Run()` subtests
- Use `testify/assert` or `testify/require` for assertions
- Use `httptest.NewServer` for HTTP testing
- Use `t.Cleanup()` for resource cleanup
- Use build tags for integration tests: `//go:build integration`

```go
func TestAdd(t *testing.T) {
    tests := []struct {
        name     string
        a, b     int
        expected int
    }{
        {"positive", 1, 2, 3},
        {"zero", 0, 0, 0},
        {"negative", -1, -2, -3},
    }
    for _, tc := range tests {
        t.Run(tc.name, func(t *testing.T) {
            got := Add(tc.a, tc.b)
            assert.Equal(t, tc.expected, got)
        })
    }
}
```

## Logging

Use `slog` (structured logging, stdlib since Go 1.21):

```go
logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
logger.Info("user created", "user_id", user.ID, "email", user.Email)
```

## Configuration

- Use environment variables (12-factor app)
- Parse with `envconfig` or `viper`
- Validate required config at startup, fail fast
- Use struct tags for config binding

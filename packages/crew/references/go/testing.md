# Go Testing

## Framework

Use the standard `testing` package. Complement with:
- `testify/assert` — expressive assertions
- `testify/require` — assertions that stop the test on failure
- `testify/mock` — mock generation
- `httptest` — HTTP handler testing
- `testcontainers-go` — integration tests with real databases

## Table-Driven Tests

The idiomatic Go testing pattern:

```go
func TestParseStatus(t *testing.T) {
    tests := []struct {
        name    string
        input   string
        want    Status
        wantErr bool
    }{
        {"valid active", "active", StatusActive, false},
        {"valid inactive", "inactive", StatusInactive, false},
        {"invalid", "unknown", 0, true},
        {"empty", "", 0, true},
    }
    for _, tc := range tests {
        t.Run(tc.name, func(t *testing.T) {
            got, err := ParseStatus(tc.input)
            if tc.wantErr {
                require.Error(t, err)
                return
            }
            require.NoError(t, err)
            assert.Equal(t, tc.want, got)
        })
    }
}
```

## Integration Tests

Use build tags to separate integration tests:

```go
//go:build integration

func TestUserRepository_Create(t *testing.T) {
    db := setupTestDB(t)
    repo := NewUserRepository(db)
    // ...
}
```

Run with: `go test -tags=integration ./...`

## HTTP Testing

```go
func TestHandler(t *testing.T) {
    srv := httptest.NewServer(router())
    defer srv.Close()

    resp, err := http.Get(srv.URL + "/api/users")
    require.NoError(t, err)
    assert.Equal(t, http.StatusOK, resp.StatusCode)
}
```

## Coverage

```bash
go test -coverprofile=coverage.out ./...
go tool cover -html=coverage.out -o coverage.html
```

## Benchmarks

```go
func BenchmarkParse(b *testing.B) {
    for i := 0; i < b.N; i++ {
        Parse(testInput)
    }
}
```

Run with: `go test -bench=. -benchmem ./...`

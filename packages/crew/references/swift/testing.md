# Swift Testing

## Framework

Use **Swift Testing** (`import Testing`) for new tests. Use `@Test` and `#expect`:

```swift
@Test("User creation validates email")
func userCreationValidatesEmail() throws {
    #expect(throws: ValidationError.invalidEmail) {
        try User(email: "not-an-email")
    }
}
```

## Test Isolation

Each test gets a fresh instance — set up in `init`, tear down in `deinit`. No shared mutable state between tests.

## Parameterized Tests

```swift
@Test("Validates formats", arguments: ["json", "xml", "csv"])
func validatesFormat(format: String) throws {
    let parser = try Parser(format: format)
    #expect(parser.isValid)
}
```

## Protocol-Based DI for Testing

Abstract external dependencies behind protocols:

1. Define small, focused protocols (`FileAccessorProviding`, `NetworkProviding`)
2. Create default (production) implementations
3. Create mock implementations with configurable error properties
4. Inject via default parameters — production uses defaults, tests inject mocks

```swift
final class MockFileAccessor: FileAccessorProviding, @unchecked Sendable {
    var files: [URL: Data] = [:]
    var readError: Error?
    // ...
}
```

## Coverage

```bash
swift test --enable-code-coverage
```

## XCTest (Legacy)

For existing XCTest suites, follow standard `setUp`/`tearDown` patterns. Migrate to Swift Testing for new tests.

## Anti-Patterns

- Using `#if DEBUG` instead of proper dependency injection
- Mocking internal types that have no external dependencies
- Forgetting `Sendable` conformance when testing actor-based code
- Over-engineering: simple types don't need protocol abstractions

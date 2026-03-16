# Swift Coding Style

## Formatting

- **SwiftFormat** for auto-formatting, **SwiftLint** for style enforcement
- `swift-format` is bundled with Xcode 16+ as an alternative

## Immutability

- Prefer `let` over `var` — define everything as `let` and only change to `var` if the compiler requires it
- Use `struct` with value semantics by default; use `class` only when identity or reference semantics are needed

## Naming

Follow [Apple API Design Guidelines](https://www.swift.org/documentation/api-design-guidelines/):

- Clarity at the point of use — omit needless words
- Name methods and properties for their roles, not their types
- Use `static let` for constants over global constants
- Protocols: use `-able`, `-ible`, or `-ing` suffix for capabilities (e.g., `Sendable`, `Identifiable`)

## Error Handling

Use typed throws (Swift 6+) and pattern matching:

```swift
func load(id: String) throws(LoadError) -> Item {
    guard let data = try? read(from: path) else {
        throw .fileNotFound(id)
    }
    return try decode(data)
}
```

Prefer `Result<T, E>` for async operations that need explicit error handling.

## Concurrency

Enable Swift 6 strict concurrency checking. Prefer:

- `Sendable` value types for data crossing isolation boundaries
- Actors for shared mutable state
- Structured concurrency (`async let`, `TaskGroup`) over unstructured `Task {}`
- `@MainActor` for UI-related code

## Value Types

- Use structs for data models and DTOs
- Use enums with associated values for distinct states:

```swift
enum LoadState<T: Sendable>: Sendable {
    case idle, loading, loaded(T), failed(Error)
}
```

## Protocol-Oriented Design

- Define small, focused protocols (single responsibility)
- Use protocol extensions for shared defaults
- Mark protocols as `Sendable` when used across actor boundaries

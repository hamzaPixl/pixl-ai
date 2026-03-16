---
paths:
  - "**/*.swift"
  - "**/Package.swift"
---
# Swift Coding Style Rules

## Formatting

- Use SwiftFormat or swift-format (Xcode 16+) for auto-formatting
- Use SwiftLint for style enforcement

## Immutability

- Prefer `let` over `var` — only use `var` when the compiler requires reassignment
- Use `struct` by default; use `class` only for identity/reference semantics

## Naming

- Follow Apple API Design Guidelines
- Clarity at point of use — omit needless words
- Protocols: `-able`, `-ible`, `-ing` suffixes for capabilities

## Error Handling

- Use typed throws (Swift 6+): `throws(MyError)`
- Use `guard let` for early returns
- Never force-unwrap optionals in production code

## Concurrency

- Enable Swift 6 strict concurrency checking
- Prefer `Sendable` value types, actors for shared mutable state
- Use structured concurrency (`async let`, `TaskGroup`) over `Task {}`
- Use `@concurrent` only for CPU-intensive work — profile first

## SwiftUI

- Use `@Observable` (not `ObservableObject`) for view models
- Use `@Environment` (not `@EnvironmentObject`)
- Extract subviews to limit re-render scope
- Use `.task {}` for async work in views

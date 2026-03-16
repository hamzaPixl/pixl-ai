---
name: swift-patterns
description: "SwiftUI patterns, Swift 6.2 concurrency, actor persistence, and protocol-oriented DI. Use when building iOS/macOS apps, working with SwiftUI, implementing Swift concurrency, or writing testable Swift code."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
argument-hint: "<topic: swiftui|concurrency|actors|testing|all>"
---

# Swift Patterns

Comprehensive Swift development patterns covering SwiftUI, concurrency, persistence, and testing.

## Topics

### `swiftui` — SwiftUI Architecture

**State Management:**
- Use `@Observable` (not `ObservableObject`) — tracks property-level changes
- `@State` for view-local values, `@Binding` for parent references
- `@Environment` replaces `@EnvironmentObject`
- `@Bindable` for two-way binding to `@Observable` properties

**View Composition:**
- Extract subviews to limit re-render scope
- Use `ViewModifier` for reusable styling
- Use `#Preview` macro with mock data

**Navigation:**
- `NavigationStack` + `NavigationPath` for type-safe routing
- Centralize routes in a `Router` `@Observable` class
- Use `Destination` enum with associated values

**Performance:**
- `LazyVStack`/`LazyHStack` for large collections
- Stable identifiers in `ForEach` (never array indices)
- Use `.task {}` for async work (auto-cancels on disappear)
- Conform expensive views to `Equatable`

### `concurrency` — Swift 6.2 Approachable Concurrency

**Core principle:** Code runs single-threaded by default. Concurrency is opt-in.

- Async functions stay on the calling actor (no implicit offloading)
- Use `@concurrent` for explicit background work on CPU-intensive tasks
- Isolated conformances: `extension Type: @MainActor Protocol`
- MainActor inference mode reduces `@MainActor` annotations
- Protect globals with `@MainActor`

**Migration:**
1. Enable in Xcode Build Settings → Concurrency
2. Start with MainActor defaults for app targets
3. Add `@concurrent` only where profiling shows bottlenecks
4. Use isolated conformances instead of `nonisolated` workarounds

### `actors` — Actor-Based Persistence

**Pattern:** Actor + in-memory cache + file-backed storage

```swift
public actor LocalRepository<T: Codable & Identifiable> where T.ID == String {
    private var cache: [String: T] = [:]
    private let fileURL: URL
    // O(1) reads from cache, atomic writes to file
}
```

- Compiler-enforced thread safety (no locks)
- Synchronous init loading
- `.atomic` file writes
- Combine with `@Observable` ViewModels

### `testing` — Protocol-Based DI + Swift Testing

**Pattern:** Small focused protocols → default implementations → mock implementations → inject via default parameters

```swift
protocol FileAccessorProviding: Sendable { ... }
struct DefaultFileAccessor: FileAccessorProviding { ... }
final class MockFileAccessor: FileAccessorProviding { ... }

actor SyncManager {
    init(fileAccessor: FileAccessorProviding = DefaultFileAccessor()) { ... }
}
```

**Swift Testing framework:**
- `@Test("description")` with `#expect`
- Parameterized tests with `arguments:`
- Each test gets fresh instance (no shared state)
- `swift test --enable-code-coverage`

## References

- See `references/swift/coding-style.md` for naming and style
- See `references/swift/concurrency.md` for detailed concurrency patterns
- See `references/swift/testing.md` for testing patterns
- See `.claude/rules/swift/coding-style.md` for enforced rules

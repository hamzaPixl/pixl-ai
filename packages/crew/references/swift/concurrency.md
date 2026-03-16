# Swift Concurrency (6.2)

## Core Principle

Swift 6.2 Approachable Concurrency: code runs **single-threaded by default**. Concurrency is introduced explicitly with `@concurrent`.

## Key Changes from Swift 6.1

| Swift 6.1 Behavior | Swift 6.2 Behavior |
|---|---|
| Async functions could offload to background threads | Async stays on calling actor by default |
| `@MainActor` annotations required everywhere | MainActor inference mode (opt-in) |
| Protocol conformance on @MainActor types was hard | Isolated conformances: `extension T: @MainActor P` |
| Global/static state needed manual synchronization | Protected by MainActor inference |

## Patterns

### Isolated Conformances

MainActor types can safely conform to non-isolated protocols:

```swift
extension StickerModel: @MainActor Exportable {
    func export() {
        photoProcessor.exportAsPNG()
    }
}
```

### @concurrent for Background Work

Only use for CPU-intensive operations:

```swift
nonisolated final class PhotoProcessor {
    @concurrent
    static func extractSubject(from data: Data) async -> Sticker { /* ... */ }
}
```

Steps: (1) Mark containing type `nonisolated`, (2) Add `@concurrent`, (3) Add `async`, (4) `await` at call sites.

### MainActor Default Inference

Opt-in mode where MainActor is inferred for app targets:

```swift
// No @MainActor needed — inferred
final class StickerLibrary {
    static let shared: StickerLibrary = .init()
}
```

## Migration

1. Enable in Xcode Build Settings → Concurrency
2. Enable in SPM via `SwiftSettings`
3. Start with MainActor defaults for app targets
4. Add `@concurrent` where profiling shows bottlenecks
5. Use isolated conformances instead of `nonisolated` workarounds

## Best Practices

- Start on MainActor — single-threaded first, optimize later
- Profile before offloading — use Instruments to find real bottlenecks
- Protect globals with MainActor
- Use `Sendable` value types for data crossing actor boundaries
- Migrate incrementally — enable features one at a time

## Anti-Patterns

- Applying `@concurrent` to everything (most code doesn't need parallelism)
- Using `nonisolated` to suppress compiler errors without understanding
- Keeping legacy `DispatchQueue` when actors provide the same safety
- Assuming async = background (Swift 6.2: async stays on calling actor)

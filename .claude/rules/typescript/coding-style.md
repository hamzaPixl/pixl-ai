---
paths:
  - "**/*.ts"
  - "**/*.tsx"
---
# TypeScript Coding Style Rules

## Strict Mode

- Enable `strict: true` in tsconfig.json — never disable individual strict checks
- Use `noUncheckedIndexedAccess` for array/object safety

## Types

- Prefer `interface` for object shapes, `type` for unions/intersections/computed types
- Avoid `any` — use `unknown` when type is truly unknown, then narrow
- Use `as const` for literal types and `satisfies` for type-safe object literals
- Export types explicitly: `export type { MyType }` (not bundled with runtime exports)

## Enums

- Prefer union types over enums: `type Status = 'active' | 'inactive'`
- If using enums, use `const enum` for zero-runtime-cost or string enums for debuggability

## Generics

- Name generics descriptively when not obvious: `TItem`, `TResult` (not just `T`, `U`)
- Constrain generics: `<T extends Record<string, unknown>>` over bare `<T>`

## Null Handling

- Use optional chaining `?.` and nullish coalescing `??`
- Avoid non-null assertions `!` — narrow the type instead
- Use `undefined` over `null` unless interfacing with external APIs that use `null`

## Async

- Always use `async/await` over raw Promises
- Handle errors with try/catch at boundaries, not on every call
- Use `Promise.all()` for independent async operations
- Never use `void` promises without error handling — at minimum catch and log

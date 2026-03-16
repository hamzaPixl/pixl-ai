# Coding Style

## Immutability

- Prefer `const` over `let` — only use `let` when reassignment is necessary
- Use `readonly` for class properties that shouldn't change after construction
- Prefer immutable data transformations (map, filter, reduce) over mutation
- Use `Object.freeze()` for configuration objects

## Naming

- Files: `kebab-case.ts` for modules, `PascalCase.tsx` for React components
- Variables/functions: `camelCase`
- Classes/types/interfaces: `PascalCase`
- Constants: `UPPER_SNAKE_CASE` for true constants, `camelCase` for derived values
- Booleans: prefix with `is`, `has`, `can`, `should` (e.g., `isLoading`, `hasPermission`)
- Event handlers: prefix with `handle` (e.g., `handleClick`, `handleSubmit`)

## File Size

- Source files should stay under 300 lines — split when exceeding
- Functions should stay under 50 lines — extract helpers when growing
- One component/class per file

## Error Handling

- Use typed errors, not string messages
- Catch at boundaries (API routes, event handlers), not in utility functions
- Never swallow errors silently — at minimum, log them
- Use `Result<T, E>` patterns over try/catch when error handling is part of the contract

## Imports

- Group imports: external packages → internal modules → relative imports → types
- Use named exports over default exports (better refactoring support)
- Avoid barrel files (`index.ts` re-exports) in large projects — they hurt tree-shaking

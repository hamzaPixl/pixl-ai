# React Performance

Key performance rules for React/Next.js applications, organized by impact.

## Critical — Eliminating Waterfalls

- Move `await` into the branch where the value is actually used
- Use `Promise.all()` for independent async operations
- Start promises early, await late in API route handlers
- Use Suspense boundaries to stream content progressively
- Compose server components to fetch data in parallel

## Critical — Bundle Size

- Import directly from modules — avoid barrel files (`index.ts` re-exports)
- Use `next/dynamic` for heavy components not needed at initial load
- Load analytics and tracking scripts after hydration
- Conditionally import modules only when needed
- Preload resources on hover/focus for perceived performance

## High — Server-Side Optimization

- Use `React.cache()` for per-request data deduplication
- Use LRU cache for cross-request caching of stable data
- Minimize data serialized from server to client components
- Use `after()` for non-blocking operations (logging, analytics)

## Medium-High — Client-Side Data

- Use SWR or React Query for automatic request deduplication
- Deduplicate global event listeners (resize, scroll)
- Use passive event listeners for scroll handlers
- Version localStorage data and minimize stored payloads

## Medium — Re-render Prevention

- Don't subscribe to state that's only used in callbacks
- Memoize components that receive complex props
- Use primitive values as effect dependencies
- Subscribe to derived booleans instead of entire objects
- Use functional `setState` when next state depends on previous
- Use lazy state initialization for expensive defaults
- Use `startTransition` for non-urgent UI updates

## Medium — Rendering Optimization

- Animate wrapper `<div>` elements, not SVG directly
- Use `content-visibility: auto` for long lists
- Hoist static JSX outside component functions
- Reduce SVG coordinate precision (2-3 decimal places)
- Use inline `<script>` for hydration flicker prevention (e.g., dark mode)
- Use ternary (`? :`) not `&&` for conditional rendering

## Low-Medium — JavaScript Patterns

- Batch CSS changes via classes or `cssText`, not individual properties
- Use `Map` with index keys for repeated lookups
- Cache property access and function results in tight loops
- Combine `filter` + `map` into a single `reduce` or loop
- Check `.length` before expensive string/array comparisons
- Use early return to avoid unnecessary computation
- Hoist `RegExp` construction outside loops
- Use `Set` or `Map` for O(1) lookups instead of array `.includes()`

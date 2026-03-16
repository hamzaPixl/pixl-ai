# Performance

## Measure Before Optimizing

- Profile first — never optimize based on assumptions
- Use browser DevTools, Instruments (Swift), py-spy, or node --prof
- Benchmark with realistic data volumes, not toy examples
- Set performance budgets: page load < 3s, API response < 200ms, bundle < 200KB

## Database

- Add indexes for columns used in WHERE, JOIN, and ORDER BY
- Avoid N+1 queries — use eager loading or batch queries
- Paginate all list endpoints — never return unbounded results
- Use connection pooling in production

## Frontend

- Lazy-load routes and heavy components
- Use `useMemo`/`useCallback` only when profiling shows re-render cost
- Optimize images: WebP/AVIF, proper sizing, lazy loading
- Minimize bundle size: tree-shake, code-split, analyze with bundle analyzer

## API

- Use pagination (cursor-based for large datasets, offset for small)
- Cache expensive computations and slow external API calls
- Use streaming for large responses
- Set appropriate HTTP cache headers

## General

- Prefer O(n) or better algorithms for hot paths
- Avoid premature optimization — readability > micro-performance
- Use async/parallel execution for independent I/O operations
- Don't optimize code that runs rarely — focus on hot paths

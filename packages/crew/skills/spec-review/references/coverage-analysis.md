# Coverage Analysis

Strategies for scanning a codebase to determine requirement implementation status.

## Scanning Strategy

### 1. Search Hint Execution

For each requirement's `search_hints[]`:

1. **Grep for code patterns**: Use Grep with each hint as a pattern
   - Search in source directories only (exclude `node_modules`, `dist`, `.next`, `__pycache__`)
   - Use case-insensitive matching for flexibility
   - Capture file path, line number, and matching text

2. **Glob for file patterns**: Use Glob for path-based hints
   - `**/auth/signup*` for path hints like "auth/signup"
   - Check both source and test directories

3. **Score evidence quality**:
   - **Strong**: Function/class definition matching the hint
   - **Medium**: Import/usage of a matching function
   - **Weak**: Comment or string literal mentioning the pattern

### 2. Acceptance Criteria Matching

For each acceptance criterion within a requirement:

1. Generate sub-patterns from the criterion text
2. Search for each sub-pattern
3. A requirement is `implemented` only if ALL criteria have at least medium-strength evidence
4. A requirement is `partial` if SOME criteria have evidence
5. A requirement is `missing` if NO criteria have evidence

### 3. Parallel Scanning for Large Codebases

When there are >20 requirements:

1. Group requirements into batches of 5-10
2. Launch parallel Explore agents, one per batch
3. Each agent receives its batch of requirements + search hints
4. Collect results and merge

Agent prompt template:
```
Search the codebase for evidence of these requirements being implemented.
For each requirement, search using the provided hints and classify as
implemented/partial/missing. Return structured JSON results.

Requirements:
[batch of 5-10 requirements with search_hints]
```

### 4. Extra Detection (Scope Creep)

After scanning for known requirements:

1. Identify major code modules/directories not referenced by any requirement
2. Look for feature flags, TODO comments mentioning unplanned work
3. Check recent git history for commits not linked to any requirement ID
4. Flag these as `extra` — potential scope creep or undocumented features

### 5. Evidence Quality Assessment

| Evidence Type | Strength | Example |
|--------------|----------|---------|
| Function/class definition | Strong | `async function signUp()` |
| Route handler | Strong | `router.post('/auth/signup')` |
| Test file with matching describe/it | Strong | `describe('signup')` |
| Import statement | Medium | `import { signUp } from './auth'` |
| Configuration entry | Medium | `SIGNUP_ENABLED: true` |
| Comment or TODO | Weak | `// TODO: implement signup` |
| String literal | Weak | `'signup'` in a constants file |

### 6. Coverage Calculation

```
implemented_count = requirements with status "implemented"
partial_count = requirements with status "partial"
total_count = total requirements (excluding constraints)

coverage_percentage = (implemented_count + 0.5 * partial_count) / total_count * 100
```

Constraints are excluded from coverage calculation since they describe boundaries, not implementations. However, they should still be verified (e.g., "must use PostgreSQL" → check for Prisma/pg dependency).

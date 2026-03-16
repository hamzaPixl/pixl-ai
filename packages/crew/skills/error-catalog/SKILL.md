---
name: error-catalog
description: "Scan a service for thrown errors, catch blocks, error classes, HTTP status codes, and validation patterns. Produce a unified error catalog with codes, messages, and HTTP mappings. Detect inconsistencies and generate base error classes if missing. Use when asked to catalog errors, standardize error handling, create error codes, or audit error responses."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
argument-hint: "<optional: path to service directory>"
---

## Overview

Error catalog pipeline: discovery → scan → catalog → inconsistency detection → generation. Produces a unified error reference and optionally generates standardized error infrastructure.

## Step 1: Discovery

1. **Language/framework detection**:
   - Check `package.json` for Node.js/TypeScript (Fastify, Express, NestJS)
   - Check `pyproject.toml`/`requirements.txt` for Python (FastAPI, Django, Flask)
   - Check for existing error infrastructure: `errors/`, `exceptions/`, `error-codes`
2. **Scope**:
   - If argument provided, scope to that directory
   - Otherwise, scan the entire service `src/` or project root

## Step 2: Error Pattern Scan

Scan for all error-related patterns:

### TypeScript/JavaScript
```bash
# Thrown errors
grep -rn "throw new" --include="*.ts" --include="*.js"
# Custom error classes
grep -rn "extends Error" --include="*.ts" --include="*.js"
# HTTP status codes
grep -rn "reply\.\(code\|status\)\|res\.status\|HttpStatus\|statusCode" --include="*.ts"
# Validation errors (Zod, Joi, class-validator)
grep -rn "ZodError\|ValidationError\|BadRequest" --include="*.ts"
# Fastify error handlers
grep -rn "setErrorHandler\|onError" --include="*.ts"
# Try-catch blocks
grep -rn "catch\s*(" --include="*.ts"
```

### Python
```bash
# Raised exceptions
grep -rn "raise " --include="*.py"
# Custom exception classes
grep -rn "class.*Exception\|class.*Error" --include="*.py"
# HTTP exceptions (FastAPI)
grep -rn "HTTPException\|status_code" --include="*.py"
# Validation (Pydantic)
grep -rn "ValidationError\|ValueError" --include="*.py"
```

## Step 3: Catalog Construction

For each discovered error, extract:

| Field | Source |
|-------|--------|
| Error class/type | Class name or thrown type |
| Error code | String code if present (e.g., `"AUTH_EXPIRED"`) |
| HTTP status | Status code mapping |
| Message template | Error message string |
| Location | File:line where thrown |
| Context | What triggers this error |

Build the catalog as a markdown table:

```markdown
## Error Catalog

| Code | HTTP | Message | Class | Location | Context |
|------|------|---------|-------|----------|---------|
| AUTH_001 | 401 | Token expired | AuthError | src/auth/guard.ts:45 | JWT validation |
| ... | ... | ... | ... | ... | ... |
```

## Step 4: Inconsistency Detection

Flag the following issues:

1. **Missing error codes**: Errors thrown without a code identifier
2. **Inconsistent HTTP status mapping**: Same error type returning different status codes
3. **Bare throws**: `throw new Error("message")` without custom error class
4. **Swallowed errors**: Empty catch blocks or catch blocks without re-throw/logging
5. **Inconsistent error format**: Some errors return `{ error: ... }` vs `{ message: ... }`
6. **Missing error handling**: Routes without try-catch or error middleware
7. **Duplicate messages**: Same message used for different error conditions
8. **Missing client-safe messages**: Errors that leak internal details (stack traces, SQL)

## Step 5: Output

### Error Catalog Report

Output the full catalog with inconsistency analysis:

```markdown
# Error Catalog — {service-name}

## Summary
- Total error patterns found: N
- Unique error codes: N
- HTTP status codes used: [list]
- Inconsistencies found: N

## Catalog
[table from Step 3]

## Inconsistencies
[findings from Step 4 with severity]

## Recommendations
1. [Specific actionable fixes]
```

### Optional: Generate Error Infrastructure

If the user confirms or requests it, generate:

1. **Base error class** with code, HTTP status, and client-safe message
2. **Error code enum/constants** from the catalog
3. **Error handler middleware** that maps errors to consistent responses
4. **Error response type** (Zod schema or Pydantic model)

Follow the existing code patterns in the project. Do NOT generate if infrastructure already exists — instead recommend specific improvements.

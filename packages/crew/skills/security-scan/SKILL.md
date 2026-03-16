---
name: security-scan
description: "Automated security scanning: secrets detection, OWASP Top 10 checks, dependency CVEs, and RBAC audit. Use when asked to scan for vulnerabilities, audit security, check for leaked secrets, or review dependencies for CVEs."
allowed-tools: Read, Bash, Glob, Grep, Agent
argument-hint: "<scope: secrets|owasp|deps|rbac|full> [path]"
---

# Security Scan

Automated security scanning across multiple dimensions.

## Required References

Before starting, read `references/standards/security-audit.md` for OWASP patterns and severity classification.

## Step 0: Parse Scope

| Scope       | What it checks                                    |
| ----------- | ------------------------------------------------- |
| `secrets`   | Hardcoded API keys, passwords, private keys       |
| `owasp`     | OWASP Top 10 vulnerability patterns               |
| `deps`      | Dependency CVEs via npm audit / pip audit          |
| `rbac`      | Authorization checks on routes and endpoints      |
| `full`      | All of the above                                  |

Default scope: `full`. Optional `path` restricts scanning to a subdirectory.

## Step 1: Secrets Scan

Search for common secret patterns:

```bash
# API keys
grep -rn 'sk_live_\|sk_test_\|AKIA[A-Z0-9]\|ghp_\|gho_\|xox[bpas]-' --include='*.ts' --include='*.js' --include='*.py' --include='*.go' .

# Private keys
grep -rn 'BEGIN.*PRIVATE KEY' .

# Hardcoded passwords
grep -rn 'password\s*=\s*["\x27][^"\x27]*["\x27]' --include='*.ts' --include='*.js' --include='*.py' .

# .env files committed
git ls-files | grep -E '\.env($|\.local|\.prod|\.staging)'
```

Severity: **CRITICAL** for any finding.

## Step 2: OWASP Top 10

Scan for common vulnerability patterns:

| OWASP             | Pattern to grep                                      |
| ----------------- | ---------------------------------------------------- |
| **SQL Injection** | String concatenation in SQL queries                  |
| **XSS**           | `dangerouslySetInnerHTML`, unescaped template vars   |
| **SSRF**          | User-controlled URLs in fetch/axios calls            |
| **Broken Auth**   | Missing auth middleware on routes                    |
| **Insecure CORS** | `origin: '*'` or `credentials: true` with wildcard  |
| **Path Traversal**| `../` in file operations with user input             |
| **Hardcoded JWT** | JWT secrets as string literals                       |

Use Grep to search for each pattern. Report file, line, and severity.

## Step 3: Dependency Audit

```bash
# Node.js
npm audit --json 2>/dev/null || npx audit-ci 2>/dev/null

# Python
pip audit 2>/dev/null || safety check 2>/dev/null

# Go
govulncheck ./... 2>/dev/null
```

Parse output and report:
- Critical/High vulnerabilities (must fix)
- Medium vulnerabilities (should fix)
- Low vulnerabilities (track)

## Step 4: RBAC Audit

1. Find all route definitions (Express/Fastify/FastAPI)
2. Check each route for auth middleware/decorator
3. Flag routes without authorization checks
4. Check for privilege escalation paths (user accessing admin routes)

## Step 5: Report

Output a structured security report:

```markdown
# Security Scan Report
Date: <timestamp>
Scope: <scope>
Path: <path>

## Summary
| Category | Critical | High | Medium | Low |
|----------|----------|------|--------|-----|
| Secrets  | ...      | ...  | ...    | ... |
| OWASP    | ...      | ...  | ...    | ... |
| Deps     | ...      | ...  | ...    | ... |
| RBAC     | ...      | ...  | ...    | ... |

## Critical Findings
<list with file:line, description, remediation>

## Recommendations
<prioritized list of fixes>
```

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

## Gotchas

- `.env` files in git history are still leaked even if currently gitignored — always check `git log --all --diff-filter=A -- '*.env*'` for past commits that added secrets
- `npm audit` reports may include false positives from dev dependencies — filter with `npm audit --omit=dev` to focus on production dependency vulnerabilities
- RBAC checks must happen server-side — client-side role checks (hiding UI elements, conditional rendering) are trivially bypassed and provide zero security
- Regex-based secret detection has high false positive rates — validate each finding before reporting as CRITICAL (e.g., test keys, example placeholders, base64 data that resembles tokens)
- Container images may contain secrets baked into intermediate layers — use multi-stage builds to ensure build-time secrets (npm tokens, API keys for private registries) never appear in the final image

## Helper Scripts

- `scripts/scan-secrets.sh [path]` — grep-based secret detection, run before full scan
- `scripts/scan-owasp.sh [path]` — OWASP Top 10 pattern scan for quick triage

## Data Logging

After completing a scan, append a summary record to persist trend data:

```bash
DATA_DIR="${CLAUDE_PLUGIN_DATA:-${HOME}/.pixl/plugin-data}/security-scan"
mkdir -p "$DATA_DIR"
cat >> "$DATA_DIR/scan-history.jsonl" <<EOF
{"date":"$(date -u +%Y-%m-%dT%H:%M:%SZ)","project":"$(basename $(pwd))","findings_critical":0,"findings_high":0,"findings_medium":0,"scope":"full"}
EOF
```

Replace the `0` values with actual counts from the scan. This enables trend analysis across sessions.

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

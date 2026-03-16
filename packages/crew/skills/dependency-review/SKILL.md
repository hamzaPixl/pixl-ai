---
name: dependency-review
description: "Audit project dependencies for outdated packages, known CVEs, breaking changes, license issues, and unused packages. Supports npm/yarn/pnpm, pip/poetry, and Go modules. Use when asked to review dependencies, check for vulnerabilities, update packages, or audit licenses."
allowed-tools: Read, Bash, Glob, Grep
argument-hint: "<optional: specific package name or path to lockfile>"
---

## Overview

Dependency review pipeline: discovery → vulnerability scan → outdated check → license audit → unused detection → report. Read-only analysis that produces an actionable report.

## Required References

Before starting, read `references/standards/security-audit.md` for CVE severity classification and dependency risk assessment patterns.

## Step 1: Discovery

1. **Package manager detection**:
   - `package.json` + `package-lock.json` → npm
   - `package.json` + `yarn.lock` → yarn
   - `package.json` + `pnpm-lock.yaml` → pnpm
   - `package.json` + `bun.lockb` → bun
   - `pyproject.toml` or `requirements.txt` → pip/poetry
   - `go.mod` → Go modules
2. **Dependency inventory**:
   - Count production vs dev dependencies
   - Identify monorepo structure (workspaces)
   - Check for multiple lockfiles (inconsistency risk)

## Step 2: Vulnerability Scan

Run the appropriate audit command:

```bash
# npm
npm audit --json 2>/dev/null || true

# yarn
yarn audit --json 2>/dev/null || true

# pnpm
pnpm audit --json 2>/dev/null || true

# pip
pip audit --format json 2>/dev/null || true
# or if pip-audit not available:
# Check against GitHub Advisory Database via grep
```

Parse results and categorize:
- **Critical**: Remote code execution, SQL injection, auth bypass
- **High**: XSS, SSRF, path traversal
- **Medium**: DoS, information disclosure
- **Low**: Minor issues, theoretical attacks

## Step 3: Outdated Check

```bash
# npm
npm outdated --json 2>/dev/null || true

# pip
pip list --outdated --format json 2>/dev/null || true
```

Categorize updates:
- **Major** (breaking): Requires migration work
- **Minor** (feature): Safe to update, review changelog
- **Patch** (fix): Safe to update immediately

Flag dependencies more than 2 major versions behind.

## Step 4: License Audit

1. Check licenses of all production dependencies:
   ```bash
   # npm — check package.json of each dep
   npx license-checker --json 2>/dev/null || true
   ```
2. Flag problematic licenses:
   - **GPL/AGPL** in a commercial project (copyleft risk)
   - **UNLICENSED** or missing license
   - **Custom/proprietary** licenses
3. Check for license compatibility with project license

## Step 5: Unused Detection

1. **JavaScript/TypeScript**:
   - Grep imports across all source files
   - Compare against `dependencies` in `package.json`
   - Flag packages in `dependencies` but never imported
2. **Python**:
   - Grep imports across all `.py` files
   - Compare against declared dependencies
3. Also check for:
   - Packages only used in scripts (should be devDependencies)
   - Packages duplicated across workspaces

## Step 6: Report

```markdown
## Dependency Review — {project-name}

### Summary
| Metric | Count |
|--------|-------|
| Total dependencies | N |
| Production | N |
| Dev | N |
| Vulnerabilities | N (C critical, H high, M medium, L low) |
| Outdated | N (N major, N minor, N patch) |
| License issues | N |
| Unused | N |

### 🔴 Vulnerabilities
| Package | Severity | CVE | Description | Fix |
|---------|----------|-----|-------------|-----|
| ... | ... | ... | ... | ... |

### 📦 Major Updates Available
| Package | Current | Latest | Breaking Changes |
|---------|---------|--------|-----------------|
| ... | ... | ... | ... |

### ⚖️ License Issues
| Package | License | Risk |
|---------|---------|------|
| ... | ... | ... |

### 🗑️ Potentially Unused
| Package | Last Import Found | Recommendation |
|---------|-------------------|----------------|
| ... | None | Remove |

### Recommended Actions (priority order)
1. ...
```

---
name: deploy-verify
description: "Post-merge deploy verification: wait for deployment, run canary checks (page load, console errors, content verification), and auto-revert on failure. Use when verifying a deployment, running post-merge checks, or when asked to verify production after shipping."
allowed-tools: Read, Bash, Glob, Grep
argument-hint: "<url> [--pr <number>] [--revert]"
---

## Overview

Release engineer workflow that verifies a deployment after merge. Runs canary checks on the live site and triggers revert if critical failures are detected.

**How this differs from other skills**:
- `/ship-milestone` — end-to-end shipping (build → test → commit → push). This skill runs AFTER merge/deploy.
- `/code-review` — pre-merge review. This skill is post-merge verification.
- `/runbook` — incident response. This skill is proactive verification to prevent incidents.

## Step 1: Determine Target

Parse arguments to identify what to verify:

- **URL provided**: Use directly as the canary target
- **PR provided**: `gh pr view <number> --json mergedAt,headRefName,baseRefName` to confirm merge, then determine deploy URL
- **Neither**: Check for deploy URL in config:
  - `.env` or `.env.production` → `DEPLOY_URL`, `PRODUCTION_URL`, `BASE_URL`
  - `vercel.json` → project URL
  - `wrangler.jsonc` → workers URL

If no URL can be determined, ask the user.

## Step 2: Wait for Deploy

If a PR was just merged, the deploy may be in progress:

```bash
# GitHub Actions: check deploy workflow status
gh run list --branch main --limit 5 --json status,conclusion,name,createdAt

# Wait for running deploy (poll every 30s, max 10 min)
gh run watch $(gh run list --branch main --limit 1 --json databaseId -q '.[0].databaseId') --exit-status
```

If no CI deploy is detected, assume the deployment is already live.

## Step 3: Canary Checks

Run these checks against the target URL. Each check produces a pass/fail result.

### Check 1: Page Load (Critical)

```bash
# HTTP status check
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$URL" --max-time 10)
# Should be 200

# Response time
RESPONSE_TIME=$(curl -s -o /dev/null -w "%{time_total}" "$URL" --max-time 10)
# Should be < 3.0 seconds
```

**Pass**: HTTP 200 AND response time < 3s
**Fail**: Non-200 status OR response time > 5s
**Warn**: Response time 3-5s

### Check 2: Key Content Verification

Verify critical content is present on the page:

```bash
# Fetch page content
PAGE_CONTENT=$(curl -s "$URL" --max-time 10)

# Check for error indicators
echo "$PAGE_CONTENT" | grep -qi "500\|internal server error\|application error\|503\|502"
# Should NOT match

# Check for expected content (if known)
echo "$PAGE_CONTENT" | grep -qi "<title>"
# Should match — page has a title
```

### Check 3: API Health (if applicable)

```bash
# Health endpoint
curl -s "$URL/health" --max-time 5 | jq '.status'
# or
curl -s "$URL/api/health" --max-time 5 | jq '.status'
```

### Check 4: Console Errors (via curl headers)

```bash
# Check for CSP violations or server errors in headers
curl -sI "$URL" --max-time 10 | grep -i "x-error\|x-debug\|server-error"
# Should NOT match
```

### Check 5: SSL Certificate

```bash
# Verify SSL is valid and not expiring soon
curl -sI "https://${DOMAIN}" --max-time 10 2>&1 | head -1
# Check for SSL errors
```

## Step 4: Report Results

```
Deploy Verification: https://example.com
========================================
PR: #123 (merged 5 min ago)
Deploy: GitHub Actions (completed)

  [PASS] Page Load:     200 OK, 0.8s response time
  [PASS] Content:       No error pages, title present
  [PASS] API Health:    /health returns {"status":"ok"}
  [WARN] Response Time: 2.8s (close to 3s threshold)
  [PASS] SSL:           Valid, expires in 45 days

Result: DEPLOY VERIFIED (4 pass, 1 warn, 0 fail)
```

## Step 5: Handle Failures

### On Critical Failure (page down, 500 errors)

If `--revert` flag is set:
```bash
# Revert the merge commit
git revert HEAD --no-edit
git push origin main
echo "REVERTED: Deploy verification failed — merge commit reverted"
```

If `--revert` is NOT set:
```
CRITICAL FAILURE: Deploy verification found issues.
Recommended actions:
1. Run /runbook <service> for incident diagnosis
2. Revert with: git revert HEAD && git push origin main
3. Or hotfix and re-deploy

Do you want to auto-revert? (This will revert the last merge commit)
```

### On Warnings

Report warnings but do not revert. Suggest monitoring for the next 15 minutes.

## Gotchas

- Auto-revert only works if the last commit on main is the merge — check `git log -1` before reverting
- Some deploys take >10 minutes (Docker builds, CDN invalidation) — adjust wait time accordingly
- Health endpoints may return 200 even when the app is partially broken — verify actual content
- SSL checks fail on localhost/development — skip for non-HTTPS URLs
- Rate limiting may block rapid curl checks — add 1s delay between checks
- Never auto-revert without the `--revert` flag — always ask first by default

# Security

> See also: `references/standards/security-audit.md` for OWASP audit checklists and vulnerability severity classification.

## Input Validation

- Validate at system boundaries: API routes, form handlers, webhook receivers
- Use schema validation (Zod, Pydantic, joi) — not manual checks
- Reject unknown fields (`strict` mode) to prevent mass assignment
- Sanitize HTML output to prevent XSS — use framework escaping, not manual regex

## Authentication & Authorization

- Never store passwords in plaintext — use bcrypt/argon2 with proper cost factors
- Use short-lived JWTs (15 min) + refresh tokens (7 days)
- Check authorization on every request — don't rely on frontend guards alone
- Use RBAC or ABAC — not role strings scattered in route handlers

## Secrets Management

- Never commit secrets to git — use `.env` files (gitignored) or secret managers
- Rotate API keys and tokens regularly
- Use different keys for dev/staging/prod
- Scan for leaked secrets in pre-commit hooks

## OWASP Top 10 Awareness

- **Injection** — Use parameterized queries, never string concatenation for SQL/commands
- **Broken auth** — Rate limit login attempts, use MFA for admin accounts
- **Sensitive data exposure** — Encrypt at rest and in transit, minimize data collection
- **SSRF** — Validate and allowlist outbound URLs
- **Security misconfiguration** — Remove default credentials, disable debug in production

## Dependencies

- Run `npm audit` / `pip audit` regularly
- Pin major versions, allow patch updates
- Review new dependencies before adding — check maintenance, popularity, security history
- Prefer well-maintained packages over rolling your own crypto/auth

# Security Audit Checklist

## OWASP Top 10 (2021) Quick Reference

### A01: Broken Access Control
- [ ] All routes require authentication
- [ ] Authorization checks on every endpoint (permission guards)
- [ ] No IDOR vulnerabilities (user can't access other users' data)
- [ ] Rate limiting on sensitive endpoints

### A02: Cryptographic Failures
- [ ] Passwords hashed with argon2/bcrypt (never MD5/SHA)
- [ ] JWT secrets are strong and from environment variables
- [ ] TLS enforced in production
- [ ] No sensitive data in logs

### A03: Injection
- [ ] Parameterized queries (Prisma handles this by default)
- [ ] Input validation with Zod on all request bodies
- [ ] No dynamic SQL construction
- [ ] XSS prevention (React escapes by default, but check dangerouslySetInnerHTML)

### A04: Insecure Design
- [ ] Threat model exists for critical flows
- [ ] Rate limiting on authentication endpoints
- [ ] Account lockout after failed attempts
- [ ] CORS configured restrictively (not `*` in production)

### A05: Security Misconfiguration
- [ ] No default credentials
- [ ] Error messages don't leak stack traces in production
- [ ] Unnecessary HTTP methods disabled
- [ ] Security headers set (Helmet)

### A06: Vulnerable Components
- [ ] Dependencies scanned for known CVEs
- [ ] No unmaintained packages in critical paths
- [ ] Lock files committed

### A07: Authentication Failures
- [ ] Strong password requirements
- [ ] JWT expiration and refresh token rotation
- [ ] Session invalidation on password change

### A08: Data Integrity Failures
- [ ] Signed tokens (JWT) for stateless auth
- [ ] Audit log for all mutations
- [ ] Transactional outbox for event integrity

### A09: Logging Failures
- [ ] Authentication events logged
- [ ] Authorization failures logged
- [ ] Sensitive data redacted from logs (passwords, tokens)

### A10: SSRF
- [ ] No user-controlled URL fetching without validation
- [ ] Internal network not accessible from user input

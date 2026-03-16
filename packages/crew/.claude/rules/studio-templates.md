---
paths: studio/**/*.tmpl
---

# Studio Template Rules

- Use `{{TOKEN_NAME}}` syntax for all replaceable values — no hardcoded project-specific values
- Token names must be UPPER_SNAKE_CASE (e.g. `{{PROJECT_NAME}}`, `{{PORT}}`)
- Templates are processed by `scripts/scaffold.sh` — test with `grep -r '{{' <file>` to verify all tokens
- Never include real credentials, API keys, or environment-specific URLs in templates

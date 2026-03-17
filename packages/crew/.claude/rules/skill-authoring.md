---
paths: skills/**/SKILL.md
---

# Skill Authoring Rules

- YAML frontmatter is required with: `name`, `description`
- `allowed-tools` should list only tools the skill actually needs
- `argument-hint` provides usage hint shown to the user (e.g., `<url>`)
- Skill body should be under 500 lines — split into referenced files if longer
- Description must be specific enough to trigger reliably from natural language

## Skill Configuration (config.json)

For skills that repeatedly ask the same discovery questions (framework preference, locale, threshold values), add a `config.json` to the skill directory:

```json
{
  "$schema": "../../schemas/skill-config.schema.json",
  "description": "User defaults for /skill-name",
  "settings": {
    "setting_name": {
      "description": "What this controls",
      "type": "string|number|boolean|array",
      "enum": ["option1", "option2"],
      "default": "value"
    }
  }
}
```

### When to add config.json

- The skill asks 2+ discovery questions that rarely change between invocations
- The answers are project-wide (not per-invocation)
- Examples: framework preference, test coverage threshold, scan severity level, locale list

### How the skill uses it

At the start of the skill body, instruct Claude to:

1. Check if `config.json` exists in the skill directory
2. Load defaults from it
3. Allow argument-level overrides to take precedence
4. Skip the discovery question if a default is set

### Skills with config.json

- `/test-writer` — framework, coverage_threshold, style
- `/security-scan` — scan_scope, severity_threshold, skip_modules
- `/i18n-setup` — locales, default_locale, library
- `/website` — framework, styling, component_library, package_manager
- `/code-review` — confidence_threshold, post_comments, reviewers

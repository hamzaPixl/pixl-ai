---
paths: skills/**/SKILL.md
---

# Skill Authoring Rules

- YAML frontmatter is required with: `name`, `description`
- `allowed-tools` should list only tools the skill actually needs
- `argument-hint` provides usage hint shown to the user (e.g., `<url>`)
- Skill body should be under 500 lines — split into referenced files if longer
- Description must be specific enough to trigger reliably from natural language

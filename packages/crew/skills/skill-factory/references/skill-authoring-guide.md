# Skill Authoring Guide

Comprehensive guide for writing high-quality Claude Code skills. Extracted from the skill-development and skill-creator methodologies.

## Anatomy of a Skill

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter metadata (required)
│   │   ├── name: (required)
│   │   └── description: (required)
│   └── Markdown instructions (required)
└── Bundled Resources (optional)
    ├── scripts/          - Executable code (Python/Bash/etc.)
    ├── references/       - Documentation loaded into context as needed
    └── assets/           - Files used in output (templates, icons, fonts, etc.)
```

### Resource Types

- **Scripts** — For tasks requiring deterministic reliability or repeatedly rewritten code. Token efficient, may be executed without loading into context.
- **References** — Documentation Claude should reference while working (schemas, API docs, domain knowledge). Keeps SKILL.md lean; loaded only when needed. If files are large (>10k words), include grep search patterns in SKILL.md. Avoid duplicating content between SKILL.md and references.
- **Assets** — Files used in final output (templates, images, boilerplate). Not loaded into context, copied or modified directly.

## Progressive Disclosure

Skills use a three-level loading system:

1. **Metadata (name + description)** — Always in context (~100 words)
2. **SKILL.md body** — When skill triggers (<5k words)
3. **Bundled resources** — As needed by Claude (unlimited — scripts can execute without reading into context)

## Writing Style

Write using **imperative/infinitive form** (verb-first instructions), not second person. Use objective, instructional language (e.g., "To accomplish X, do Y" rather than "You should do X").

## Description Quality

Use third-person format with specific trigger phrases:

```yaml
# Good — third person, specific trigger phrases, concrete scenarios:
description: "This skill should be used when the user asks to 'create a hook', 'add a PreToolUse hook', or mentions hook events (PreToolUse, PostToolUse, Stop)."

# Bad — wrong person, vague, no triggers:
description: "Use this skill when working with hooks."
```

## SKILL.md Body

Answer these questions:

1. What is the purpose of the skill, in a few sentences?
2. When should the skill be used? (reflected in frontmatter description with specific triggers)
3. How should Claude use the skill? All reusable resources should be referenced.

**Keep SKILL.md lean:** Target 1,500-2,000 words. Move detailed content to references/:

- Detailed patterns → `references/patterns.md`
- Advanced techniques → `references/advanced.md`
- API references → `references/api-reference.md`

## Common Warnings

- Weak triggers ("Provides guidance for X") will not reliably activate the skill — include exact user phrases
- Bloated SKILL.md (>3,000 words) wastes context — move details to references/
- Second-person writing ("You should...") breaks style consistency — use imperative form
- Unreferenced resources are invisible to Claude — always reference bundled files in SKILL.md
- Missing `allowed-tools` means the skill can't use tools it needs

## Validation Checklist

- [ ] SKILL.md has valid YAML frontmatter with `name` and `description`
- [ ] Description includes specific trigger phrases in third person
- [ ] Body uses imperative/infinitive form, not second person
- [ ] SKILL.md is lean (~1,500-2,000 words), detailed content in references/
- [ ] All referenced files exist; no duplicated information across files
- [ ] Examples/scripts are complete and executable
- [ ] `allowed-tools` lists only tools the skill actually needs

## Plugin-Specific Notes

- Plugin skills live in `skills/<skill-name>/SKILL.md`
- Claude Code auto-discovers skills by scanning `skills/` for `SKILL.md` files
- No packaging needed — distributed as part of the plugin

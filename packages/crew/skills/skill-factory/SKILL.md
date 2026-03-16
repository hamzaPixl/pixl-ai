---
name: skill-factory
description: "Create, detect, or improve Claude Code skills. Three modes: (A) Create — build a new skill from a description or requirements, (B) Detect — analyze a session transcript to extract repeatable workflows and auto-generate a skill, (C) Improve — audit an existing skill against best practices and apply fixes. Use when asked to 'create a skill', 'make a skill', 'extract a skill from this session', 'improve this skill', 'audit skill quality', or 'skill-factory'."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
argument-hint: "<skill description, session transcript, or path to existing skill>"
---

## Overview

Unified skill for creating and maintaining Claude Code skills. Combines skill creation, detection from session patterns, and quality improvement into one workflow.

## Required References

Before generating or auditing, read `references/skill-authoring-guide.md` for the complete authoring guide (anatomy, progressive disclosure, writing style, validation checklist).

For the original Anthropic skill-creator methodology, see `references/skill-creator-original.md`.

## Mode Detection

- If input is a session transcript or "detect"/"extract" → **Mode B** (Detect)
- If input points to an existing skill directory or mentions "improve"/"audit" → **Mode C** (Improve)
- Otherwise → **Mode A** (Create)

---

## Mode A: Create

Build a new skill from a description or requirements.

### Step A1: Gather Requirements

Ask targeted questions (avoid overwhelming — 2-3 at a time):

1. What the skill does and when to use it
2. Concrete usage examples ("What would a user say to trigger this?")
3. Input parameters and expected output format
4. Step-by-step process

### Step A2: Plan Resources

Analyze the workflow to identify reusable resources:

- **Scripts** — Code that would be rewritten each time (e.g., `scripts/rotate_pdf.py`)
- **References** — Knowledge rediscovered each time (e.g., `references/schema.md`)
- **Assets** — Boilerplate needed each time (e.g., `assets/template/`)

### Step A3: Design

1. Define YAML frontmatter: `name`, `description` (with trigger phrases), `allowed-tools`, `argument-hint`
2. Break the workflow into numbered steps
3. Identify conditional steps and parallel execution points
4. Define what each step produces

### Step A4: Generate

1. Create the skill directory: `skills/<skill-name>/`
2. Write `SKILL.md` with frontmatter and step instructions
3. Create reference/script/asset files as needed
4. Ensure instructions are clear enough for Claude to follow autonomously

**CRITICAL:** Follow the writing style in `references/skill-authoring-guide.md` — imperative form, third-person description, specific trigger phrases.

### Step A5: Validate

Run the checklist from `references/skill-authoring-guide.md`:

- [ ] Valid YAML frontmatter with `name` and `description`
- [ ] Description includes specific trigger phrases in third person
- [ ] Body uses imperative form, not second person
- [ ] SKILL.md under 2,000 words; detailed content in references/
- [ ] All referenced files exist
- [ ] `allowed-tools` matches what steps actually need

---

## Mode B: Detect

Extract a repeatable skill from a session transcript.

### Step B1: Analyze Transcript

Identify in the session:

1. Repeatable workflow patterns (steps that would work on other inputs)
2. Decision points and branching logic
3. Tools used and their sequence
4. Input parameters and output format
5. Domain knowledge that was looked up or discovered

### Step B2: Extract Workflow

Distill the session into a generalized workflow:

1. Replace specific values with parameter placeholders
2. Separate one-time decisions from repeatable steps
3. Identify which parts are domain knowledge (→ references) vs. procedure (→ SKILL.md)

### Step B3: Generate

Follow Mode A Steps A3-A5 (Design → Generate → Validate) using the extracted workflow.

---

## Mode C: Improve

Audit an existing skill and apply fixes.

### Step C1: Read the Skill

Read the target `SKILL.md` and all files in its directory (references, scripts, assets).

### Step C2: Audit

Score each dimension (1-5):

| Dimension | What to check |
|-----------|--------------|
| **Trigger quality** | Does the description include specific user phrases? Would it reliably trigger? |
| **Clarity** | Are steps clear enough for Claude to follow autonomously? |
| **Progressive disclosure** | Is SKILL.md lean (<2,000 words)? Is detailed content in references? |
| **Writing style** | Imperative form? No second-person? |
| **Completeness** | Are all referenced files present? All tools listed? |
| **Redundancy** | Does it duplicate content from other skills or references? |

Output a quality report with scores and specific issues.

### Step C3: Fix

Apply targeted fixes for issues found:

- Strengthen weak trigger phrases
- Move bloated sections to references/
- Fix writing style violations
- Add missing tool declarations
- Remove duplicated content (delegate to source skill instead)

### Step C4: Validate

Run the full validation checklist from `references/skill-authoring-guide.md`.

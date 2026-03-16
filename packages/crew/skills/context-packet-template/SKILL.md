---
name: context-packet-template
description: "Template and utilities for creating context packets — the standard format for passing structured data between agents. Use when setting up inter-agent communication or when a skill needs to produce/consume shared context."
allowed-tools: Read, Write, Edit, Bash
argument-hint: "<packet type: design | review | architecture | custom>"
disable-model-invocation: true
---

## Overview

Provides templates, examples, and merge utilities for the context packet standard defined in `references/orchestration/context-packet.md`. Use this skill to bootstrap context packet creation in any workflow.

## Required References

Before starting, read `references/orchestration/context-packet.md` for the full schema and conventions.

## COPY THIS BLOCK — In-Prompt Pattern

When the packet is under 500 tokens and consumed by 1-2 agents, inline it directly in the agent prompt:

````markdown
## Context Packet

```json
{
  "type": "design",
  "version": "1.0",
  "metadata": { "skill": "website", "project": "PROJECT_SLUG", "created_at": "TIMESTAMP" },
  "payload": {
    "archetype": "ARCHETYPE_NAME",
    "tokens": { ... },
    "variants": { ... },
    "content": { ... },
    "constraints": [ ... ]
  }
}
`` `
```
````

## COPY THIS BLOCK — File-Based Pattern

When the packet exceeds 500 tokens or 3+ agents need the same data, write to `.context/`:

```bash
mkdir -p .context
cat > .context/design-tokens.json << 'PACKET'
{
  "type": "design",
  "version": "1.0",
  "metadata": { "skill": "website", "project": "PROJECT_SLUG", "created_at": "TIMESTAMP" },
  "payload": {
    "archetype": "ARCHETYPE_NAME",
    "tokens": { ... },
    "variants": { ... },
    "content": { ... },
    "constraints": [ ... ]
  }
}
PACKET
```

Then instruct each agent: "Read `.context/design-tokens.json` for design system context."

## Merging Parallel Packets

When multiple agents produce packets, merge them:

```bash
bash skills/context-packet-template/scripts/merge-context.sh packet-a.json packet-b.json > merged.json
```

See `references/orchestration/context-packet.md` for merge precedence rules.

## Step 1: Determine Packet Type

Choose from: `design`, `review`, `architecture`, `custom`.

## Step 2: Fill Payload

Use the example in `references/context-packet-example.json` as a starting point. Fill all required fields for the chosen type.

## Step 3: Decide Delivery

Apply the decision guide from the reference doc:

- Under 500 tokens and 1-2 consumers: inline in prompt
- Over 500 tokens or 3+ consumers: write to `.context/` file

## Step 4: Validate

Verify the packet has all required fields: `type`, `version`, `metadata.skill`, `metadata.project`, `metadata.created_at`, `payload`.

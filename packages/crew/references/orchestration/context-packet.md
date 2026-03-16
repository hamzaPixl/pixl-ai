# Context Packet Standard

Standard format for passing structured context between agents during parallel execution. Builds on the Agent Context Template from `references/methodology/parallel-execution.md`.

## JSON Schema

Every context packet conforms to this schema:

```json
{
  "type": "design | review | architecture | custom",
  "version": "1.0",
  "metadata": {
    "skill": "website",
    "project": "acme-landing",
    "created_at": "2026-02-26T10:00:00Z"
  },
  "payload": {}
}
```

**Fields:**

| Field                 | Type     | Required | Description                                                 |
| --------------------- | -------- | -------- | ----------------------------------------------------------- |
| `type`                | enum     | yes      | Discriminator: `design`, `review`, `architecture`, `custom` |
| `version`             | string   | yes      | Schema version, currently `"1.0"`                           |
| `metadata.skill`      | string   | yes      | Skill that produced this packet                             |
| `metadata.project`    | string   | yes      | Project slug                                                |
| `metadata.created_at` | ISO 8601 | yes      | Creation timestamp                                          |
| `payload`             | object   | yes      | Type-specific content (see formats below)                   |

## Discovery Output Format (type: design)

Produced by design/discovery phases. Consumed by implementation agents.

```json
{
  "type": "design",
  "version": "1.0",
  "metadata": {
    "skill": "website",
    "project": "acme-landing",
    "created_at": "..."
  },
  "payload": {
    "archetype": "minimal",
    "tokens": {
      "colors": {
        "primary_hsl": "217 91% 60%",
        "secondary_hsl": "187 70% 50%"
      },
      "typography": { "font_sans": "Inter", "heading_font": "serif" },
      "shape": { "border_radius": "6px" },
      "shadows": { "sm": "none", "md": "0 1px 2px rgba(0,0,0,0.04)" },
      "motion": { "duration_micro": "150ms", "ease": "[0.25, 0.1, 0.25, 1]" },
      "layout": { "section_padding": "py-16 sm:py-20", "max_width": "6xl" }
    },
    "variants": {
      "hero": "split",
      "nav": "bar",
      "footer": "4-column",
      "features": "alternating-rows"
    },
    "content": {
      "hero_headline": "Build faster with Acme",
      "hero_subhead": "The platform for modern teams"
    },
    "constraints": [
      "WCAG 2.1 AA contrast ratios",
      "Use CSS variables for shadows, durations, easing"
    ]
  }
}
```

## Implementation Input Format (type: architecture)

Produced by architecture phases. Consumed by scaffolding and build agents.

```json
{
  "type": "architecture",
  "version": "1.0",
  "metadata": {
    "skill": "fullstack-app",
    "project": "acme-app",
    "created_at": "..."
  },
  "payload": {
    "component_tree": ["app/layout.tsx", "app/page.tsx", "components/nav.tsx"],
    "api_contract": {
      "endpoints": [
        { "method": "GET", "path": "/api/users", "response": "User[]" }
      ],
      "error_format": "{ error: { code, message } }"
    },
    "decisions": [
      { "decision": "REST over tRPC", "rationale": "Simpler client generation" }
    ],
    "tech_stack": {
      "frontend": "Next.js",
      "backend": "Fastify",
      "db": "PostgreSQL"
    }
  }
}
```

## Review Findings Format (type: review)

Produced by review agents. Consumed by fixer agents.

```json
{
  "type": "review",
  "version": "1.0",
  "metadata": {
    "skill": "self-review-fix-loop",
    "project": "acme-app",
    "created_at": "..."
  },
  "payload": {
    "findings": [
      {
        "severity": "P0",
        "file": "src/api/users.ts",
        "description": "Missing auth check on DELETE endpoint",
        "fix_direction": "Add requirePermission guard before handler",
        "evidence": "Line 42: router.delete('/users/:id', handler) has no guard"
      }
    ]
  }
}
```

## File-Based Handoff Convention

Write packets to the `.context/` directory in the project root when they meet the file threshold (see Decision Guide below).

| File                                  | Contents                                 | Producer               | Consumer                |
| ------------------------------------- | ---------------------------------------- | ---------------------- | ----------------------- |
| `.context/design-tokens.json`         | Design system packet (type: design)      | Discovery/design phase | Build agents            |
| `.context/task-plan.md`               | Task decomposition in markdown           | Planning phase         | All agents              |
| `.context/architecture.md`            | Component tree, decisions, API contract  | Architecture phase     | Build agents            |
| `.context/review-findings.json`       | Review findings (type: review)           | Review agents          | Fixer agents            |
| `.context/api-contract.json`          | API contract packet (type: architecture) | Architecture phase     | Frontend/backend agents |
| `.context/review-findings-final.json` | Archived final review state              | Verify phase           | Audit trail             |

Add `.context/` to `.gitignore`. These files are ephemeral build artifacts.

## Merge Protocol for Parallel Discovery

When multiple agents produce packets in parallel, merge with field-level precedence:

1. **Last-write wins** for scalar fields within the same `type`.
2. **Array union** for list fields (`findings`, `constraints`, `endpoints`) -- concatenate, then deduplicate by identity key (`file` + `description` for findings, `method` + `path` for endpoints).
3. **Conflict resolution** for contradictory scalars (e.g., two agents set different `archetype`):
   - If a coordinator agent exists, it decides.
   - Otherwise, the agent with narrower scope (more specific skill) wins.
4. **Metadata**: use the latest `created_at`, preserve the original `skill` as an array if merged across skills.

Merge command (simple overlay):

```bash
jq -s '.[0] * .[1]' packet-a.json packet-b.json > merged.json
```

For array union with dedup, use the merge script in `skills/context-packet-template/scripts/merge-context.sh`.

## Decision Guide: Files vs Inline Strings

| Criterion      | Inline (in prompt)    | File (in `.context/`)    |
| -------------- | --------------------- | ------------------------ |
| Token count    | < 500 tokens          | >= 500 tokens            |
| Consumer count | 1-2 agents            | 3+ agents need same data |
| Mutability     | Read-once, no updates | Updated across phases    |
| Persistence    | Ephemeral within run  | Needed across iterations |

**Rule of thumb:** If the packet exceeds 500 tokens OR 3+ agents need the same data, write it to a `.context/` file. Otherwise, inline it in the agent prompt.

## Relationship to Parallel Execution

This standard extends the Agent Context Template from `references/methodology/parallel-execution.md`. The template provides the per-agent dispatch format (files to modify, boundaries, success criteria). Context packets provide the **shared data** that populates the "complete context" field in that template.

Workflow:

1. Discovery/design phase produces a context packet.
2. Coordinator reads the packet and builds per-agent prompts using the Agent Context Template.
3. Each agent receives its template with the relevant packet payload inlined or as a file reference.
4. Agents write output packets for downstream phases.

# Phase Handoff Protocol

Rules for transitioning between phases in the `/website-project` pipeline. Every phase boundary has a completion checklist, output validation, and gate condition that must pass before the next phase begins.

---

## Phase Completion Checklists

### Phase 1: Discovery

- [ ] Agent A (design extraction) returned a complete design token set with all fields populated
- [ ] Agent B (task plan) returned an ordered task list with acceptance criteria
- [ ] Agent C (reference analysis) returned a section inventory with content patterns
- [ ] All three outputs have been merged into a single `discovery_packet`
- [ ] The packet has been slimmed (no raw HTML, no screenshots, no verbose logs)
- [ ] The packet has been written to `.context/discovery-packet.json`

### Phase 2: Architecture

- [ ] Component tree includes every section identified in the discovery packet
- [ ] Every section is mapped to exactly one file path
- [ ] Implementation groups have zero file overlap
- [ ] Page structure defines section ordering for every page
- [ ] Shared components (nav, footer) are identified with their build wave
- [ ] Token gaps are either resolved or explicitly accepted with defaults
- [ ] The `architecture_packet` has been written to `.context/architecture-packet.json`

### Phase 3: Implementation

- [ ] All files in every implementation group have been created
- [ ] Each file exports a valid React component
- [ ] `npx tsc --noEmit` passes with zero errors
- [ ] All sections are imported into the page file in the correct order
- [ ] Nav and footer are integrated into the layout
- [ ] SEO metadata, sitemap, and robots.txt are in place
- [ ] `npm run build` succeeds
- [ ] The `implementation_packet` has been written to `.context/implementation-packet.json`

### Phase 4: Quality

- [ ] Self-review-fix-loop completed with no P0 or P1 findings remaining
- [ ] Tech-lead has issued a final verdict
- [ ] If REQUEST_CHANGES: changes have been made and re-reviewed (max 2 rounds)
- [ ] Final `npx tsc --noEmit` passes
- [ ] Final `npm run build` passes

---

## Output Validation Rules

Each agent output is validated before it is accepted into the context packet.

### Design Extraction Output

| Field                 | Validation Rule                                  |
| --------------------- | ------------------------------------------------ |
| `archetype`           | Must be one of the 12 recognized archetype names |
| `colors.*_hsl`        | Must match pattern `\d+ \d+% \d+%`               |
| `typography.font_*`   | Must be a non-empty string                       |
| `shape.border_radius` | Must end with `px`                               |
| `shadows.*`           | Must be a valid CSS box-shadow value or `"none"` |
| `motion.duration_*`   | Must end with `ms`                               |
| `motion.ease`         | Must be a JSON array of 4 numbers                |
| `variants.*`          | Must be a non-empty string (variant name)        |

### Task Plan Output

| Field                         | Validation Rule                              |
| ----------------------------- | -------------------------------------------- |
| `items`                       | Must be a non-empty array                    |
| `items[].id`                  | Must be unique across all items              |
| `items[].title`               | Must be a non-empty string                   |
| `items[].agent_role`          | Must be a recognized agent role name         |
| `items[].acceptance_criteria` | Must be a non-empty array of strings         |
| `parallel_groups`             | Each task_id must reference an existing item |

### Reference Analysis Output

| Field              | Validation Rule                                         |
| ------------------ | ------------------------------------------------------- |
| `sections`         | Must be a non-empty array                               |
| `sections[].name`  | Must be a non-empty string                              |
| `sections[].order` | Must be a non-negative integer, unique within the array |
| `nav_structure`    | Must be a non-empty string                              |
| `content_tone`     | Must be a non-empty string                              |

### Architecture Output

| Field                        | Validation Rule                                          |
| ---------------------------- | -------------------------------------------------------- |
| `component_tree`             | Must be a non-empty array                                |
| `component_tree[].file_path` | Must be a valid relative path ending in `.tsx`           |
| `page_structure`             | Must have at least one page                              |
| `page_structure[].sections`  | Must be a non-empty array, ordered by `.order`           |
| `implementation_groups`      | No file path may appear in more than one group           |
| `implementation_groups`      | Every section file_path must appear in exactly one group |

---

## Retry Policy

| Failure Type                                       | Action                                                             | Max Retries |
| -------------------------------------------------- | ------------------------------------------------------------------ | ----------- |
| Agent returns empty or malformed output            | Re-spawn the same agent with the same input                        | 1           |
| Agent returns partial output (some fields missing) | Re-spawn with specific feedback about missing fields               | 1           |
| Validation fails on assembled packet               | Fix the specific validation error in the orchestrator, re-validate | 2           |
| Phase gate fails                                   | Return output to the responsible agent with gate failure details   | 2           |
| Build failure (`tsc` or `npm run build`)           | Identify breaking file, re-delegate to owning agent with error     | 3           |
| Tech-lead REQUEST_CHANGES                          | Route feedback to responsible agent, re-submit for review          | 2           |

### Partial Failure Handling

If one of the 3 Phase 1 agents fails and retry also fails:

- **Design extraction fails:** The orchestrator must manually define design tokens using the archetype mapping from `references/frontend/design-archetypes.md`. This is the most critical output — do not proceed without design tokens.
- **Task plan fails:** The orchestrator can derive a basic task list from the reference analysis sections. Quality will be lower but the pipeline can continue.
- **Reference analysis fails:** The orchestrator can proceed with design tokens and task plan alone. Section ordering will fall back to the archetype's default section pattern from `references/frontend/sector-design-intelligence.md`.

Never proceed to Phase 2 with zero successful Phase 1 outputs.

---

## Gate Conditions Table

| Gate          | Condition                                       | On Failure                                              |
| ------------- | ----------------------------------------------- | ------------------------------------------------------- |
| Phase 1 exit  | At least 2 of 3 agents returned valid output    | Retry failed agent once; if still fails, proceed with 2 |
| Phase 1 exit  | Design tokens output is present and valid       | BLOCK — cannot proceed without design tokens            |
| Phase 2 exit  | Zero file overlap in implementation groups      | Return to architect with overlap details                |
| Phase 2 exit  | Every section has a file path assignment        | Return to architect with missing sections list          |
| Phase 3 exit  | `npx tsc --noEmit` passes                       | Identify breaking files, re-delegate to owning agents   |
| Phase 3 exit  | `npm run build` passes                          | Identify errors, re-delegate to owning agents           |
| Phase 3 exit  | All sections rendered in correct page order     | Orchestrator fixes import order in page file            |
| Phase 4 exit  | No P0/P1 findings from self-review              | Continue review-fix loop (up to 3 iterations)           |
| Phase 4 exit  | Tech-lead verdict is APPROVE                    | Route changes to agents (max 2 rounds), then escalate   |
| Pipeline exit | All 4 phase gates passed + final build succeeds | Escalate to user with status report                     |

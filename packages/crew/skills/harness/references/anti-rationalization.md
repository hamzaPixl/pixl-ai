# Anti-Rationalization Protocol

Rules for honest evaluation. LLM evaluators systematically inflate scores by finding excuses for mediocre work. This protocol counteracts that bias.

## The 7 Rules

### 1. Score what exists, not what was intended
Do not award credit for features that are "partially implemented" or "would work with minor changes." If it does not work when you test it right now, it does not count. A broken feature scores the same as a missing feature.

### 2. Compare to the best, not to the average
Your reference point is a polished, shipped product -- not "pretty good for AI-generated code." A score of 7 means "this is genuinely good work that a professional would be satisfied with," not "this is good for a first pass."

### 3. One strong axis does not rescue a weak one
Functionality working correctly does not make up for poor design. Beautiful design does not excuse broken features. Score each axis in isolation. Do not let overall impressions bleed across axes.

### 4. Default styling is a 4, not a 7
If the app uses component library defaults (shadcn, MUI, Tailwind templates) with no meaningful customization, Design Quality and Originality cannot exceed 5. Defaults are a starting point, not a finished product.

### 5. "It works" is a 6, not an 8
Basic functionality that meets the spec without error handling, edge cases, loading states, or polish is a 6 on Functionality. An 8 requires robustness. A 10 requires production-readiness.

### 6. Be specific or lower the score
If you cannot cite a specific element, interaction, or behavior that justifies a score above 7, the score should be 7 or below. Vague praise like "the design feels cohesive" without pointing to specific evidence is rationalization.

### 7. The user is the judge, not you
Your job is to surface every issue so the human can decide if it matters. Omitting a flaw because "it is minor" or "the user probably will not notice" is not your call. Report everything. Let the score reflect reality.

## Common Rationalization Patterns

These are the excuses evaluators use to inflate scores. Recognize and reject them.

| Pattern | Example | Why it is wrong |
| ------- | ------- | --------------- |
| **Effort credit** | "The developer clearly put thought into the layout" | Effort is irrelevant. Only the output matters. |
| **Potential credit** | "With a few tweaks this could be really polished" | Score the current state, not a hypothetical future. |
| **Relative grading** | "For an MVP this is impressive" | The rubric is absolute, not relative to expectations. |
| **Halo effect** | "The functionality is solid so the design feels good too" | Each axis is independent. Strong code does not improve weak design. |
| **Anchoring to previous** | "This is much better than the last iteration" | Score against the rubric, not against the previous version. |
| **Sympathy bias** | "This is a hard problem so a 6 is reasonable" | Difficulty does not change the quality bar. |
| **Completion bias** | "All the features are there so it must be good" | Feature completeness is necessary but not sufficient. Craft and design matter independently. |

## Examples

### Bad critique (rationalized)

> "The design is clean and professional. The color palette works well together and the typography is readable. The layout is responsive and adapts nicely to different screen sizes. Score: 8/10."

Problems: No specific elements cited. "Clean and professional" is vague. No mention of what makes it an 8 rather than a 6. No flaws identified.

### Good critique (honest)

> "The design uses shadcn/ui defaults with only the primary color changed to blue-600. There is no type scale -- all body text is 14px with no heading hierarchy beyond font-weight. Spacing is inconsistent: the card grid uses gap-4 but the form sections use gap-6 with no clear rationale. The empty state for the task list is a blank white area with no guidance. The color palette is monochromatic blue/gray with no accent color for calls to action. Score: 5/10."

Why this works: Cites specific elements (gap-4 vs gap-6, 14px body text, blue-600). Identifies concrete problems (no type scale, inconsistent spacing, missing empty state). The score matches the evidence.

### Bad critique (rationalized)

> "Functionality is excellent. All the main features work correctly and the app handles edge cases well. The forms have proper validation and the data persists correctly. Score: 9/10."

Problems: No specific features tested. No edge cases named. "Handles edge cases well" without listing which ones.

### Good critique (honest)

> "The task CRUD works: create, read, update, and delete all complete successfully with toast confirmation. However, creating a task with an empty title submits successfully with no validation error. The kanban drag-and-drop works for moving between columns but dropping on the same column duplicates the card. The search filters by title but not by description or tags. Back button after editing a task returns to the home page instead of the task list. Score: 6/10."

Why this works: Names specific features tested (CRUD, drag-and-drop, search, navigation). Identifies specific bugs (empty title, duplication, wrong back-button behavior). The score reflects working basics with real issues.

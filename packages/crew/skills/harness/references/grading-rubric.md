# Grading Rubric

4-axis evaluation framework for generated applications. Each axis is scored independently on a 1-10 scale. The evaluator must provide a score AND specific evidence for each axis.

## Score Descriptors

| Range | Label       | Meaning                                                    |
| ----- | ----------- | ---------------------------------------------------------- |
| 1-3   | Poor        | Fundamentally broken or missing. Unacceptable for any use. |
| 4-5   | Mediocre    | Functional but generic, lazy, or clearly AI-generated.     |
| 6-7   | Good        | Solid work with minor issues. Meets expectations.          |
| 8-9   | Great       | Exceeds expectations. Distinctive, polished, professional. |
| 10    | Exceptional | Best-in-class. Could ship as a premium product today.      |

## Axis 1: Design Quality

Visual hierarchy, spacing, typography, color, and layout.

**Scoring criteria:**

- **1-3**: No visual hierarchy. Default browser styling or broken layouts. Text is hard to read. Colors clash or are absent. No spacing system.
- **4-5**: Generic template look. Spacing is inconsistent. Typography is default sans-serif with no scale. Colors are safe but uninspired (stock blue/gray). Layout works but feels like a Bootstrap tutorial.
- **6-7**: Clear visual hierarchy. Consistent spacing rhythm. Intentional typography with size/weight contrast. Cohesive color palette. Responsive layout that works on mobile.
- **8-9**: Strong spatial design. Typography creates mood and guides the eye. Color palette is distinctive and supports the brand/purpose. Whitespace is used deliberately. Animations enhance rather than distract.
- **10**: Museum-quality visual design. Every pixel is intentional. The design itself communicates the product's values. Could win a design award.

**What to inspect:**
- Heading/body type contrast and scale
- Consistent padding/margin rhythm (4px or 8px grid)
- Color palette coherence (not just random hex values)
- Alignment and grid discipline
- Empty states, loading states, error states

## Axis 2: Originality

Distinctiveness and avoidance of generic, template, or "AI slop" aesthetics.

**Scoring criteria:**

- **1-3**: Obvious template or boilerplate. Looks like every other AI-generated app. Uses default component library styling with zero customization. Hero section with stock gradient.
- **4-5**: Some customization but still recognizably template-based. Generic illustrations or placeholder content. "SaaS landing page starter kit" energy.
- **6-7**: Clear design identity. Custom color choices, intentional layout decisions. Would not be immediately recognized as AI-generated. Some unique UI patterns or interactions.
- **8-9**: Distinctive and memorable. Custom design language. Unique interactions or visual metaphors. Shows creative problem-solving in the UI. Would stand out in a portfolio.
- **10**: Genuinely novel. Introduces new interaction patterns or visual approaches. Could inspire other designers. Has a clear, ownable aesthetic.

**What to inspect:**
- Does it look like a shadcn/ui default theme with zero changes?
- Are there any custom design decisions (not just config tweaks)?
- Would you remember this app after seeing 10 others?
- Are illustrations/icons generic stock or purposeful?
- Does the layout break any conventions in a good way?

## Axis 3: Craft

Attention to detail, polish, micro-interactions, and handling of edge cases.

**Scoring criteria:**

- **1-3**: Rough edges everywhere. Broken hover states. Missing focus indicators. No loading feedback. Console errors. Misaligned elements. Lorem ipsum still present.
- **4-5**: Basic functionality works but feels unfinished. Hover states exist but are default. No transitions or animations. Error messages are generic ("Something went wrong"). Empty states show nothing.
- **6-7**: Smooth transitions between states. Proper loading indicators. Meaningful error messages. Hover and focus states are styled. Forms have validation feedback. Empty states have helpful content.
- **8-9**: Delightful micro-interactions (subtle hover effects, smooth page transitions, skeleton loaders). Keyboard navigation works. Toast notifications for async actions. Optimistic UI updates. Dark mode if appropriate.
- **10**: Every interaction feels intentional and polished. Animations follow physics-based easing. Accessibility is thorough (ARIA labels, focus trapping in modals, screen reader tested). Performance is optimized (no layout shifts, instant navigation).

**What to inspect:**
- Hover, focus, and active states on all interactive elements
- Loading states (skeleton, spinner, progress bar)
- Error states (inline validation, toast, full-page)
- Empty states (first-use experience)
- Transition/animation quality (easing, duration, purpose)
- Keyboard navigation (tab order, focus rings, escape to close)
- Console errors or warnings

## Axis 4: Functionality

Features work correctly, data flows are complete, and the app is usable.

**Scoring criteria:**

- **1-3**: Core features are broken or missing. Buttons do nothing. Navigation is broken. Data is not persisted. App crashes on basic usage.
- **4-5**: Core happy path works but edge cases break. Forms submit but validation is missing. Navigation works but back button behavior is wrong. Data persists but there is no feedback.
- **6-7**: All specified features work correctly. Forms validate and provide feedback. Navigation is consistent. Data operations (CRUD) are complete. Responsive on mobile.
- **8-9**: Features work robustly. Handles concurrent operations. Proper optimistic updates. URL state reflects app state (deep-linkable). Works offline or degrades gracefully. Search, filtering, and sorting work on large datasets.
- **10**: Production-ready functionality. Rate limiting, input sanitization, proper auth flows. Real-time updates where appropriate. Undo/redo support. Import/export. Comprehensive keyboard shortcuts.

**What to inspect:**
- Does each specified feature actually work end-to-end?
- What happens with empty inputs, long strings, special characters?
- Does the back button work correctly?
- Is form validation present and helpful?
- Do CRUD operations complete with appropriate feedback?
- Is the app responsive (test at 375px, 768px, 1440px)?

## Evaluation Protocol

1. Read the harness spec (`harness-spec.md`) to understand what was requested
2. Launch the application and interact with every feature
3. Score each axis independently -- do not let a high score on one axis inflate another
4. For each axis, cite specific evidence (element names, screenshots, behaviors observed)
5. Write actionable feedback: "The submit button has no loading state" not "Could be more polished"
6. Apply the anti-rationalization protocol (see `anti-rationalization.md`)

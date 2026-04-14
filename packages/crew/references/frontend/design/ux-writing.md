---
title: UX Writing
domain: frontend/design
source: adapted from impeccable (github.com/pbakaus/impeccable, Apache-2.0)
---

# UX Writing

Every word earns its place. Voice stays constant; tone adapts to the moment.

## The Button Label Problem

Never use "OK", "Submit", or "Yes / No". They are lazy and ambiguous. Use **verb + object**:

| Lazy | Clear | Why |
|------|-------|-----|
| OK | Save changes | Says what happens |
| Submit | Create account | Outcome-focused |
| Yes | Delete message | Confirms the action |
| Cancel | Keep editing | Clarifies the outcome of cancel |
| Click here | Download PDF | Describes the destination |

For destructive actions, name the destruction:

- "Delete" (permanent), not "Remove" (implies recoverable).
- "Delete 5 items", not "Delete selected" — show the count.

## Error Messages: The Formula

Every error answers three questions: (1) What happened? (2) Why? (3) How to fix it?

"Email address is not valid. Please include an @ symbol." beats "Invalid input."

### Templates

| Situation | Template |
|-----------|----------|
| Format error | "[Field] needs to be [format]. Example: [example]" |
| Missing required | "Please enter [what is missing]" |
| Permission denied | "You do not have access to [thing]. [What to do instead]" |
| Network error | "We could not reach [thing]. Check your connection and [action]." |
| Server error | "Something went wrong on our end. We are looking into it. [Alternative action]" |

### Do Not Blame the User

- Prefer: "Please enter a date in MM/DD/YYYY format."
- Avoid: "You entered an invalid date."

## Empty States Are Onboarding

Three parts: (1) acknowledge briefly, (2) explain the value of filling it, (3) provide a clear action. "No projects yet. Create your first one to get started." beats "No items."

## Voice vs Tone

**Voice** is the brand personality — consistent everywhere. **Tone** adapts to the moment.

| Moment | Tone |
|--------|------|
| Success | Celebratory, brief: "Done. Your changes are live." |
| Error | Empathetic, helpful: "That did not work. Here is what to try..." |
| Loading | Reassuring: "Saving your work..." |
| Destructive confirm | Serious, clear: "Delete this project? This cannot be undone." |

**Never use humor for errors.** Users are already frustrated. Be helpful, not cute.

## Writing for Accessibility

- **Link text** must have standalone meaning. "View pricing plans", not "Click here".
- **Alt text** describes information, not the image. "Revenue increased 40% in Q4", not "Chart". Use `alt=""` for decorative images.
- **Icon buttons** need `aria-label`.

## Writing for Translation

Plan for text expansion:

| Language | Expansion |
|----------|-----------|
| German | +30% |
| French | +20% |
| Finnish | +30–40% |
| Chinese | −30% (fewer chars, same width) |

Translation-friendly patterns:

- Keep numbers separate: "New messages: 3" beats "You have 3 new messages."
- Use full sentences as single strings. Word order varies by language; do not concatenate fragments.
- Avoid abbreviations: "5 minutes ago", not "5 mins ago".
- Give translators context for where strings appear.

## Consistency: Pick One Term

| Inconsistent | Consistent |
|--------------|-----------|
| Delete / Remove / Trash | Delete |
| Settings / Preferences / Options | Settings |
| Sign in / Log in / Enter | Sign in |
| Create / Add / New | Create |

Build a terminology glossary and enforce it. Variety creates confusion.

## Avoid Redundant Copy

If the heading explains it, the intro is redundant. If the button is clear, do not explain it again. Say it once, say it well.

## Loading Copy

Be specific: "Saving your draft..." beats "Loading...". For long waits, set expectations ("This usually takes 30 seconds") or show progress.

## Confirmation Dialogs: Sparingly

Most confirmation dialogs are design failures — prefer undo. When you must confirm: name the action, explain consequences, use specific button labels ("Delete project" / "Keep project", not "Yes" / "No").

## Form Instructions

Show format via placeholder (`MM/DD/YYYY`), not via a full instruction. For non-obvious fields, explain *why* you are asking ("We use your phone for 2FA only — we will not call you").

## Rules Checklist

**DO**

- Use verb + object on buttons.
- Match tone to moment.
- Keep link text standalone.

**DON'T**

- Use jargon without explanation.
- Blame the user.
- Ship vague errors ("Something went wrong").
- Vary terminology for variety.
- Use humor for errors.
- Repeat information users can already see.

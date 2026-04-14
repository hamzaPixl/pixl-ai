---
title: Interaction Design
domain: frontend/design
source: adapted from impeccable (github.com/pbakaus/impeccable, Apache-2.0)
---

# Interaction Design

Make interactions feel fast, purposeful, and accessible. Every interactive surface should feel intentional and responsive.

## The Eight Interactive States

Every interactive element needs all eight designed:

| State | Trigger | Treatment |
|-------|---------|-----------|
| Default | At rest | Base styling |
| Hover | Pointer over (not touch) | Subtle lift, color shift |
| Focus | Keyboard / programmatic | Visible ring |
| Active | Being pressed | Pressed in, darker |
| Disabled | Not interactive | Reduced opacity, no pointer |
| Loading | Processing | Spinner or skeleton |
| Error | Invalid | Red border, icon, message |
| Success | Completed | Green check, confirmation |

Common miss: designing hover without focus. They are different surfaces — keyboard users never see hover states.

## Focus Rings: Do Them Right

Never `outline: none` without a replacement. Use `:focus-visible` so the ring shows only for keyboard users:

```css
button:focus            { outline: none; }
button:focus-visible    { outline: 2px solid var(--color-accent); outline-offset: 2px; }
```

Design the ring with:

- Contrast 3:1+ against adjacent colors.
- 2–3px thickness.
- Offset from the element, not inside it.
- Consistent across all interactive elements.

## Form Design

- Placeholders are NOT labels — they disappear on input. Always use a visible `<label>`.
- Validate on **blur**, not on every keystroke (exception: password strength).
- Place errors **below** the field; connect with `aria-describedby`.
- Show format with a placeholder (`MM/DD/YYYY`), not a full instruction line.

## Loading States

- **Skeleton screens > spinners**: they preview content shape and feel faster.
- **Optimistic UI**: update immediately, roll back on failure. Use for likes, follows, toggles. Never for payments or destructive actions.

## Modals: Use the Native Element

`<dialog>` gives you focus trap and Escape-to-close for free. Pair with `inert` to freeze content behind:

```html
<main inert>...</main>
<dialog open>...</dialog>
```

```js
const dialog = document.querySelector('dialog');
dialog.showModal();
```

Avoid modals unless there is no better alternative. Most modals are lazy.

## Popover API

For tooltips, dropdowns, and non-modal overlays:

```html
<button popovertarget="menu">Open menu</button>
<div id="menu" popover>...</div>
```

The `popover` attribute places the element in the **top layer**, above all content regardless of z-index or overflow ancestry. Light-dismiss, no portals, accessible by default.

## Dropdown Positioning

The single most common dropdown bug in generated code: a dropdown with `position: absolute` inside a container that has `overflow: hidden` or `overflow: auto` gets clipped.

### Modern: CSS Anchor Positioning

```css
.trigger  { anchor-name: --menu-trigger; }
.dropdown {
  position: fixed;
  position-anchor: --menu-trigger;
  position-area: block-end span-inline-end;
}
@position-try --flip-above {
  position-area: block-start span-inline-end;
}
```

Because the dropdown is `position: fixed`, it escapes ancestor overflow. `@position-try` handles viewport edges. Browser support: Chrome / Edge 125+. Use a fallback for Firefox / Safari.

### Popover + Anchor Combo

Combining Popover API with anchor positioning gives stacking, light-dismiss, accessibility, and correct placement in one pattern. Top-layer rendering means no portals.

### Portal / Teleport Fallback

- React: `createPortal(dropdown, document.body)`
- Vue: `<Teleport to="body">`
- Svelte: mount to `document.body`

Position with `getBoundingClientRect()` → `position: fixed`. Recalculate on scroll + resize. Flip above or align right on viewport overflow.

### Anti-Patterns

- `position: absolute` inside `overflow: hidden`.
- Arbitrary `z-index: 9999`. Use a semantic scale (dropdown 100 → sticky 200 → modal-backdrop 300 → modal 400 → toast 500 → tooltip 600).
- Rendering dropdown markup inline without a stacking-context escape (popover, portal, or fixed).

## Destructive Actions: Undo > Confirm

Users click through confirmations mindlessly. Remove from UI immediately, show an undo toast, actually delete after the toast expires. Reserve confirmation for truly irreversible actions (account deletion), high-cost actions, or batch operations — and even then, require the user to type the target name for the most destructive cases.

## Keyboard Navigation

### Roving Tabindex

For component groups (tabs, menus, radio groups): one item tabbable, arrow keys move within.

```html
<div role="tablist">
  <button role="tab" tabindex="0">Tab 1</button>
  <button role="tab" tabindex="-1">Tab 2</button>
  <button role="tab" tabindex="-1">Tab 3</button>
</div>
```

Tab moves to the next component entirely.

### Skip Links

Provide `<a href="#main-content">Skip to main content</a>`. Hide off-screen, reveal on focus.

## Progressive Disclosure

Start simple; reveal sophistication through interaction. Basic options first, advanced behind expandable sections. Hover states can reveal secondary actions, but never make them the ONLY way — touch users cannot hover.

## Gesture Discoverability

Swipe-to-delete and similar gestures are invisible. Hint:

- **Partial reveal**: show a delete button peeking from the edge.
- **Onboarding**: coach marks on first use.
- **Fallback**: always provide a visible menu option.

Do not rely on gestures as the only way to perform an action.

## Empty States as Onboarding

Empty states are teaching moments: (1) acknowledge briefly, (2) explain the value of filling it, (3) provide a clear action. "No projects yet. Create your first one to get started." beats "No items."

## Rules Checklist

**DO**

- Design all 8 states per interactive element.
- Use `:focus-visible` plus a visible ring.
- Use `<dialog>`, Popover API, anchor positioning.
- Prefer undo to confirmation.
- Use progressive disclosure.

**DON'T**

- Remove focus indicators without a replacement.
- Use placeholder text as a label.
- Size touch targets below 44×44px.
- Write generic error messages.
- Build custom controls without ARIA + keyboard support.
- Make every button primary. Use ghost buttons, text links, secondaries. Hierarchy matters.

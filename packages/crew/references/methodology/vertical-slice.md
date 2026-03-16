# Vertical Slice Decomposition

## Principle

Decompose features into vertical slices — each slice delivers user-visible value across all layers (UI → API → domain → persistence) rather than completing one horizontal layer at a time.

## Why Vertical Slices

- Each slice is independently deployable and testable
- Provides early feedback on the full flow
- Reduces integration risk (no "big bang" integration at the end)
- Enables parallel development of independent slices

## How to Decompose

1. **Identify the user action** — What does the user do?
2. **Trace the full path** — UI → API → domain → persistence
3. **Find the minimal slice** — What's the smallest version that works end-to-end?
4. **Add complexity incrementally** — Each subsequent slice adds a feature variant

## Example

Feature: "User can manage media files"

Vertical slices (ordered):
1. Upload a file (POST /media) → saves to DB → returns file ID
2. List files (GET /media) → paginated list
3. View file details (GET /media/:id) → single file with metadata
4. Update file metadata (PATCH /media/:id) → partial update
5. Delete file (DELETE /media/:id) → soft delete with archived status
6. Process file (background job) → thumbnail generation

Each slice is independently deployable and testable.

## Anti-patterns

- Building all DB migrations first, then all endpoints, then all UI
- Creating "utility" tasks that don't deliver user value
- Slices that depend on other unfinished slices

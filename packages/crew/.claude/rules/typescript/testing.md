---
paths:
  - "**/*.test.ts"
  - "**/*.spec.ts"
  - "**/*.test.tsx"
  - "**/*.spec.tsx"
---
# TypeScript Testing Rules

## Framework

- Use vitest for new projects (faster, native ESM support)
- Use jest for existing projects that already have it configured
- Use `@testing-library/react` for React component tests

## Test Structure

```typescript
describe('UserService', () => {
  it('should create user with valid email', async () => {
    // Arrange
    const service = new UserService(mockRepo);
    // Act
    const user = await service.create({ email: 'test@example.com' });
    // Assert
    expect(user.email).toBe('test@example.com');
  });
});
```

## Mocking

- Use `vi.fn()` / `jest.fn()` for function mocks
- Use `vi.mock()` / `jest.mock()` for module mocks
- Prefer dependency injection over module mocking when possible
- Reset mocks between tests: `beforeEach(() => vi.clearAllMocks())`

## Type Safety in Tests

- Don't use `any` in test code — use proper types or `Partial<T>` for test fixtures
- Use `satisfies` for test data: `const testUser = { ... } satisfies CreateUserInput`
- Type-check test helpers and factory functions

## React Testing

- Test behavior, not implementation details
- Query by role/label (accessible selectors), not test IDs
- Use `userEvent` over `fireEvent` for realistic interactions
- Use `screen` from testing-library for queries

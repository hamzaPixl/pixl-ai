# Requirement Decomposition

Strategies for parsing PRDs, user stories, and specification documents into atomic, checkable requirements.

## Parsing Strategy

### 1. Identify Requirement Sources

PRDs contain requirements in various forms:
- **Explicit**: "The system shall..." / "Users must be able to..."
- **Implicit**: Feature descriptions that imply behavior ("The dashboard shows real-time metrics" → must have WebSocket/polling, must have metrics API)
- **Acceptance criteria**: Often listed under user stories as checkboxes
- **Non-functional**: Performance targets, security requirements, compliance needs
- **Constraints**: "Must use PostgreSQL", "Must deploy to AWS", "Must support IE11"

### 2. Atomicity Rules

Each requirement should be:
- **Testable**: Can be verified with a yes/no check
- **Independent**: Doesn't bundle multiple behaviors
- **Unambiguous**: One reasonable interpretation

**Split when**: a requirement contains "and", "or", "also", or describes multiple behaviors.

Example — before:
> "Users can sign up with email and password, and receive a confirmation email"

After:
- R-001: User can submit signup form with email and password
- R-002: Email is validated on signup input
- R-003: Password must be at least 8 characters
- R-004: Confirmation email sent after successful signup

### 3. Category Classification

| Category | Description | Examples |
|----------|-------------|----------|
| `functional` | User-visible behavior | "User can reset password" |
| `non-functional` | Quality attributes | "Page loads in < 3s", "99.9% uptime" |
| `constraint` | Technical boundaries | "Must use React", "GDPR compliant" |

### 4. Priority Assignment

Use MoSCoW if the PRD doesn't specify priority:
- **must**: Core functionality, launch blocker
- **should**: Important but has workaround
- **could**: Nice to have, not critical

If the PRD uses numbered priorities (P0/P1/P2), map: P0 → must, P1 → should, P2 → could.

### 5. Search Hint Generation

For each requirement, generate 3-5 search patterns:
- **Function names**: camelCase versions of the action ("resetPassword", "sendConfirmation")
- **Route patterns**: URL segments ("/auth/reset", "/api/confirm")
- **File paths**: expected directory patterns ("auth/", "password/")
- **Domain terms**: key nouns from the requirement ("confirmation", "audit-log")
- **Test names**: expected test descriptions ("should reset password", "sends confirmation")

### 6. Handling Ambiguity

When a requirement is ambiguous:
1. Note the ambiguity in the requirement's `notes` field
2. Generate search hints for the most likely interpretation
3. Flag for user clarification using AskUserQuestion
4. Don't guess — missing a requirement is better than misclassifying one

## Output Format

Each decomposed requirement follows this structure:

```json
{
  "id": "R-NNN",
  "category": "functional|non-functional|constraint",
  "summary": "One-sentence description of the requirement",
  "acceptance_criteria": [
    "Specific testable criterion 1",
    "Specific testable criterion 2"
  ],
  "priority": "must|should|could",
  "search_hints": ["pattern1", "pattern2", "path/pattern"],
  "notes": "Any ambiguity or clarification needed"
}
```

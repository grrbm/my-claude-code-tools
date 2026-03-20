---
name: linear-create-task
description: Create a new Linear task. Use when asked to create a linear task, create a linear issue, add a task to linear, or log something to linear.
argument-hint: <description>
allowed-tools: Bash(curl *)
---

Create a new Linear issue based on: $ARGUMENTS

Title format:
```
<type>/<kebab-case-title> — <Short human-readable summary>
```

Examples:
```
fix/notification-deep-link — Push notification opens specific order
feat/order-export — Export orders as CSV from merchant dashboard
chore/cleanup-draft-orders — Remove stale draft orders on expiry
```

Description template (fill in all sections — never leave placeholder text):

```markdown
<type>/<kebab-case-title> — <Short human-readable summary>

## What & Why
<!-- One paragraph explaining the problem and why it matters -->

## Done looks like
<!-- Bullet list of concrete, verifiable acceptance criteria -->

## What already exists
<!-- Bullet list of relevant existing code: file paths, function names, etc. -->

## NOT in scope
<!-- Bullet list of things explicitly excluded from this task -->

## Assumptions [⚠️ verify]
<!-- Any assumptions that need to be validated before or during implementation -->
```

Workflow:

1. If the team ID is unknown, fetch it: `query { teams { nodes { id name } } }`
2. Build the title and description from the provided input.
3. Create the issue via the Linear GraphQL mutation:

```graphql
mutation IssueCreate($input: IssueCreateInput!) {
  issueCreate(input: $input) {
    success
    issue { id identifier title url }
  }
}
```

Input fields:
- `teamId` — Linear team ID
- `title` — formatted as above
- `description` — filled template in markdown
- `stateId` — "Backlog" state ID (fetch if needed)

4. Print the result:
```
<ISSUE_KEY> - <ISSUE_TITLE>
<ISSUE_URL>
```

Rules:
- All description sections must be present; use "N/A" if not applicable.
- Fill sections with real content — do not leave placeholder comments as-is.
- Never hardcode or print the API key.
- Do NOT assign the issue or set priority unless explicitly asked.

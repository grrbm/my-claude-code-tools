# Create a Linear Task

Trigger:
When I ask something like:

create a linear task
create a linear issue
add a task to linear
log this to linear

Behavior:
Create a new issue in Linear using the API with a structured title and description.

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
<!-- One paragraph explaining the problem and why it matters to the user -->

## Done looks like
<!-- Bullet list of concrete, verifiable acceptance criteria -->

## What already exists
<!-- Bullet list of relevant existing code: file paths, function names, hooks, etc. -->

## NOT in scope
<!-- Bullet list of things explicitly excluded from this task -->

## Assumptions [⚠️ verify]
<!-- Any assumptions that need to be validated before or during implementation -->
```

Workflow:

1. Ask me for the team ID if not already known. The shopit workspace team ID is `SHOPIT_TEAM_ID` — fetch it once via the API if needed.
2. Build the title and description from what I provide.
3. Create the issue via the Linear GraphQL mutation:

```graphql
mutation IssueCreate($input: IssueCreateInput!) {
  issueCreate(input: $input) {
    success
    issue {
      id
      identifier
      title
      url
    }
  }
}
```

With input fields:
- `teamId` — the Linear team ID
- `title` — formatted as above
- `description` — filled template in markdown
- `stateId` — use the "Backlog" state ID for the team (fetch if needed)

4. Print the created issue in this format:

```
<ISSUE_KEY> - <ISSUE_TITLE>
<ISSUE_URL>
```

Rules:

- Always use the description template — all sections must be present.
- Fill in sections with real content based on what I describe — do not leave placeholder comments as-is.
- Sections with no relevant content should say "N/A".
- Never hardcode or print the API key.
- Do NOT assign the issue or set a priority unless I explicitly ask.
- If the team ID is unknown, fetch it from `query { teams { nodes { id name } } }` first.

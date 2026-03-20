---
name: linear-find-task
description: Find an available Linear task to work on next. Use when asked to find a new task, find a linear issue, or what to work on next. Queries unassigned issues in "To Do" or "Backlog" states, checks blockers, and returns the best candidate.
allowed-tools: Bash(curl *)
---

Find a suitable Linear task using the Linear GraphQL API ($LINEAR_API_KEY).

Selection criteria — the task must satisfy ALL of the following:

1. Issue state must be "To Do" or "Backlog".
2. Must NOT be assigned to anyone.
3. If it has blockers, all blocker issues must be in a completed state.

Priority rules:
1. Always prioritize issues in "To Do" first.
2. Fall back to "Backlog" only if no valid "To Do" issues exist.

Additional conditions:
- Must not be archived.
- Must not be canceled.

Workflow:

1. Query Linear issues using the API.
2. Filter among "To Do" issues first.
3. If none are valid, search among "Backlog" issues.
4. For each candidate: verify it is unassigned and check blocker issues.
5. Skip any issue whose blockers are not completed.
6. Select the best valid candidate.

Output format:

```
<ISSUE_KEY> - <ISSUE_TITLE>
<ISSUE_URL>
```

Example:
```
SHO-142 - Fix cart tax calculation edge case
https://linear.app/shopit/issue/SHO-142
```

Rules:
- Do NOT assign the issue.
- Do NOT modify the issue.
- Only fetch and display one task unless explicitly asked for more.
- If no valid task exists, say so.

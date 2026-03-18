# Find a New Linear Task

Trigger:
When I ask something like:

find me a new linear task to do
find a linear issue for me
what task should I work on next

Behavior:

Use the Linear API to find a suitable task.

Selection criteria:

The task must satisfy ALL of the following:

1. The issue state must be either:
   - "To Do"
   - or "Backlog"

2. The issue must NOT be assigned to anyone.

3. If the issue has blockers:
   - All blocker issues must be in a completed state.
   - If any blocker is still open, skip the task.

Priority rules:

1. Always prioritize issues in **"To Do"**.
2. If no valid "To Do" issues exist, then look for issues in **"Backlog"**.

Additional conditions:

- The issue must not be archived.
- The issue must not be canceled.

Workflow:

1. Query Linear issues using the API.
2. First filter and search among issues in **"To Do"**.
3. If none are valid, search among issues in **"Backlog"**.
4. For each candidate issue:
   - verify it is unassigned
   - check blocker issues
5. Skip any issue whose blockers are not completed.
6. Select the best valid candidate.

Output:

Print the issue in the terminal in this format:

<ISSUE_KEY> - <ISSUE_TITLE>
<ISSUE_URL>

Example:

SHO-142 - Fix cart tax calculation edge case
https://linear.app/shopit/issue/SHO-142

Rules:

- Do NOT assign the issue to me.
- Do NOT modify the issue.
- Only fetch and display a good task candidate.
- Only return one task unless I explicitly ask for more.
- If no valid task exists, say that no suitable tasks were found.

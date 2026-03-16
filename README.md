# Global Claude Rules

These rules apply to all projects unless explicitly overridden.

---

# Test Rule

Trigger:
When I ask: "how much are we on"

Action:
Reply exactly:

100+1 percent

Do not add anything else.

---

# Linear Integration

Trigger:
When I ask you to check, fetch, or modify anything on Linear.

Behavior:
1. Use the Linear API.
2. Use the API key from the environment variable `LINEAR_API_KEY`.
3. Never hardcode or print the API key.
4. Prefer using curl or CLI tools to query the Linear GraphQL API.

API Endpoint:
https://api.linear.app/graphql

Authentication Header:

Authorization: $LINEAR_API_KEY

Example request pattern:

curl https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{ "query": "query { viewer { id name email } }" }'

Rules:
- Always read the API key from the environment variable.
- Never expose the API key in output.
- Only return relevant results.

---

# GitHub PR Review Automation

Trigger:
When I say:

review this PR <pr_link>

Behavior:
Automatically review the GitHub pull request using GitHub CLI (`gh`).

Workflow:

1. Parse the PR URL to determine:
   - owner
   - repository
   - pull request number

2. Collect PR information:
   - title
   - description
   - changed files
   - full diff
   - existing issue comments
   - existing review comments

3. Read the entire diff before writing the review.

4. Read all previous comments and reviews first.

5. Verify whether previously reported issues are already resolved.

6. Write my own consolidated review comment.

Requirements:

- Always read the diff before reviewing.
- Always read previous comments and reviews.
- Do not repeat feedback unless it is still unresolved.
- Base the review on the latest version of the PR.
- Focus on:
  - bugs
  - regressions
  - edge cases
  - security
  - performance
  - maintainability
  - architecture

Review style:

- concise
- specific
- reference file paths or functions when relevant

Posting behavior:

- Post a single consolidated PR comment.
- Only submit an official GitHub review (Approve / Request changes) if I explicitly ask.

Preferred GitHub CLI tools:

gh pr view  
gh pr diff  
gh api repos/<owner>/<repo>/pulls/<number>/comments  
gh api repos/<owner>/<repo>/issues/<number>/comments  
gh pr comment

---

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

---

# Implement a Linear Task

Trigger:
When I ask to implement a Linear task and provide a Linear issue URL.

Workflow:

1. Parse the Linear issue URL.
2. Fetch the issue details from Linear.
3. Fetch all comments from the issue.
4. Checkout `main`.
5. Pull the latest `main` from origin.
6. Create a branch from the updated `main` using:

feat/<issue-key-lowercase>-<kebab-case-title>

Example:
feat/sho-114-cart-replace-hardcoded-tax-and-shipping-pricing

7. Checkout the new branch.
8. Review the issue description and all comments carefully.
9. Use the latest clarified requirements from the task discussion.
10. Start implementing the feature.

Rules:

- Always base the branch on the latest `main`.
- Always read the Linear task before coding.
- Always read all Linear comments before coding.
- Do not skip clarifying comments or implementation notes.
- Do not ask me whether to checkout `main` or pull first; do it automatically.
- Do not ask me whether to create the branch; do it automatically.
- Start implementation after the branch is ready and the task context is fully read.
- If there is an existing local branch for the same issue, mention it before creating a duplicate.
- If access/authentication fails, explain the exact missing command, credential, or permission.

---

# Commit Message Convention

Trigger:
When I ask you to commit changes, create a commit, or stage and commit anything.

Format:

```
<type>(<scope>): SHO-<number> <description>
```

Types (pick one):
`feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`, `ci`, `build`, `revert`

Scopes (pick one or combine with `/`):
`web`, `mobile`, `convex`, `shared`, `workflows`

Examples:
```
feat(mobile): SHO-152 add orphaned gift draft order cleanup cron
fix(convex/mobile): SHO-99 correct order fulfillment notification payload
chore(shared): SHO-101 remove unused gift expiration helpers
```

Rules:

- Always follow this format exactly — no exceptions.
- Infer the scope from the files changed (e.g. changes in `apps/mobile` → `mobile`, `packages/convex` → `convex`).
- If changes span multiple scopes, combine them with `/` (e.g. `convex/mobile`).
- Infer the SHO issue number from the current branch name if not explicitly provided.
- If no issue number can be determined, ask me before committing.
- The description must be lowercase and concise.
- Do not add a period at the end of the description.

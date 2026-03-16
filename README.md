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

# Implement PR Review Changes

Trigger:
When I say something like:

implement changes on <pr-url>
implement review changes on <pr-url>
address review comments on <pr-url>
fix review feedback on <pr-url>

Behavior:
Read the entire PR and all its review/comments, implement any pending requested changes, then post a comment summarizing what was done.

Workflow:

1. Parse the PR URL to determine owner, repository, and PR number.

2. Collect all PR information using GitHub CLI:
   - PR title, description, and current diff (`gh pr view`, `gh pr diff`)
   - All issue-level comments (`gh api repos/<owner>/<repo>/issues/<number>/comments`)
   - All review comments on the diff (`gh api repos/<owner>/<repo>/pulls/<number>/comments`)
   - All submitted reviews (`gh api repos/<owner>/<repo>/pulls/<number>/reviews`)

3. Identify pending items: only act on comments/reviews requesting changes that have NOT already been addressed in a subsequent commit or reply.

4. Check out the PR branch locally if not already on it:
   - `gh pr checkout <number>`

5. Implement all pending requested changes.

6. Post a single comment on the PR via `gh pr comment <number> --body "..."` summarizing:
   - What was changed and why (one bullet per addressed item)
   - Any items intentionally skipped and the reason

Rules:

- Always read ALL comments and reviews before touching any code.
- Never implement something that is already resolved.
- If a review comment is ambiguous, make a reasonable judgment and note it in the PR comment.
- Do not ask for confirmation before implementing — just do it.
- Do not leave placeholder TODOs; fully implement each change.
- Follow all existing code conventions.
- If the PR branch does not exist locally, check it out automatically.
- Do NOT commit or push — leave that to me.

Preferred GitHub CLI tools:

gh pr view <number>
gh pr diff <number>
gh pr checkout <number>
gh api repos/<owner>/<repo>/pulls/<number>/comments
gh api repos/<owner>/<repo>/issues/<number>/comments
gh api repos/<owner>/<repo>/pulls/<number>/reviews
gh pr comment <number> --body "..."

---

# Log Work to Memory

Trigger:
Automatically — after completing any meaningful unit of work during a conversation.

Behavior:
Save a `project` type memory entry describing what was just done, so it can be recalled later in "what did i do today" summaries.

When to save:
- After finishing or making significant progress on a feature or bug fix
- After addressing PR review feedback
- After creating or merging a PR
- After completing a Linear task or a significant chunk of one

What to save:
- A plain-English description of what was done (no jargon, no file paths)
- The Linear issue it relates to (if any)
- Today's date (use the `currentDate` from context)

Format (use `project` memory type):

```
What was done, in plain English.

**Why:** The Linear issue or reason behind the work.
**How to apply:** Use this for daily standup / end-of-day summary.
```

Rules:

- Save after the work is done, not before.
- Keep it brief — one or two sentences max.
- Do not save ephemeral or in-progress notes; only save completed work.
- Do not save the same work twice.

---

# What Did I Do Today

Trigger:
When I ask something like:

what did i do today
what have i worked on today
summarize my day
what did we do today

Behavior:
Read Claude memory to reconstruct what was worked on today, then give a short, plain-English summary — no technical jargon.

Workflow:

1. Get today's date from the environment.

2. Read all memory files in the project memory directory:
   `/Users/guilhermereis/.claude/projects/-Users-guilhermereis-Desktop-clones-shopit-monorepo/memory/`

3. Look for any `project` type memories logged today (check dates in the memory content).

4. Check for any uncommitted changes or work in progress as a supplement:
   `git status` and `git diff --stat`

5. Synthesize into bullet points describing what was worked on — as if explaining to a non-technical friend or writing a standup note.

Rules:

- Use bullet points — one bullet per meaningful area of work.
- No technical terms, no function names, no file paths, no jargon.
- Focus on the "what" and "why" from a product/feature perspective, not implementation details.
- Only report work that I (the user) did — not other contributors.
- If memory is empty or has nothing for today, say so honestly rather than falling back to git log.
- If nothing was committed yet but there are changes in progress, mention that too.
- Never mention the `new-apis-examples/` folder or any untracked folders that are clearly experiments/scratch work.

Example output:

- Added an automatic cleanup job that removes stale gift orders that got stuck during checkout
- Set up a PR for it and got it reviewed

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
- Do NOT add a `Co-Authored-By` line or any Claude attribution to commit messages.
- Never stage or commit files that are gitignored (e.g. `_generated/`). Only commit source files.

---

# PR Creation Convention

Trigger:
When I ask you to create a PR, open a pull request, or push and create a PR.

Title format:

```
<type>(<scope>): SHO-<number> <description>
```

Same rules as commit messages — infer type, scope, and issue number from branch name and changed files.

Example:
```
chore(convex): SHO-152 add orphaned gift draft order cleanup cron
```

Body template (fill in each section based on the changes — do not leave placeholder text):

```markdown
## Short Description
<!-- Brief description since we link to Linear anyway -->

## Linear Issue
https://linear.app/shopit/issue/SHO-<number>

## What should reviewers focus on?
<!-- Any "gotchas" or non-obvious changes. Include thought process or trade-offs with different approaches if any -->

## How to manually test this
<!-- Specific steps and edge cases reviewers should verify -->

## Deployment Notes
<!-- DB Schema changes, new API keys, feature flags, deployment order, etc. -->

## Performance/Security Implications
<!-- New actions, auth changes, performance impacts, etc. -->

## App/Platform Specific Notes
<!-- Any mobile/web/convex/shared specific considerations -->

## Screenshots or Video
<!-- Visual evidence of changes -->
```

Rules:

- Always use this template — no exceptions.
- Infer the Linear issue URL from the branch name.
- Fill in each section with real content based on the diff — do not leave placeholder comments as-is if the content is known.
- Sections with no relevant content should say "N/A".
- Do NOT add any Claude attribution to the PR body.

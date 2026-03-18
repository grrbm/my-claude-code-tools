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

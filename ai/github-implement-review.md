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

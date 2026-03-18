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

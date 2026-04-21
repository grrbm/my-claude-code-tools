---
name: create-pr
description: Create a GitHub pull request. Use when asked to create a PR, open a pull request, or push and create a PR.
allowed-tools: Bash(git *), Bash(gh *)
---

Create a pull request following the project conventions.

## Step 1 — Gather context

Run in parallel:
```bash
git status
git diff origin/main...HEAD --stat
git log origin/main...HEAD --format="%h %s"
```

## Step 2 — Determine title

Format: `<type>(<scope>): SHO-<number> <description>`

- Infer `type` from the nature of the changes: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`, `ci`, `build`, `revert`
- Infer `scope` from files changed: `web`, `mobile`, `convex`, `shared`, `workflows` — combine with `/` if multiple (e.g. `convex/mobile`)
- Infer the SHO issue number from the current branch name
- Description must be lowercase and concise, no trailing period

## Step 3 — Push if needed

```bash
git push -u origin HEAD
```

## Step 4 — Create the PR

Use this exact body template, filled in from the diff — do not leave placeholder comments as-is. Sections with nothing relevant should say "N/A". Do NOT add any Claude attribution.

```bash
gh pr create --title "<title>" --body "$(cat <<'EOF'
## Short Description
<brief description>

## Linear Issue
https://linear.app/shopit/issue/SHO-<number>

## What should reviewers focus on?
<gotchas, non-obvious changes, trade-offs>

## How to manually test this
<specific steps and edge cases>

## Deployment Notes
<schema changes, new API keys, feature flags, deployment order>

## Performance/Security Implications
<new actions, auth changes, performance impacts>

## App/Platform Specific Notes
<mobile/web/convex/shared considerations>

## Screenshots or Video
<visual evidence or N/A>
EOF
)"
```

## Step 5 — Return the PR URL

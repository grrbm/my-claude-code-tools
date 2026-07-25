---
name: create-pr
description: Create a GitHub pull request. Use when asked to create a PR, open a pull request, or push and create a PR.
allowed-tools: Bash(git *), Bash(gh *), Bash(curl *), Bash(grep *), Read
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

## Step 3 — Fetch the Linear ticket and all comments

Read the API key:
```bash
grep '^LINEAR_API_KEY=' /Users/guilhermereis/Desktop/clones/shopit-monorepo/.env.local | tail -1 | cut -d'=' -f2
```

Fetch the issue and all comments in one request (replace `<IDENTIFIER>` with the SHO number from the branch name):
```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: <key>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ issue(id: \"<IDENTIFIER>\") { id identifier title description comments { nodes { body createdAt user { name } } } } }"
  }'
```

Read every comment. Look for:
- Answers to open questions (especially replies to any "Questions for your team ❓" or "Questions ❓" sections in earlier comments)
- Scope addenda or requirement clarifications that supersede the original description
- Product decisions, trade-off resolutions, or explicit "yes/no" answers to implementation questions

## Step 4 — Push if needed

```bash
git push -u origin HEAD
```

## Step 5 — Create the PR

Use this exact body template, filled in from the diff and the Linear context. Do not leave placeholder comments as-is. Sections with nothing relevant should say "N/A". Do NOT add any Claude attribution.

For the **Open Questions** section:
- If questions from the ticket analysis comments were answered in subsequent comments, summarise the answer and mark them as resolved.
- If questions were never answered in any comment, list them verbatim and mark them as still open so reviewers know they need resolution.
- If there were no open questions in the ticket, write "N/A".

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

## Open Questions
<for each question from the ticket analysis:
  - ✅ **<question summary>** — <answer from comments, or "resolved: <decision>">
  - ❓ **<question summary>** — still open, needs resolution before/after merge>
or N/A if there were none>

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

## Step 6 — Return the PR URL

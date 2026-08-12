---
name: hotfix-pr
description: Ship a hotfix PR straight from a plain-text description, with zero Linear involvement — no issue created, none looked up, nothing linked in the PR. Use when asked to hotfix something, "hotfix-pr", "ship a hotfix", or open a PR for a fix that doesn't have and shouldn't get a Linear ticket.
argument-hint: <description of what to fix>
---

Ship a hotfix PR for: $ARGUMENTS — same destination as `create-pr` (a properly titled/described PR, pushed and opened via `gh`), but this pipeline must never touch Linear: no issue created, no issue fetched, no Linear API call anywhere in the run.

That constraint is why this skill can't just compose `linear-create-task`, `linear-implement-task`, and `create-pr` the way the rest of this repo's pipelines do — `linear-implement-task` needs a real Linear issue URL as its argument, and `create-pr`'s own Step 3 unconditionally fetches a ticket by the SHO number it expects to find in the branch name. Both would either fail or force a Linear round-trip. So the steps below are self-contained, deliberately mirroring what those skills do minus every Linear-touching part.

## Step 0 — Require a real description

If `$ARGUMENTS` is empty or too vague to implement from (e.g. just "hotfix"), stop and ask what needs to change — there's no ticket to fall back on for context here, so the description in the command *is* the entire spec.

## Step 1 — Branch off main

- Checkout `main` and pull the latest from origin.
- Branch as `fix/<kebab-case-summary-of-the-description>` — no issue number prefix, since there is no issue.
- If a local branch with that name already exists, mention it before creating a duplicate rather than overwriting it.

## Step 2 — Implement it

Implement the change described in `$ARGUMENTS` directly against the codebase. There's no Linear description or comment thread to cross-check against — the command's argument is the full and only spec, so if it's ambiguous on some point, use your own judgment and note the assumption in the PR body's "What should reviewers focus on?" section rather than guessing silently.

## Step 3 — Commit

Commit the change with a concise message describing what changed and why, in this repo's usual style (see `git log` for recent examples). Only stage the files that are actually part of this fix — leave any unrelated pre-existing working-tree changes untouched.

## Step 4 — Push and open the PR

```bash
git push -u origin HEAD
```

Title format: `<type>(<scope>): <description>` — same `type`/`scope` inference rules as `create-pr` (type from the nature of the change: `feat`, `fix`, `refactor`, etc.; scope from files touched: `mobile`, `web`, `convex`, `shared`, combined with `/` if more than one). There is no `SHO-<number>` segment, since there is no ticket.

Use this body template — the same shape as `create-pr`'s, minus the Linear-specific section:

```bash
gh pr create --title "<title>" --body "$(cat <<'EOF'
## Short Description
<brief description>

## What should reviewers focus on?
<gotchas, non-obvious changes, trade-offs, or assumptions made in place of a Linear ticket to clarify against>

## How to manually test this
<specific steps and edge cases>

## Deployment Notes
<schema changes, new API keys, feature flags, deployment order, or N/A>

## Performance/Security Implications
<new actions, auth changes, performance impacts, or N/A>

## App/Platform Specific Notes
<mobile/web/convex/shared considerations, or N/A>

## Screenshots or Video
<visual evidence or N/A>
EOF
)"
```

Capture the returned PR URL.

## Step 5 — Report

Return the PR URL. Nothing else needs reporting — there's no Linear artifact to mention because none was ever created.

## Rules

- Never call the Linear API, never invoke `linear-create-task` or `linear-implement-task`, never reference a SHO number in the branch name, commit message, or PR — that's the entire point of this command over the regular `create-pr` flow.
- Don't ask the user for a Linear ticket — if they wanted one, they'd have used `linear-implement-task` + `create-pr` directly instead of this command.
- Do not add any Claude attribution anywhere (commits or PR).

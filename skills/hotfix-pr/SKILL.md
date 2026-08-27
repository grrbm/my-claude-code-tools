---
name: hotfix-pr
description: Ship a hotfix PR straight from a plain-text description, with zero Linear involvement — no issue created, none looked up, nothing linked in the PR. Use when asked to hotfix something, "hotfix-pr", "ship a hotfix", or open a PR for a fix that doesn't have and shouldn't get a Linear ticket.
argument-hint: <description of what to fix>
allowed-tools: Bash(git *), Bash(gh *), Bash(node *), Read, Edit, Write
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

## Step 4 — Docs-sync preflight (before pushing)

Same reasoning as `create-pr`: this repo's `main` branch ruleset has `dismiss_stale_reviews_on_push: true`, so any commit pushed after review dismisses approvals — get docs coverage right before the PR exists, not after. Run:

```bash
node scripts/check-docs-sync.mjs --validate
```

If it reports `<file>: no page lists it under "sources" — add it to the page that describes it, or exempt it in apps/docs/not-documented.json with a reason` for any file this fix adds or touches, either add the file's path to the closest-matching existing page's `sources:` frontmatter (`apps/docs/content/**/*.mdx`), or add a reasoned entry (10+ chars, not a placeholder) to `apps/docs/not-documented.json` (create it as `{}` if missing). Fold that fix into Step 3's commit — nothing has been pushed yet. Re-run until it prints `Docs valid: N page(s).`.

## Step 5 — Push and open the PR

```bash
git push -u origin HEAD
```

Title format: `<type>(<scope>): <description>` — same `type`/`scope` inference rules as `create-pr` (type from the nature of the change: `feat`, `fix`, `refactor`, etc.; scope from files touched: `mobile`, `web`, `convex`, `shared`, combined with `/` if more than one). There is no `SHO-<number>` segment, since there is no ticket.

Use this body template — `.github/pull_request_template.md`'s six required sections (Danger, `.github/danger/rules.ts`, fails the build if any is missing, misheaded, or a placeholder), plus the same reviewer-focus/testing content the old template carried, folded in as extra trailing sections:

- `## What this changes (plain English)` must be the very first content line of the body. 3-5 plain sentences, no file names, acronyms expanded. Never N/A.
- `## Linear Issue` — this skill never touches Linear, so this is always `N/A — hotfix, no Linear ticket` (writing that line is not "touching Linear": no API call, no SHO number, nothing looked up or created — it only satisfies Danger's required heading).
- `## Merge invariant` — one sentence on what must stay true for this to be safe, then risk areas/where reviewers should look. Can never be N/A.
- `## QA` — real verification evidence, or exactly `Not visually verified — <reason, 10+ chars, not a placeholder like "not tested">`.
- `## Deployment Notes` — prose or `N/A`.
- `## Docs` — prose on what was updated, or exactly `Docs: not needed — <reason, 10+ chars>`, or `N/A`.

```bash
gh pr create --title "<title>" --body "$(cat <<'EOF'
## What this changes (plain English)
<3-5 plain-English sentences: what changes and why, no file names, acronyms expanded>

## Linear Issue
N/A — hotfix, no Linear ticket

## Merge invariant
<one sentence on what must remain true for this to be safe, then risk areas/where reviewers should look>

## QA
<verification evidence, or exactly "Not visually verified — <reason>">

## Deployment Notes
<schema changes, new API keys, feature flags, deployment order, or N/A>

## Docs
<pages updated, or exactly "Docs: not needed — <reason>", or N/A>

## What should reviewers focus on?
<gotchas, non-obvious changes, trade-offs, or assumptions made in place of a Linear ticket to clarify against>
EOF
)"
```

## Step 6 — Gate check

```bash
git fetch origin main --quiet
PR_BODY="$(gh pr view --json body -q .body)" node scripts/check-docs-sync.mjs --base origin/main --head HEAD
```

If it prints `FAIL`, fix the `## Docs` opt-out line (edit via `gh pr edit --body-file`, no push needed) or update the listed page now, before anyone reviews.

Capture the returned PR URL.

## Step 7 — Report

Return the PR URL. Nothing else needs reporting — there's no Linear artifact to mention because none was ever created.

## Rules

- Never call the Linear API, never invoke `linear-create-task` or `linear-implement-task`, never reference a SHO number in the branch name, commit message, or PR — that's the entire point of this command over the regular `create-pr` flow.
- Don't ask the user for a Linear ticket — if they wanted one, they'd have used `linear-implement-task` + `create-pr` directly instead of this command.
- Do not add any Claude attribution anywhere (commits or PR).

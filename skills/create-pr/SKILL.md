---
name: create-pr
description: Create a GitHub pull request. Use when asked to create a PR, open a pull request, or push and create a PR.
allowed-tools: Bash(git *), Bash(gh *), Bash(curl *), Bash(grep *), Bash(node *), Read, Edit, Write
---

Create a pull request following the project conventions.

This repo enforces two independent, code-level gates on every PR — `PR Policy` (Danger, reads `.github/danger/dangerfile.ts` / `rules.ts`) and `PR CI`'s docs-sync gate (`scripts/check-docs-sync.mjs`). Both are read from `main` at check-run time, not from whatever version existed when the branch was created, so they can start failing on an unchanged branch if `main` moves. Get both right before the PR exists — this repo's branch ruleset has `dismiss_stale_reviews_on_push: true`, so any commit pushed to an already-reviewed PR wipes its approvals. Confirm that's still the setting if it matters (`gh api repos/<owner>/<repo>/rulesets/<id>`); don't assume it's stayed the same.

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

## Step 4 — Docs-sync preflight (before pushing)

This catches "new file nothing documents" before there's a PR to lose reviews on. Run:

```bash
node scripts/check-docs-sync.mjs --validate
```

If it reports `<file>: no page lists it under "sources" — add it to the page that describes it, or exempt it in apps/docs/not-documented.json with a reason` for any file this branch adds or touches:

- Prefer documenting it: find the page under `apps/docs/content/**/*.mdx` whose `sources:` frontmatter already lists sibling files in the same directory/domain, and add the new file's repo-relative path to that list.
- Only if no page's domain genuinely fits, add an entry to `apps/docs/not-documented.json` (create it as `{}` if it doesn't exist) — `{ "<repo-relative-glob>": "<real reason, 10+ chars, not a placeholder>" }`.

Commit that fix into the same pre-push commit (amend, or a small follow-up commit — either is fine, nothing has been pushed yet). Re-run `--validate` until it prints `Docs valid: N page(s).` with no problems.

## Step 5 — Push

```bash
git push -u origin HEAD
```

## Step 6 — Draft the PR body

Use this exact body template — it is `.github/pull_request_template.md` verbatim, filled in from the diff and the Linear context. Do not leave placeholder comments as-is. Do NOT add any Claude attribution.

Hard constraints (enforced by `.github/danger/rules.ts` — get these wrong and `PR Policy` fails even with good content):
- `## What this changes (plain English)` must be the very first content line of the body — nothing before it, not even a blank HTML comment.
- All six headings must appear exactly as written below, in order. Danger matches heading text exactly (case-insensitive); do not rename or merge them.
- **What this changes (plain English)**: 3-5 sentences, no file names, acronyms expanded, plain enough for any teammate. State explicitly if this touches money, privacy, or the gift claim path. Never N/A.
- **Linear Issue**: a real `SHO-<number>` link, or `N/A — <reason, 10+ chars>` for maintenance/emergency work.
- **Merge invariant**: one sentence on what must stay true for this to be safe, then the risk areas/where reviewers should look. Can never be N/A.
- **QA**: real verification evidence (screenshots, test output, review steps), or exactly the line `Not visually verified — <reason, 10+ chars>`. Reasons like "not tested"/"n/a"/"todo" are rejected as placeholders — give the real reason (e.g. "backend-only refactor, no UI change").
- **Deployment Notes**: prose, or `N/A — <reason>` / bare `N/A`.
- **Docs**: prose describing what was updated, or the exact line `Docs: not needed — <reason, 10+ chars>` when nothing changed that a page covers, or `N/A` when no page covers this code at all. This is a separate gate from Step 4 — Step 4 catches *new undocumented files*, this line covers *existing documented files this PR's diff touches without updating their page* (checked by `scripts/check-docs-sync.mjs` in gate mode against the diff, not `--validate`).

Extra optional sections (reviewer focus notes, open questions from the ticket, app/platform-specific notes) can still follow after `## Docs` — Danger only requires the six above, it doesn't forbid more.

```bash
gh pr create --title "<title>" --body "$(cat <<'EOF'
## What this changes (plain English)
<3-5 plain-English sentences: what changes and why, no file names, acronyms expanded>

## Linear Issue
https://linear.app/shopit/issue/SHO-<number>

## Merge invariant
<one sentence on what must remain true for this to be safe, then risk areas/where reviewers should look>

## QA
<verification evidence: screenshots/recordings for anything user-visible, checks that ran, steps to verify — or exactly "Not visually verified — <reason>">

## Deployment Notes
<schema changes, new API keys, feature flags, deployment order, or N/A>

## Docs
<pages updated, or exactly "Docs: not needed — <reason>", or N/A>

## What should reviewers focus on?
<gotchas, non-obvious changes, trade-offs>

## Open Questions
<for each question from the ticket analysis:
  - ✅ **<question summary>** — <answer from comments, or "resolved: <decision>">
  - ❓ **<question summary>** — still open, needs resolution before/after merge>
or N/A if there were none>
EOF
)"
```

## Step 7 — Gate check (before or right after `gh pr create`)

Confirm the diff-based docs gate agrees with the `## Docs` line you wrote:

```bash
git fetch origin main --quiet
PR_BODY="$(gh pr view --json body -q .body)" node scripts/check-docs-sync.mjs --base origin/main --head HEAD
```

If it prints `FAIL`, either the `## Docs` opt-out line is missing/malformed (fix via `gh pr edit --body-file`, no push needed) or a listed page genuinely needs updating (requires a commit — do this now, before anyone reviews, not after).

## Step 8 — Return the PR URL

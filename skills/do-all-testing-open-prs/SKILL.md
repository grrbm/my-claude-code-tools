---
name: do-all-testing-open-prs
description: Find every open GitHub PR authored by the user in the current repo that doesn't yet have a manual-testing evidence section (screenshots + notes, like PR #590), then run the do-all-manual-testing skill sequentially across exactly that list. Use when the user asks to "do all the testing on my open PRs", "run manual testing on all my PRs that need it", "catch up my open PRs on manual testing", or similar — a batch, self-discovering wrapper around do-all-manual-testing rather than a one-PR-at-a-time request.
argument-hint: [owner/repo]
---

Discover the user's open PRs still missing manual-testing evidence, then hand the filtered list to `do-all-manual-testing` to actually execute: $ARGUMENTS

This skill is a thin composition, not a rewrite — it does the discovery/filtering, then delegates all of the actual simulator work, screenshotting, bug-fixing, and PR-body editing to `do-all-manual-testing`. Don't duplicate that skill's mechanics here; read it if you need to know how a step actually works.

## Step 1 — Resolve the repo and the author

`$ARGUMENTS` may optionally name a repo as `owner/repo`. If omitted, use the repo of the current working directory (the `gh` CLI infers this from the git remote automatically — no need to hardcode `ShopIt-LLC/shopit-monorepo`).

Per [[feedback_gh_token]], always `unset GITHUB_TOKEN` before any `gh` call in this skill — a stale PAT in the env silently overrides the logged-in keyring token, including for read calls that later feed a write.

```bash
unset GITHUB_TOKEN && gh pr list --author "@me" --state open -R <owner/repo> --json number,url,title,body
```

`--author "@me"` resolves to whichever account `gh` is authenticated as — this is what "authored by me" means here, not a hardcoded username.

If this returns zero PRs, tell the user there are no open PRs authored by them in this repo and stop — there is nothing to hand to `do-all-manual-testing`.

## Step 2 — Filter to PRs that don't already have a manual-testing report

For each PR from Step 1, inspect its `body` for an existing evidence section shaped like the one `do-all-manual-testing` itself produces (see that skill's Step 6, and the live example at https://github.com/ShopIt-LLC/shopit-monorepo/pull/590 — a `## Manual testing (<platform>)` heading followed by labeled screenshots and a `### Verified` list).

A PR counts as **already done** — and gets excluded from this run — only if its body contains:

1. A heading matching `## Manual testing` (case-insensitive, optionally followed by a parenthetical like `(iOS simulator + web)`), **and**
2. At least one `user-attachments/assets/` image URL (an actual uploaded screenshot, not just placeholder text) somewhere between that heading and the next `##` heading or end of body.

Don't confuse this with a `## How to manually test this` / `## Manual Testing` *instructions* heading (the one `do-all-manual-testing` reads as its input in its own Step 1) — that describes what to test, it isn't evidence that testing happened. The distinguishing signal is the uploaded screenshot URL, not the heading text alone: a PR can have testing instructions and still have zero evidence.

Keep every PR that fails this check — no such heading, a heading with no screenshots under it, or a body with neither. These are the PRs that still need testing.

If the filter removes every PR (all of the user's open PRs already have a report), tell the user that and stop.

## Step 3 — Run do-all-manual-testing across the filtered list, in order

Invoke the `do-all-manual-testing` skill, passing it the full URL list of the PRs that survived Step 2, oldest or lowest-numbered first (a stable, predictable order — don't shuffle). That skill already enforces strict one-PR-at-a-time processing internally (its own "Moving to the next PR" rule), including the simulator/backend collision-avoidance reasoning — don't re-implement that sequencing here, just hand it the right list.

Do this without asking for confirmation before starting — the user asking for "all open PRs" is the go-ahead for the batch; `do-all-manual-testing` itself is the thing that still stops on a case-by-case basis (e.g. its no-authenticated-browser fallback).

## Rules

- This skill only ever *discovers and filters*; all execution, bug-fixing, and PR-body editing happens inside `do-all-manual-testing` — don't take any simulator or `gh pr edit` action directly from here.
- If `gh pr list` or a `gh pr view`-equivalent body fetch fails for the repo, report that plainly and stop rather than guessing at a PR list.
- At the end, relay `do-all-manual-testing`'s own per-PR summary back to the user, plus one line up front noting how many open PRs were found vs. how many were excluded for already having a report.

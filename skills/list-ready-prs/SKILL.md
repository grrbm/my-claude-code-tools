---
name: list-ready-prs
description: List the user's own open GitHub PRs in the current repo, split into two groups — PRs they've personally reviewed and left a comment on themselves (ready to move forward on), and every other open PR they authored that has no self-review comment yet. Use when the user asks "/list-ready-prs", "which of my PRs are ready", "what have I actually reviewed of my own PRs", "what's left in my open PR backlog", or wants a quick status pass across their open PRs before merging, following up, or reprioritizing.
argument-hint: [owner/repo]
---

List the user's open PRs in the current repo, split by whether they've personally left a review or comment on it: $ARGUMENTS

This is a read-only lookup — it never posts, edits, or merges anything. It exists to answer "which of my open PRs have I actually looked at again after opening them, and which haven't I touched since?"

## Step 1 — Resolve the repo and the account

`$ARGUMENTS` may optionally name a repo as `owner/repo`. If omitted, use the repo of the current working directory — `gh` infers this from the git remote automatically, no need to hardcode one.

Per [[feedback_gh_token]], always `unset GITHUB_TOKEN` before any `gh` call here — a stale PAT in the env silently overrides the logged-in keyring token and can 404 on a private repo.

```bash
unset GITHUB_TOKEN && gh api user -q .login
```

This is the exact login to match against review/comment authors in Step 3 — `--author "@me"` below resolves the same identity for the list itself, but reviews/comments come back with a literal `login` string, so grab it once up front rather than re-resolving `@me` per PR.

## Step 2 — List the user's open PRs

```bash
unset GITHUB_TOKEN && gh pr list --author "@me" --state open -R <owner/repo> --json number,title,url,updatedAt,isDraft
```

If this returns zero PRs, say so plainly — "You have no open PRs in <owner/repo>." — and stop.

## Step 3 — Check each PR for a self-review or self-comment

For every PR from Step 2:

```bash
unset GITHUB_TOKEN && gh pr view <number> -R <owner/repo> --json reviews,comments
```

A PR counts as **ready** if the login from Step 1 appears as the author of at least one entry in `reviews` (a formal GitHub review — approve, comment, or request-changes) **or** `comments` (a plain issue-thread comment). Either counts; this is about whether the user has come back and said *something* on their own PR since opening it, not about which mechanism they used.

Everything else — no matching review, no matching comment, including PRs where only other people have commented — goes in the second group, regardless of draft status, CI state, or anything else. "Different states" here just means "not yet self-reviewed"; don't try to subdivide it further into draft/failing-checks/etc. unless the user asks for that.

## Step 4 — Report both lists

Use this shape, newest-updated first within each group:

```markdown
## Ready — self-reviewed (<count>)
- #<number> [<title>](<url>) — updated <relative time>

## Everything else, open (<count>)
- #<number> [<title>](<url>) — updated <relative time>
```

If a group is empty, still print its heading with `(0)` and a one-line note (e.g., "None of your open PRs have a self-review comment yet.") rather than omitting the section — the user is checking status across the whole backlog, and a silently-missing section reads as an error rather than a real zero.

## Rules

- Read-only: never call `gh pr comment`, `gh pr review`, `gh pr edit`, or anything else that mutates a PR from this skill.
- If a `gh pr view` call fails for one PR (deleted, permissions changed mid-run), drop that PR from both lists, note it was skipped and why, and keep going — don't abort the whole report over one bad PR.

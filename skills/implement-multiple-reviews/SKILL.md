---
name: implement-multiple-reviews
description: Sequentially implement pending review changes across multiple GitHub PRs, committing and pushing after each one. Use when asked to implement reviews on several PRs at once, e.g. "implement review changes on PR #1, #2, #3" or given a list of PR URLs to address in bulk. Runs the implement-review skill for each PR one at a time (never in parallel, to avoid branch-checkout/working-tree collisions), then commits and pushes before moving to the next PR — unlike implement-review alone, which never commits or pushes.
argument-hint: <pr-url-1> <pr-url-2> [...]
allowed-tools: Bash(gh *), Bash(git *), Read, Glob, Grep, Edit, Write
---

Implement pending review changes across these PRs, one at a time: $ARGUMENTS

This skill composes the existing `implement-review` skill with a commit+push step it doesn't do on its own. Invoking it via the Skill tool rather than copying its steps here means this pipeline automatically stays in sync if `implement-review` is ever updated.

## Step 1 — Parse the PR list

Split `$ARGUMENTS` on whitespace and/or commas into individual PR URLs. Validate each looks like a GitHub PR URL (`https://github.com/<owner>/<repo>/pull/<number>`). If none are found, stop and ask the user for URLs.

## Step 2 — Process each PR strictly in order

For each PR URL, in the order given:

1. **Implement the review.** Invoke the `implement-review` skill via the Skill tool, passing this PR's URL as its argument. Let it run to completion — it checks out the PR's branch, reads all comments/reviews, implements pending items, and posts its own summary comment to the PR. It does not commit or push, by design.

2. **Check for changes.** Run `git status --porcelain`. If it's empty, nothing was pending for this PR — skip to step 4 for this PR (nothing to commit/push).

3. **Commit and push.**
   - Stage exactly the files `implement-review` modified, listed individually via `git add <file1> <file2> ...` — never `git add -A` or `git add .`.
   - Derive the commit message using the [git commit convention](../../ai/git-conventions.md): `<type>(<scope>): SHO-<number> <description>`. Infer the SHO number from the branch name, the scope from the changed files, and pick whichever `type` (usually `fix`) matches what was actually changed. Base the description on the summary `implement-review` just posted to the PR, e.g. `address pr review — <short summary>`. Lowercase, no trailing period, no `Co-Authored-By` line, no Claude attribution.
   - Write the message to a scratch file with the Write tool (not inline in the Bash command) and commit with `git commit -F <path>` — avoids quoting/heredoc issues.
   - Push to the PR's branch: `git push`.

4. **Move to the next PR only after this one is fully committed and pushed** (or confirmed to have nothing pending). Do not start the next PR's `implement-review` pass until the current PR's working tree is clean — this is what prevents branch checkouts and uncommitted edits from colliding across PRs.

## Rules

- Never run PRs in parallel. `implement-review` checks out each PR's branch directly in the shared working directory (`gh pr checkout`) and leaves changes uncommitted until this skill commits them — running two PRs at once means two branch checkouts and two sets of uncommitted edits fighting over the same working tree. The only way to safely parallelize this would be to give each PR its own git worktree (a separate checkout of its branch backed by the same `.git`) and process each independently — real added complexity (worktree setup/teardown, per-worktree dependency installs, cleanup on failure) for a handful of PRs that mostly wait on `gh` API round-trips anyway. Not worth it here — go sequential.
- Do not ask for confirmation between PRs — process the whole list unattended once started.
- If `implement-review` fails outright for one PR (bad URL, PR not found, checkout fails), report the failure for that PR specifically and continue on to the next one rather than aborting the whole batch.
- If a PR has nothing pending, say so plainly in the final summary rather than silently skipping it.
- Never force-push.
- Never prefix `git`/`gh` commands with `cd /path/to/repo &&` — the working directory is already the project root.
- At the end, report one line per PR: implemented+pushed, nothing pending, or failed (with reason).

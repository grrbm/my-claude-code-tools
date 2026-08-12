---
name: self-review-multiple
description: Sequentially self-review multiple GitHub PRs, waiting for each PR's entire self-review chain — including any auto-implemented rounds spawned in separate terminals — to finish before starting the next. Use when asked to self-review several PRs at once, e.g. "self-review PR #1, #2, #3" or given a list of the user's own PR URLs to self-review in bulk.
argument-hint: <pr-url-1> <pr-url-2> [...]
allowed-tools: Bash(gh *), Read
---

Self-review these PRs, one at a time, waiting for each PR's entire self-review chain to finish before starting the next: $ARGUMENTS

This skill composes the existing `self-review-pr` skill — it has no review logic of its own. Invoking it via the Skill tool rather than copying its steps here means this pipeline automatically stays in sync if `self-review-pr` (or `implement-self-review`, which it can chain into) is ever updated.

## Step 1 — Parse the PR list

Split `$ARGUMENTS` on whitespace and/or commas into individual PR URLs. Validate each looks like a GitHub PR URL (`https://github.com/<owner>/<repo>/pull/<number>`). If none are found, stop and ask the user for URLs.

## Step 2 — Process each PR strictly in order

For each PR URL, in the order given:

1. **Run the self-review.** Invoke the `self-review-pr` skill via the Skill tool, passing this PR's URL as its argument. Let it run to completion: it reads the diff and comments, writes the review to `/private/tmp/self-review-<project-slug>.md`, and then branches —
   - if nothing blocking/important was found, it posts a short "nothing left" comment and stops there, or
   - otherwise it invokes `implement-self-review` directly, which commits, pushes, and then (capped at 6 rounds) opens a **separate, fresh terminal** to kick off the next round against the same PR.

2. **Wait for this PR's entire chain to finish before moving to the next PR.** This is the part that matters: because `implement-self-review` can hand off to a new terminal that keeps running `git`/`gh` commands against this same shared working directory after this skill's Step 1 call already returned, starting the next PR too early risks two `claude` processes doing git operations in the same working tree at once. Detect completion using the exact round-counter file `self-review-pr`/`implement-self-review` already maintain: `/tmp/.claude-self-review-rounds-<owner>-<repo>-<number>` (owner/repo with the `/` replaced by `-`; `<number>` is this PR's number).
   - Immediately after the Step 1 call returns, check with the `Read` tool whether this file exists.
     - If it does **not** exist: the review came back completely clean on the first pass — `self-review-pr` never invoked `implement-self-review`, no terminal was opened, and the chain is already fully finished. Move on to the next PR right away.
     - If it **does** exist: a chain is in progress (or a background terminal just finished a round and is about to open the next one) — proceed to wait.
   - Wait for the chain to finish. It's done once the counter file is either gone/empty (`self-review-pr` clears it the moment a round comes back clean) or its value exceeds 6 (`implement-self-review`'s own `MAX_AUTO_ROUNDS` cap — at that point it stops without opening another terminal). Run a single Bash command in the background for this rather than polling manually — you'll be notified when it exits:
     ```bash
     until [ ! -s /tmp/.claude-self-review-rounds-<owner>-<repo>-<number> ] || [ "$(cat /tmp/.claude-self-review-rounds-<owner>-<repo>-<number> 2>/dev/null)" -gt 6 ]; do sleep 60; done
     ```
     Substitute the real owner/repo/number, and pass `run_in_background: true`. Do not sleep-poll this file yourself in a loop of your own turns — wait for the background command's completion notification.
   - Safety valve: cap the wait at 2 hours total, in case something got silently stuck (e.g. the Terminal Bridge extension failing to open the next terminal). If it's still unresolved after that, stop waiting, note it plainly in this PR's line of the final report, and proceed to the next PR anyway rather than hanging the whole batch indefinitely.

3. **Move to the next PR only after this one's chain has actually finished** (or was confirmed already-finished in step 2's first check, or hit the 2-hour safety valve). Do not start the next PR's `self-review-pr` pass while a background terminal might still be mid-round on the current one.

If this is the last PR (or the only PR given), still perform the wait — unlike `do-everything`, there is no next PR's own git operations that skipping the wait would protect, but the final summary should still accurately reflect whether the chain finished, hit the round cap, or timed out.

## Rules

- Never run PRs in parallel, and never start PR N+1 while PR N's self-review chain is still running in another terminal against the shared working directory.
- Do not ask for confirmation between PRs — process the whole list unattended once started.
- If `self-review-pr` fails outright for one PR (bad URL, PR not found), report the failure for that PR specifically and continue on to the next one rather than aborting the whole batch.
- Never prefix `git`/`gh` commands with `cd /path/to/repo &&` — the working directory is already the project root.
- Never force-push, and never raise or bypass the 6-round auto-continue cap.
- At the end, report one line per PR: nothing pending (clean on first pass), implemented+pushed (with how many rounds it took, if known), failed (with reason), or timed out waiting after 2 hours.

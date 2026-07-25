---
name: do-everything
description: Runs the full ticket-to-review pipeline for one or more Linear issues, fully automatically with no confirmation between steps — for each issue, in order, implements the ticket (linear-implement-task), opens the resulting branch as a draft PR (create-pr), then immediately triggers a self-review pass on that PR (self-review-pr), which in turn auto-implements its own findings. Use whenever the user gives one or more Linear issue URLs and asks to "do everything", "handle this end-to-end", "implement this and open a draft PR and review it", "take this ticket all the way", "do everything for these tickets", or otherwise wants the implement → draft PR → self-review chain run in one go instead of driving each step by hand. Multiple tickets are processed strictly one at a time, never in parallel.
argument-hint: <linear-issue-url-1> [<linear-issue-url-2> ...]
---

Run this exact three-step pipeline for each Linear issue below, one ticket fully to completion before starting the next: $ARGUMENTS

This skill has no steps of its own — it's a fixed composition of three existing skills, invoked in sequence via the Skill tool. Composing them this way, instead of copying their internal steps here, means this pipeline automatically stays in sync if `linear-implement-task`, `create-pr`, or `self-review-pr` are ever updated.

## Step 0 — Parse the ticket list

Split `$ARGUMENTS` on whitespace and/or commas into individual Linear issue URLs. If only one URL is given, the pipeline below just runs once. If none are found, stop and ask the user for a Linear issue URL.

## For each ticket, in order, run:

### Step 1 — Implement the ticket

Invoke the `linear-implement-task` skill, passing this ticket's Linear issue URL as its argument. Let it run to completion: parsing the issue, reading every comment (comments often supersede the original description), creating the branch from a freshly-pulled `main`, and implementing the feature.

### Step 2 — Open a draft PR

Once implementation is done, invoke the `create-pr` skill. Pass it an argument that explicitly asks for a **draft** PR (e.g. `"draft PR for the branch just implemented"`) — `create-pr`'s own template does not default to draft, so this instruction is what makes it add `--draft` to the `gh pr create` call. Capture the PR URL it returns; the next step needs it.

### Step 3 — Self-review the PR

Once the PR is open, invoke the `self-review-pr` skill, passing that PR URL as its argument. Let it run to whatever depth it decides on its own — including its own automatic chain into `implement-self-review` and any further self-review rounds it schedules. That branching logic lives entirely inside `self-review-pr`; don't duplicate or second-guess it here.

## Moving to the next ticket

`self-review-pr`'s own auto-continue chain (via `implement-self-review`) can open a **separate, fresh terminal** — with no context from this session — to keep running further self-review rounds on the current ticket's PR after this skill's Step 3 call already returns. Critically, that terminal runs `claude` against the **same shared working directory** this skill uses for every ticket (there's no per-ticket worktree isolation here). If this skill started implementing ticket 2 while that terminal is still mid-round on ticket 1, two `claude` processes would be doing git operations (checkouts, commits) in the same working directory at the same time — exactly the collision this pipeline must not risk. So: before moving on to the next ticket, wait until this ticket's entire self-review chain — however many rounds it takes, potentially across several separate terminals — has actually finished.

Detect that using the exact same round-counter file `self-review-pr`/`implement-self-review` already maintain for this purpose: `/tmp/.claude-self-review-rounds-<owner>-<repo>-<number>` (owner/repo with the `/` between them replaced by `-`; `<number>` is the PR number Step 2's URL contains).

1. Immediately after Step 3's `self-review-pr` call returns, check with the `Read` tool whether this file exists.
   - If it does **not** exist: round 1 came back completely clean (nothing blocking or important) — `self-review-pr` never invoked `implement-self-review`, no further terminal was opened, and the chain is already fully finished. Move on to the next ticket right away.
   - If it **does** exist: a chain is in progress (or a background terminal just finished a round and is about to open the next one) — proceed to step 2.
2. Wait for the chain to finish. It's done once the counter file is either gone/empty (`self-review-pr` clears it the moment a round comes back clean) or its value exceeds 6 (`implement-self-review`'s own `MAX_AUTO_ROUNDS` cap — at that point it stops without opening another terminal). Run a single Bash command in the background for this rather than polling manually — you'll be notified when it exits:
   ```bash
   until [ ! -s /tmp/.claude-self-review-rounds-<owner>-<repo>-<number> ] || [ "$(cat /tmp/.claude-self-review-rounds-<owner>-<repo>-<number> 2>/dev/null)" -gt 6 ]; do sleep 60; done
   ```
   Substitute the real owner/repo/number, and pass `run_in_background: true`. Do not sleep-poll this file yourself in a loop of your own turns — wait for the background command's completion notification.
3. Safety valve: cap the wait at 2 hours total, in case something got silently stuck (e.g. the Terminal Bridge extension failing to open the next terminal). If it's still unresolved after that, stop waiting, note it plainly in this ticket's line of the final report (e.g. "self-review chain for PR #X hadn't finished after 2 hours — moved on without waiting further"), and proceed to the next ticket anyway rather than hanging the whole batch indefinitely.

If this is the last ticket (or the only ticket given), skip this wait — there's no next ticket's implementation step it could collide with, so let the chain trail off in the background exactly as it already does for a single-ticket run today.

## Rules

- Do not ask for confirmation before, between, or after any step, for any ticket — the entire point of this skill is to run the whole pipeline unattended.
- Never process tickets in parallel, and never start ticket N+1 while ticket N's self-review chain (see above) is still running in another terminal against the shared working directory. Do not skip a step or reorder steps within a ticket, even if a shortcut looks available (e.g. don't create the PR before the implementation is actually committed).
- If a step fails outright for a ticket — `linear-implement-task` can't reach the Linear API, or `create-pr` finds nothing to commit — report exactly what failed and why for that ticket, then continue on to the next ticket rather than aborting the whole batch. Don't silently continue to that ticket's next step with nothing for it to act on.
- If `linear-implement-task` reports an existing local branch for the same issue, follow its own guidance (mention it, don't duplicate) rather than treating that as a pipeline failure.
- At the end, report one line per ticket: the PR URL opened (if the pipeline reached Step 2), or exactly what failed and at which step. Note for each non-final ticket whether its self-review chain finished cleanly, hit the round cap, or timed out after 2 hours.

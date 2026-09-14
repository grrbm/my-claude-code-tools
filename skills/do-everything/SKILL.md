---
name: do-everything
description: Runs the ticket-to-PR pipeline for one or more Linear issues, fully automatically with no confirmation between steps — for each issue, in order, implements the ticket (linear-implement-task) and opens the resulting branch as a draft PR (create-pr). By default it stops there. Pass the literal flag `with-self-reviews` as the first argument to also run a self-review pass on each PR (self-review-pr), which in turn auto-implements its own findings. Use whenever the user gives one or more Linear issue URLs and asks to "do everything", "handle this end-to-end", "implement this and open a draft PR", "take this ticket all the way", "do everything for these tickets", or otherwise wants the implement → draft PR chain (optionally → self-review) run in one go instead of driving each step by hand. Multiple tickets are processed strictly one at a time, never in parallel.
argument-hint: "[with-self-reviews] <linear-issue-url-1> [<linear-issue-url-2> ...]"
---

Run this pipeline for each Linear issue below, one ticket fully to completion before starting the next: $ARGUMENTS

This skill has no steps of its own — it's a fixed composition of existing skills, invoked in sequence via the Skill tool. Composing them this way, instead of copying their internal steps here, means this pipeline automatically stays in sync if `linear-implement-task`, `create-pr`, or `self-review-pr` are ever updated.

## Step 0 — Parse the arguments

1. **Detect the self-review flag.** If the first whitespace-separated token of `$ARGUMENTS` is exactly `with-self-reviews`, set "self-reviews: ON" for this whole run and remove that token from the argument list. Otherwise self-reviews are **OFF** (the default) — Step 3 and the entire "Moving to the next ticket" wait are skipped for every ticket. The flag is only recognised as the very first token; a bare `with-self-reviews` appearing later is not a valid Linear URL and Step 0's URL parse will surface it as an error.
2. **Parse the ticket list.** Split what remains of `$ARGUMENTS` on whitespace and/or commas into individual Linear issue URLs. If only one URL is given, the pipeline below just runs once. If none are found, stop and ask the user for a Linear issue URL.

## For each ticket, in order, run:

### Step 1 — Implement the ticket

Invoke the `linear-implement-task` skill, passing this ticket's Linear issue URL as its argument. Let it run to completion: parsing the issue, reading every comment and attachment (comments often supersede the original description, and design references — mockups, Figma links, screenshots — are just as often posted as a comment as they are in the description), creating the branch from a freshly-pulled `main`, and implementing the feature to match any designs found precisely.

### Step 2 — Open a draft PR

Once implementation is done, invoke the `create-pr` skill. Pass it an argument that explicitly asks for a **draft** PR (e.g. `"draft PR for the branch just implemented"`) — `create-pr`'s own template does not default to draft, so this instruction is what makes it add `--draft` to the `gh pr create` call. Capture the PR URL it returns.

**If self-reviews are OFF (the default): the ticket is done here.** Record the PR URL and move straight to the next ticket's Step 1 — there is no separate terminal or self-review chain to wait on, and tickets are already processed one at a time in this session, so the next `linear-implement-task` cannot collide with anything.

### Step 3 — Self-review the PR *(only when `with-self-reviews` was passed)*

Skip this step entirely unless Step 0 turned self-reviews ON.

Once the PR is open, invoke the `self-review-pr` skill, passing that PR URL as its argument. Let it run to whatever depth it decides on its own — including its own automatic chain into `implement-self-review` and any further self-review rounds it schedules. That branching logic lives entirely inside `self-review-pr`; don't duplicate or second-guess it here.

## Moving to the next ticket *(only when `with-self-reviews` was passed)*

This whole section applies only when self-reviews are ON. With self-reviews OFF there is no chain to wait for — see the note at the end of Step 2.

`self-review-pr`'s own auto-continue chain (via `implement-self-review`) can open a **separate, fresh terminal** — with no context from this session — to keep running further self-review rounds on the current ticket's PR after this skill's Step 3 call already returns. Critically, that terminal runs `claude` against the **same shared working directory** this skill uses for every ticket (there's no per-ticket worktree isolation here). If this skill started implementing ticket 2 while that terminal is still mid-round on ticket 1, two `claude` processes would be doing git operations (checkouts, commits) in the same working directory at the same time — exactly the collision this pipeline must not risk. So: before moving on to the next ticket, wait until this ticket's entire self-review chain — however many rounds it takes, potentially across several separate terminals — has actually finished.

Detect that using the deterministic, PR-scoped **chain-completion marker** `self-review-pr`/`implement-self-review` write on whichever exit path ends the chain (clean first pass, every-item-deferred, 6-round cap, terminal-bridge-unreachable — all write it; opening a next round does not): `/tmp/.claude-self-review-chain-done-<owner>-<repo>-<number>` (owner/repo with the `/` between them replaced by `-`; `<number>` is the PR number Step 2's URL contains). Do not infer completion from the round-counter file — a clean first pass never creates it.

Before Step 3's `self-review-pr` call, `rm -f` this marker (and `/tmp/.claude-self-review-rounds-<owner>-<repo>-<number>`) so neither is stale.

1. Immediately after Step 3's `self-review-pr` call returns, check with the `Read` tool whether the marker exists.
   - If it **does**: the chain finished entirely in-process (round 1 clean, or every item deferred, with no further terminal opened). Move on to the next ticket right away.
   - If it does **not**: `implement-self-review` pushed fixes and opened a next-round terminal that's still running — proceed to step 2.
2. Wait for the marker to appear. Run a single Bash command in the background rather than polling manually — you'll be notified when it exits:
   ```bash
   end=$(( $(date +%s) + 7200 )); until [ -e /tmp/.claude-self-review-chain-done-<owner>-<repo>-<number> ] || [ "$(date +%s)" -ge "$end" ]; do sleep 15; done
   ```
   Substitute the real owner/repo/number, and pass `run_in_background: true`. Do not sleep-poll yourself in a loop of your own turns — wait for the background command's completion notification.
3. The 7200-second bound is only a safety valve for a genuinely stuck chain (e.g. the Terminal Bridge failing to open a follow-up round's terminal, so no one writes the marker). If the loop hits it with no marker, stop waiting, note it plainly in this ticket's line of the final report (e.g. "self-review chain for PR #X hadn't finished after 2 hours — moved on without waiting further"), and proceed to the next ticket anyway rather than hanging the whole batch indefinitely.

If this is the last ticket (or the only ticket given), skip this wait — there's no next ticket's implementation step it could collide with, so let the chain trail off in the background exactly as it already does for a single-ticket run today.

## Rules

- Do not ask for confirmation before, between, or after any step, for any ticket — the entire point of this skill is to run the whole pipeline unattended. This includes not asking whether to run self-reviews: the `with-self-reviews` flag is the only switch, and its absence means "no".
- Never process tickets in parallel. When self-reviews are ON, never start ticket N+1 while ticket N's self-review chain (see above) is still running in another terminal against the shared working directory. Do not skip a step or reorder steps within a ticket, even if a shortcut looks available (e.g. don't create the PR before the implementation is actually committed).
- If a step fails outright for a ticket — `linear-implement-task` can't reach the Linear API, or `create-pr` finds nothing to commit — report exactly what failed and why for that ticket, then continue on to the next ticket rather than aborting the whole batch. Don't silently continue to that ticket's next step with nothing for it to act on.
- If `linear-implement-task` reports an existing local branch for the same issue, follow its own guidance (mention it, don't duplicate) rather than treating that as a pipeline failure.
- At the end, report one line per ticket: the PR URL opened (if the pipeline reached Step 2), or exactly what failed and at which step. When self-reviews were ON, also note for each non-final ticket whether its self-review chain finished cleanly, hit the round cap, or timed out after 2 hours.

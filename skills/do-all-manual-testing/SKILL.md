---
name: do-all-manual-testing
description: Given one or more GitHub PR URLs, actually performs the on-device manual testing described in each PR's own "How to manually test this" section — drives the iOS Simulator through every step, takes evidence screenshots, catches and fixes any real bugs found along the way, then gets those screenshots formatted into the PR description. Use whenever the user gives one or more PR URLs and asks to "do the manual testing", "test this on the simulator and screenshot it", "run through the manual test steps and get screenshots into the PR", "do all the manual testing for these PRs", or otherwise wants the how-to-test steps actually carried out on device rather than just described. Multiple PRs are processed strictly one at a time, never in parallel — driving two PRs' worth of simulator/backend state at once is a real collision risk, not just a style preference.
argument-hint: <pr-url-1> [<pr-url-2> ...]
---

Actually perform the manual testing described in each PR below, one PR fully to completion before starting the next: $ARGUMENTS

This skill is a composition, not a rewrite, of two existing skills' techniques — it invokes `ios-simulator` for the mechanics of driving the simulator, and `format-pr-screenshots` for the final labeling/table/apply step, rather than duplicating either skill's instructions here. That keeps this pipeline in sync automatically if either of those skills changes, the same reason `do-everything` composes `linear-implement-task`/`create-pr`/`self-review-pr` instead of copying their steps.

## Step 0 — Parse the PR list

Split `$ARGUMENTS` on whitespace and/or commas into individual PR URLs. If only one is given, the pipeline below just runs once. If none are found, stop and ask the user for a PR URL.

## For each PR, in order, run:

### Step 1 — Read the PR's own testing instructions

```bash
gh pr view <pr> --json number,url,title,body,headRefName -R <owner>/<repo>
```

Find the section describing manual testing. `create-pr`'s template guarantees a `## How to manually test this` heading on every PR opened through it, but be flexible the same way `format-pr-screenshots` is about its own heading — also match `## Manual Testing`, `## How to Test`, `## Testing`, case-insensitively. The section runs from that heading to the next `##` heading or end of body.

If no such section exists, or it's empty/just says "N/A", tell the user plainly and move on to the next PR — don't invent test steps for a PR that never described any, and don't let one PR's missing section abort the whole batch.

### Step 2 — Separate what's actually testable on a simulator

A "how to manually test this" section is often a mix of instructions, not all of which belong here:

- **On-device steps** — "long-press X", "tap Y", "load the Z screen and verify W" — these are what this skill exists to carry out.
- **Automated-test pointers** — "run the mapper unit tests", "the db-layer test proves X" — these already ran in CI/locally; re-running them isn't manual testing and produces no screenshot. Skip them here.
- **Out-of-scope notes** — "this needs a production sync, out of scope for this PR" — skip, don't attempt.

Pull out only the on-device steps as your scenario list for this PR. If none remain after filtering, tell the user this PR's testing section is entirely non-visual (unit tests / deferred production steps) and move to the next PR — there's nothing to screenshot.

### Step 3 — Set up a dedicated, collision-proof screenshot folder

Create `<scratchpad-dir>/manual-testing-<owner>-<repo>-<pr-number>/`, where `<scratchpad-dir>` is the scratchpad directory named in your system prompt for this session. Naming it by owner/repo/PR number — not just a generic "screenshots" folder — is what lets this skill process several PRs (from the same or different repos) across a batch without one PR's images ever landing in another's folder.

### Step 4 — Drive the simulator through each scenario

Invoke the `ios-simulator` skill to load its operating rules (installation check, `agent-device open`, don't-probe-first guidance, help topics) before touching the simulator. Then, for each on-device scenario from Step 2:

1. Perform the described interaction with `agent-device` (open the app, navigate, tap, long-press, scroll — whatever the scenario calls for).
2. Take a screenshot documenting the resulting state, saved into this PR's folder with a name that says what it shows, not just a counter — `before-no-quickadd.png` beats `screenshot-1.png` when you're the one who has to explain the sequence later, and it's what makes the folder legible to the human reviewing it before upload.
3. If the scenario describes a before/after or success/failure comparison, make sure both halves actually get captured — a single screenshot proving only the "after" state is weaker evidence than the PR itself is asking for.

Setup note: getting the simulator to actually exercise the PR's change usually means the branch's code needs to be live somewhere the running app can reach — check out the PR's branch (`gh pr checkout`) if a rebuild is needed, and for a Convex/backend change, push it with a single clean `bunx convex dev --once` (not backgrounded — a backgrounded watcher left running from an earlier step can race a later push and silently revert it, which is exactly the kind of thing to check for with `ps aux | grep convex` before pushing). Confirm which simulator app build is actually installed and what backend it's pointed at before assuming a screenshot reflects the PR under test.

### Step 5 — If you find a real bug, fix it before you screenshot past it

This is the rule this skill exists to enforce, not an aside: if a scenario throws an error, crashes, shows data that's wrong, or just doesn't do what the PR says it does, that is a finding, not a screenshot. Stop taking screenshots for this PR, and:

1. Investigate — check `bunx convex logs` for backend errors, read the relevant code, reproduce narrowly if needed.
2. Fix it in the codebase.
3. Verify the fix — typecheck, run the relevant tests, and redeploy/rebuild whatever's needed for the simulator to actually pick up the change (see Step 4's setup note).
4. Resume the scenario from where the bug interrupted it, and re-capture any screenshot that would have shown the broken state — a screenshot of a bug you already fixed is misleading evidence, not honest documentation.

Keep a short running note of what broke and how it was fixed — the end-of-batch report (see Rules below) needs it. A PR's own manual-test steps are a genuine test of the code, not just a script to screenshot through; treat a failure there the way you'd treat a failing test, not as an obstacle to route around.

### Step 6 — Hand the folder to the user

```bash
open <the PR's screenshot folder>
```

Then tell the user something like: "Screenshots for PR #<number> are ready in <folder> — please upload them to the PR description, then let me know when you're done."

### Step 7 — Wait for explicit confirmation

Do not proceed to Step 8 on your own judgment about elapsed time or silence. Wait for the user to actually say they've uploaded the images.

### Step 8 — Verify the upload actually landed

Once the user confirms, re-fetch the PR body and check that the media section now genuinely contains new image links (`user-attachments/assets/` URLs or `<img>`/markdown-image tags that weren't there in Step 1's copy of the body) — don't take the user's word alone as proof, the same way `format-pr-screenshots` never trusts an unlabeled wall of images without looking. If nothing new is there, say so and wait for the user again rather than proceeding to format an unchanged section.

### Step 9 — Format the screenshots

Invoke the `format-pr-screenshots` skill, passing this PR's URL as its argument. Let it run its own full process — reading the body, viewing each image to write accurate labels, laying out the table, reassembling the full body untouched outside that section, and previewing + confirming with the user before it applies anything. Don't duplicate or second-guess that skill's steps here; it already owns this problem end to end, including its own apply-confirmation gate.

## Moving to the next PR

Do not begin Step 3 (or any simulator interaction) for PR N+1 until PR N has cleared Step 9. This mirrors why `do-everything` waits out a ticket's whole self-review chain before starting the next one: the simulator, the checked-out branch, and whatever backend deployment is live are all shared, mutable state. A bug fix mid-way through PR N's testing might touch files or a deployment PR N+1 also depends on — running them concurrently risks one PR's fix or checkout silently clobbering the other's in-progress test.

## Rules

- Do not ask for confirmation before starting a PR, between its steps, or before opening its folder — the point of this skill is to actually run the testing, not describe it. The two points that *do* require explicit confirmation are structural, not optional: waiting for the user's upload (Step 7) and `format-pr-screenshots`' own apply gate (Step 9) — both mutate or depend on state only the user can complete.
- Never skip Step 5's bug-fix-first rule to keep a batch moving faster. A screenshot of broken behavior isn't a faster path through this pipeline, it's a wrong one.
- If a PR fails outright — can't be fetched, has no testable manual-test section, or the simulator/backend setup can't be made to reflect the PR's branch — report exactly what failed and why for that PR, then continue to the next PR rather than aborting the whole batch.
- At the end, report one line per PR: whether it completed cleanly (with the final PR URL), what bugs — if any — were found and fixed along the way, or exactly what failed and at which step.

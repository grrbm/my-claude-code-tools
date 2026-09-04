---
name: do-all-manual-testing
description: Given one or more GitHub PR URLs, actually performs the on-device manual testing described in each PR's own "How to manually test this" section — drives the iOS Simulator through every step, takes evidence screenshots, catches and fixes any real bugs found along the way, then uploads those screenshots into the PR description itself — labeled, laid out, and rendering inline — with no manual drag-and-drop hand-off. Use whenever the user gives one or more PR URLs and asks to "do the manual testing", "test this on the simulator and screenshot it", "run through the manual test steps and get screenshots into the PR", "do all the manual testing for these PRs", or otherwise wants the how-to-test steps actually carried out on device rather than just described. Multiple PRs are processed strictly one at a time, never in parallel — driving two PRs' worth of simulator/backend state at once is a real collision risk, not just a style preference.
argument-hint: <pr-url-1> [<pr-url-2> ...]
---

Actually perform the manual testing described in each PR below, one PR fully to completion before starting the next: $ARGUMENTS

This skill is a composition, not a rewrite, of two existing skills' techniques — it invokes `ios-simulator` for the mechanics of driving the simulator, and `post-screenshots-to-pr` for the mechanics of minting GitHub asset URLs from the screenshots and embedding them in the PR body, rather than duplicating either skill's instructions here. That keeps this pipeline in sync automatically if either of those skills changes, the same reason `do-everything` composes `linear-implement-task`/`create-pr`/`self-review-pr` instead of copying their steps.

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

### Step 6 — Post the screenshots into the PR description yourself

Do not hand the folder to the user to drag-and-drop. Upload the screenshots and write the labeled section yourself, using `post-screenshots-to-pr`'s mechanics. Read that skill's SKILL.md for the exact `agent-browser` gotchas (dedicated Chrome profile, per-issue input ids, upload-mints-the-URL-even-if-you-discard-the-editor, `gh` is the only writer). The shape for this skill's use:

1. **Canonical body via `gh`** — `unset GITHUB_TOKEN && gh pr view <number> -R <owner>/<repo> --json body -q .body > <tmp>/body-original.md`. This is the source Step 6.6 rebuilds from; never read the body back out of the browser textarea.
2. **Label each screenshot** — `Read` each PNG and write a short factual label (2–5 words: what is on screen — "Thank <sender> CTA", "Thanked state, dark mode", "Sender inbox: one folded row"). You took these shots minutes ago and know exactly what each proves — no need to re-download or re-derive.
3. **Authenticated browser session** — `agent-browser close --all`, then drive everything from one shell with the dedicated profile: `agent-browser --profile ~/.agent-browser-profiles/github open "<PR_URL>"`. Confirm `meta[name=user-login]` is the user's login, not `null`. If that profile isn't logged in (or doesn't exist), that's the fallback case below — don't try other Chrome profiles blind.
4. **Upload** — open the description's editor (its kebab `summary.timeline-comment-action` → the `Edit` dropdown item), enumerate inputs to get the per-issue `fc-issue-<N>-body` file input id, then `agent-browser upload "#fc-issue-<N>-body" <abs-path-1.png> <abs-path-2.png> …` (one file per call is the reliable form; a multi-arg call sometimes silently no-ops). Each upload inserts an `<img … alt="<filename-without-ext>" src="https://github.com/user-attachments/assets/<uuid>">` at the cursor — the asset is minted on GitHub's CDN immediately and persists even if the editor is never saved.
5. **Collect the URLs** — read them out of the textarea value with a regex, mapping each to its file by the `alt=` filename the uploader set (more robust than upload order). Then **accept the "discard unsaved changes" dialog** (`agent-browser dialog accept`) — the browser must not save the top-stacked mess it just built; `gh` writes the real body.
6. **Assemble the new body in Python** = `body-original.md` verbatim + a new `## Manual testing (<platform>)` section appended after the last existing section:
   - a 2–4 sentence factual intro: which backend/deployment the app was pointed at, which accounts, and what was *not* re-run (e.g. reused a pre-existing claimed gift instead of re-running send+claim);
   - the screenshots as a markdown table — labels as column headers, `<img src="<url>" width="180" alt="<label>">` in the row below, **≤4 columns per table**, split into multiple table blocks if there are more than ~5 so no block needs horizontal scrolling;
   - a short **Verified** bullet list (what the run actually confirmed) and, if applicable, a **Not verified on simulator** list (e.g. push delivery — APNs doesn't reach the simulator) and any bug found + fixed.
   Sanity-check the assembled file: first char isn't `"`, zero literal `\n`, `user-attachments/assets/` count == screenshot count, first line still the PR's original first heading.
7. **Write and verify** — `unset GITHUB_TOKEN && gh pr edit <number> -R <owner>/<repo> --body-file <tmp>/body-new.md`, then `agent-browser open "<PR_URL>"` and confirm every `.markdown-body img` from your section has `complete && naturalWidth > 0`. `agent-browser close --all` when done.

Do this without asking for confirmation — it only ever *appends* a `## Manual testing` section and leaves every other part of the body byte-for-byte unchanged, and the user asked for the testing to be carried out end to end. Do not post a comment, change the title, touch other sections, or push.

**Fallback (no authenticated browser profile, or the user declines to set one up):** `open` the screenshot folder, `SendUserFile` the images, and give the user the PR edit URL plus the exact `## Manual testing` block (table + `<img>` tags with local paths for them to swap) — then stop. Don't fabricate an upload path.

## Moving to the next PR

Do not begin Step 3 (or any simulator interaction) for PR N+1 until PR N has cleared Step 6. This mirrors why `do-everything` waits out a ticket's whole self-review chain before starting the next one: the simulator, the checked-out branch, and whatever backend deployment is live are all shared, mutable state. A bug fix mid-way through PR N's testing might touch files or a deployment PR N+1 also depends on — running them concurrently risks one PR's fix or checkout silently clobbering the other's in-progress test.

## Rules

- Do not ask for confirmation before starting a PR, between its steps, before driving the simulator, or before posting the screenshots into the PR (Step 6) — the point of this skill is to actually run the testing and land the evidence, not describe it or hand it back. Step 6 only ever appends a `## Manual testing` section and never touches the rest of the body, so it needs no gate; the one place that genuinely stops is Step 6's fallback, when there's no authenticated browser session to mint the upload.
- Never skip Step 5's bug-fix-first rule to keep a batch moving faster. A screenshot of broken behavior isn't a faster path through this pipeline, it's a wrong one.
- If a PR fails outright — can't be fetched, has no testable manual-test section, or the simulator/backend setup can't be made to reflect the PR's branch — report exactly what failed and why for that PR, then continue to the next PR rather than aborting the whole batch.
- At the end, report one line per PR: whether it completed cleanly (with the final PR URL), what bugs — if any — were found and fixed along the way, or exactly what failed and at which step.

---
name: implement-multiple-reviews
description: Implement pending review changes on one or more GitHub PRs — reads all comments and reviews, implements unresolved items, posts a summary comment, then commits and pushes — with an optional self-review pass per PR. Runs entirely inside a dedicated git worktree, never the shared primary working directory, so multiple invocations of this skill can run concurrently without colliding. Use when asked to implement review changes, address review comments, or fix review feedback on a PR URL, or on several PRs at once, e.g. "implement review changes on PR #1, #2, #3" or given a list of PR URLs to address in bulk. Processes each PR one at a time within a given invocation (never in parallel within the same run, to avoid branch-checkout/working-tree collisions inside that run's worktree), committing and pushing before moving to the next. Optionally self-reviews some or all of the PRs afterward, each in its own fresh terminal opened in the same worktree, waiting for that PR's self-review chain to finish before moving on to the next PR. The `all-my-unreviewed-prs` flag skips the explicit PR list entirely: it discovers every open PR you authored that currently has changes requested by someone else, then fans out one fully independent, concurrently-running invocation of this same skill per PR (each in its own worktree) rather than processing them sequentially.
argument-hint: all-my-unreviewed-prs | <pr-url> [<pr-url> ...] [self-review: all|none|<pr-url-or-number>[,...]]
allowed-tools: Bash(gh *), Bash(git *), Bash(curl *), Bash(ps *), Bash(node *), Read, Glob, Grep, Edit, Write, EnterWorktree, ExitWorktree
---

Implement pending review changes across these PRs, one at a time: $ARGUMENTS

A single PR URL is a valid input — this skill handles one PR or many with the same flow. The per-PR review-implementation procedure is carried inline in Step 2 below (it used to be a separate `implement-review` skill, now consolidated here); this skill wraps that procedure with a commit+push step it doesn't do on its own. The optional self-review pass composes `self-review-multiple`, run in a separate terminal per PR.

If `$ARGUMENTS` carries the `all-my-unreviewed-prs` flag instead of (or alongside) explicit PR URLs, see **Step 0** below first — it discovers the PR list itself and fans the work out concurrently across independent spawned invocations, rather than this session following the rest of the flow directly.

**This skill never operates in the shared primary working directory.** Every checkout, edit, commit, and push happens inside one dedicated git worktree, entered once at the start of Step 2 and removed at the end. A point-in-time-clean `git status` in the shared directory is not a guarantee that it stays clean the instant a checkout runs there — only physical isolation is. Isolating in a worktree is also what makes it safe to run multiple invocations of this skill concurrently — different terminals, different PR lists — without them fighting over the same checked-out branch.

This repo gates every PR on two checks read live from `main`, not from whatever existed when the PR was opened — `PR Policy` (Danger, `.github/danger/dangerfile.ts`/`rules.ts`: the PR body must carry all six required sections) and `PR CI`'s docs-sync gate (`scripts/check-docs-sync.mjs`: changed/added code must be covered by a docs page or exempted). Pushing here is expected to dismiss any existing approvals anyway (this repo's ruleset has `dismiss_stale_reviews_on_push: true`, and addressing review feedback is exactly the case reviewers expect to re-review) — the goal is a single push per PR that leaves both checks green, not a green-then-red-then-fixed cycle across multiple pushes.

## Step 0 — Optional: the `all-my-unreviewed-prs` fan-out flag

Before parsing `$ARGUMENTS` as an explicit PR list, check whether it carries the `all-my-unreviewed-prs` flag — match on intent like the self-review directive in Step 1 (hyphens/spaces/case variations all count, e.g. "all my unreviewed prs"). If it's absent, skip straight to Step 1 — everything below is this flag's own path.

When present, this session's job is discovery + fan-out, not implementation — it never checks out a branch or enters a worktree itself:

a. Discover your own open PRs with changes requested by someone else: `gh pr list --author @me --state open --json number,url,title,reviewDecision`, filtered to `reviewDecision == "CHANGES_REQUESTED"` (client-side, or via `--jq`). `gh` infers the repo from the working directory; no need to pass `--repo`. `reviewDecision` is GitHub's own computed field — you can't formally request changes on your own PR, so every match here is, by construction, requested by someone else, and it already drops off on its own once a reviewer re-approves. This step is read-only: no checkout, no worktree needed.

b. If nothing matches, say so plainly — "No open PRs of yours currently have changes requested." — and stop. Do not fall through to Step 1.

c. **State the resolved list out loud**, the same way Step 1 states its self-review directive: e.g. `all-my-unreviewed-prs resolved to 3 PR(s): #501, #512, #530`.

d. Strip the flag token out of `$ARGUMENTS`. Whatever text remains (trimmed) is a self-review directive to forward verbatim to every spawned invocation below — evaluated independently by each one, against its own single-PR list, using the exact matching rules Step 1 already defines (so a subset like "self-review #512" still reaches only the spawned invocation whose PR number matches).

e. **Fan out: one fresh terminal per discovered PR, launched concurrently, none of them waited on.** This is the payoff of the worktree isolation the rest of this skill already has — each spawned terminal runs this same skill again, for exactly one PR, and immediately does its own `EnterWorktree`/`ExitWorktree`, so N of these genuinely run at once with no shared-directory collision. For each discovered PR, follow the identical four-step statically-analyzable terminal-bridge sequence Step 2 item 4 uses (read `~/.claude-terminal-bridge-token`, walk the `ps` ancestry, write the JSON body, `curl` to `/open-terminal`), with two differences:
   - `cwd` is the **main project root**, not a worktree — there is no worktree yet for this new invocation; it creates its own the moment it starts.
   - `cmd` is `claude --permission-mode auto \"/implement-multiple-reviews <PR_URL>[ <self-review-directive-text-from-d>]\"`.

   Launch every terminal without waiting for any of them to finish. This is unlike Step 2 item 4's self-review wait, which exists only because that flow shares one worktree across sequentially-processed PRs — here, each fan-out terminal owns its own worktree from the instant it opens, so there is nothing shared left to block on.

f. Report back to the user: the resolved list from (c), and for each PR either confirmation its terminal was opened or the same non-fatal handling Step 2 item 4 uses when the terminal bridge is unreachable (missing token, curl failure — note it, move on, don't block the rest of the fan-out on one failed spawn). Then stop; this session does not continue on to Step 1.

## Step 1 — Parse the PR list and the self-review directive

Split `$ARGUMENTS` on whitespace and/or commas into individual PR URLs. Validate each looks like a GitHub PR URL (`https://github.com/<owner>/<repo>/pull/<number>`). If none are found, stop and ask the user for URLs.

Separately, look for a self-review directive anywhere in the free-form instruction — this is conversational input, not a strict CLI flag, so match on intent rather than exact syntax:

- **Not mentioned at all** → directive is `none`. This is the default and preserves this skill's original behavior exactly — no self-review happens unless asked for.
- **"self-review none" / "don't self-review" / "skip self-review" / equivalent** → directive is `none`, stated explicitly.
- **"self-review all" / "self-review everything" / "self-review all of them" / equivalent** → directive is `all`: every PR in the list gets a self-review pass after its review changes are implemented.
- **A specific subset named** (e.g. "self-review #491", "self-review only <url>", "self-review PR 491 and 502") → directive is that subset. Match named PRs against the parsed list by number or URL. If a named PR isn't in the parsed list, ignore the mismatch rather than failing the whole run — just don't self-review it (nothing to self-review since it isn't in the list).

Resolve this into a simple per-PR boolean before Step 2: for each PR URL in the list, `selfReview = true` if the directive is `all`, or if the directive's subset names this PR; `selfReview = false` otherwise (including the default `none` case).

**State the resolved directive out loud before starting Step 2** — one plain line, always, regardless of which case it resolved to: e.g. `Self-review: none (not requested)`, `Self-review: all N PRs`, or `Self-review: PR #491, #502 only (of N total)`. This must appear every run, including the default case — never leave it implicit just because nothing was mentioned.

## Step 2 — Process each PR strictly in order, inside a dedicated worktree

**Before touching any PR:** call `EnterWorktree` with a fresh `name` (e.g. `implement-reviews-<short-id>`). This branches from `origin/<default-branch>` and switches this session's working directory into the new worktree — every subsequent tool call (`Bash`, `Read`, `Write`, `Edit`) operates inside it automatically, with no manual `cd` needed anywhere in this skill. Note this worktree's absolute path; it's needed verbatim in step 4's terminal-bridge JSON below.

This skill's own work — `gh`/`git` operations, file edits, the docs-sync node script — is fully self-contained within a git checkout, with no involvement of the simulator, Metro, or the shared Convex dev deployment, so worktree isolation is sufficient here on its own (unlike simulator manual-testing, where a worktree isolates files but not those other shared singletons).

**If completing any step for any PR genuinely requires checking data or running something in the current/main working directory or the running app itself — not this worktree** (for example, inspecting live simulator/Metro/Convex state, or anything else that assumes exclusive use of the shared dev environment) — **stop and flag it to the user instead of doing it.** The shared working directory or app may be busy with something else (another terminal, another concurrent invocation of this skill, manual testing in progress); this skill's whole concurrency guarantee depends on never reaching outside its own worktree.

If `EnterWorktree` itself fails, stop and report that to the user rather than falling back to running any of this in the shared primary working directory.

For each PR URL, in the order given:

1. **Implement the review.** Run the full review-implementation procedure for this PR's URL:

   a. Parse the PR URL to determine owner, repository, and PR number.

   b. Collect all PR information using GitHub CLI:
      - PR title, description, and current diff (`gh pr view`, `gh pr diff`)
      - All issue-level comments (`gh api repos/<owner>/<repo>/issues/<number>/comments`)
      - All review comments on the diff (`gh api repos/<owner>/<repo>/pulls/<number>/comments`)
      - All submitted reviews (`gh api repos/<owner>/<repo>/pulls/<number>/reviews`)

   b2. **Re-check the linked Linear issue for design references before implementing anything.** On SHO-420 (PR #616), the ticket's design decisions had been posted as a Linear *comment*; the review-implementation pass on that PR only read the PR's own review text and never went back to the ticket, so the design was implemented wrong a second time before anyone caught it. Don't repeat that: the PR template guarantees a `## Linear Issue` section carrying the ticket URL — extract the identifier (e.g. `SHO-420`) and fetch it fresh, even if this PR's own diff or comments seem self-explanatory:
      ```bash
      grep '^LINEAR_API_KEY=' /Users/guilhermereis/Desktop/clones/shopit-monorepo/.env.local | tail -1 | cut -d'=' -f2
      curl -s -X POST https://api.linear.app/graphql \
        -H "Authorization: <key>" \
        -H "Content-Type: application/json" \
        -d '{
          "query": "{ issue(id: \"<IDENTIFIER>\") { id identifier title description attachments { nodes { title url subtitle } } comments { nodes { body createdAt user { name } } } } }"
        }'
      ```
      Scan the issue `description`, every comment `body`, and every `attachments` entry for design artifacts: inline images (markdown `![...](...)`, especially `uploads.linear.app` URLs), links to Figma/Zeplin/Sketch Cloud/Framer/InVision/Miro/Abstract/Adobe XD, or any `attachments` node. For every directly-fetchable image found, download it (`curl -s -L -o /tmp/linear-design-<n>.png "<url>"`) and `Read` it before implementing — don't treat having seen the link in text as having looked at the design. Then invoke the `screenshot-to-code` skill on the downloaded image before implementing anything from it — tell it explicitly the target is this repo's Expo/React Native app (`apps/mobile`), not web React/Tailwind, so its structural/styling breakdown (layout, components, spacing, colors) comes back in those terms; use that breakdown as an input to step (e)'s implementation, still following this app's own component conventions and locked-component rules rather than pasting its output in directly. For a design-tool link that can't be rendered this way, say so plainly and ask the user for a screenshot/export rather than silently skipping it. If the PR being reviewed is UI-facing and this turns up a design that the current implementation doesn't match, treat that as a pending item in step (c) below on the same footing as an explicit review comment — the review that requested changes may not even mention it if the reviewer also missed it.

   c. Identify pending items: only act on comments/reviews requesting changes that have NOT already been addressed in a subsequent commit or reply, plus any design mismatch surfaced in (b2). Read ALL comments, reviews, and the linked ticket before touching any code. Never implement something that is already resolved.

   d. Check out the PR branch if not already on it: `gh pr checkout <number>`. If the branch does not exist locally, check it out automatically. This runs inside the worktree entered above — never in the shared primary working directory.

   e. Implement all pending requested changes. Fully implement each one — no placeholder TODOs. Follow all existing code conventions. If a review comment is ambiguous, make a reasonable judgment and note it in the summary comment. Do not ask for confirmation before implementing — just do it.

   f. Post a single comment on the PR via `gh pr comment <number> --body "..."` summarizing what was changed and why (one bullet per addressed item) and any items intentionally skipped with the accurate reason. Never say "out of scope" for an open question — the real reason is that it requires team input that an implementation pass alone cannot resolve; say that instead.

   Do NOT commit or push in this step — the commit+push is step 3.

2. **Check for changes.** Run `git status --porcelain`. If it's empty, nothing was pending for this PR — skip straight to step 4 (there's nothing to commit/push, but this PR may still be selected for self-review).

3. **Commit and push** (only if step 2 found changes).
   - Stage exactly the files modified in step 1, listed individually via `git add <file1> <file2> ...` — never `git add -A` or `git add .`.
   - **Docs-sync preflight, before committing.** Run `node scripts/check-docs-sync.mjs --validate`. If it reports a file just added/modified in step 1 with `no page lists it under "sources"`, fix it now — add the file's repo-relative path to the closest-matching existing page's `sources:` frontmatter (`apps/docs/content/**/*.mdx`) if one genuinely covers it, otherwise add a reasoned entry (10+ chars, not a placeholder) to `apps/docs/not-documented.json` (create it as `{}` if missing). Stage that fix alongside the rest (`git add` it too) so it lands in the same commit — this is the fix for PR CI's docs-coverage self-test, and it must happen before the push below, not as a follow-up.
   - Derive the commit message using the [git commit convention](../../ai/git-conventions.md): `<type>(<scope>): SHO-<number> <description>`. Infer the SHO number from the branch name, the scope from the changed files, and pick whichever `type` (usually `fix`) matches what was actually changed. Base the description on the summary comment just posted to the PR in step 1, e.g. `address pr review — <short summary>`. Lowercase, no trailing period, no `Co-Authored-By` line, no Claude attribution.
   - Write the message to a scratch file with the Write tool (not inline in the Bash command) and commit with `git commit -F <path>` — avoids quoting/heredoc issues.
   - **Docs-sync gate check, before pushing.** Run `git fetch origin main --quiet` then `PR_BODY="$(gh pr view --json body -q .body)" node scripts/check-docs-sync.mjs --base origin/main --head HEAD`. If it prints `FAIL`, either the diff genuinely moved code a docs page owns (make that doc edit now and fold it into the same commit with `git commit --amend`) or the PR body just needs the opt-out line — edit the body's `## Docs` section to add `Docs: not needed — <reason>` via `gh pr edit --body-file <scratch-file>` (this is a body edit, not a push, so it doesn't cost another review dismissal). Re-run the gate check until it passes.
   - Push to the PR's branch: `git push`.
   - **Verify CI after pushing.** Poll `gh pr checks <PR_URL>` (or `gh pr view --json statusCheckRollup`) until `PR Policy` and `PR CI` complete. If `PR Policy` fails on missing/malformed required sections (`## What this changes (plain English)`, `## Linear Issue`, `## Merge invariant`, `## QA`, `## Deployment Notes`, `## Docs` — see `.github/pull_request_template.md` and `.github/danger/rules.ts`), the PR predates the current template; fix the body via `gh pr edit --body-file` (same six-section shape `create-pr`/`hotfix-pr` use) — no push needed, so it's free. If `PR CI` fails for a reason unrelated to this PR's diff (e.g. a repo-wide gate that changed on `main` since the branch was created), diagnose and fix it now rather than leaving the PR red — do not just report the failure and move on.

4. **Self-review, only if this PR's `selfReview` is `true`.** Skip straight to step 5 if it's `false`.
   - **Open a fresh terminal** via the Claude Terminal Bridge extension to run `/self-review-multiple <this PR's URL>` for just this one PR. Do not invoke `self-review-pr`/`self-review-multiple` inline in this session — running it in its own terminal is what the user asked for, mirrors how `self-review-multiple`'s own auto-continue rounds already run (see `implement-self-review`), and keeps this session's working tree free of a self-review's own checkouts while it's running.
     Follow this exact four-step, statically-analyzable sequence — do not collapse it into a multi-line script with `$(...)`/`if`, which forces a manual permission prompt on every run:
     1. Use the `Read` tool to read `~/.claude-terminal-bridge-token`. If it's missing or empty, treat this PR's self-review as skipped non-fatally: note it in the final summary and continue to step 5 without waiting (there is no terminal to wait on).
     2. Get the caller's process-ancestry chain with two flat, single-purpose `ps` commands (not a loop/`if`/`$(...)` script — that shape triggers a manual permission prompt even with `Bash(ps *)` allowed):
        ```bash
        ps -o pid,ppid= -p $$
        ```
        ```bash
        ps -A -o pid,ppid,comm
        ```
        Walk the ancestry yourself from the first command's PID through the second command's output — find the row whose `pid` matches, note its `ppid`, repeat. Stop after 8 hops or at a `ppid` of `0`/`1`/no match. Build the comma-separated PID list from this walk.
     3. Use the `Write` tool to write the request body as literal JSON to `/private/tmp/claude-terminal-bridge-body.json`:
        ```json
        {"name": "Self-review PR #<number>", "cmd": "claude --permission-mode auto \"/self-review-multiple <PR_URL>\"", "cwd": "<WORKTREE_ABSOLUTE_PATH>", "callerPids": [<PID_LIST_FROM_STEP_2>]}
        ```
        `<WORKTREE_ABSOLUTE_PATH>` is this run's worktree — the one entered at the start of Step 2, **not** the main project root. Pointing the spawned terminal there keeps `self-review-multiple`'s own `gh pr checkout` and edits inside this run's isolated directory instead of leaking into the shared primary working directory (which may be mid-task in another terminal). `--permission-mode auto` is required — a spawned terminal has nobody present to answer a permission prompt, so a bare `claude "..."` (manual mode) can hang indefinitely the instant the chain's first Bash/Edit call needs approval. Auto mode's classifier still declines genuinely dangerous actions; it just doesn't block on routine ones (e.g. `rm -f` on a scratch marker file, `git commit`, `git push`) with no one there to click through them.
     4. Run a single flat `curl` command, with the token value from step 1 substituted in directly as literal text:
        ```bash
        curl -s -X POST http://127.0.0.1:61337/open-terminal -H "X-Token: <TOKEN_VALUE>" -H "Content-Type: application/json" -d @/private/tmp/claude-terminal-bridge-body.json
        ```
     If this curl call errors or fails (extension not installed, VS Code not running, wrong port), treat it as non-fatal: note it in the final summary and continue to step 5 without waiting — there is no terminal to wait on.
   - **Wait for this PR's self-review chain to finish before moving to the next PR.** `/self-review-multiple` in that other terminal invokes `self-review-pr`, which may hand off to `implement-self-review`'s auto-continue (further terminals, up to its own 6-round cap) — this is the part the user specifically asked for: the main terminal (this session) blocks here rather than starting the next PR's review-implementation pass while that chain might still be running.
     - **Signal:** `self-review-pr` and `implement-self-review` write a deterministic, PR-scoped **chain-completion marker** — `/tmp/.claude-self-review-chain-done-<owner>-<repo>-<number>` (owner/repo with `/` replaced by `-`; `<number>` is this PR's number) — as the last file operation on whichever exit path ends the chain (clean first pass, every-item-deferred, 6-round cap, and terminal-bridge-unreachable all write it; opening a next round does not — that round writes it when it terminates). Poll for this marker to **appear**. Do **not** infer completion from the round-counter file: a clean first pass never creates it, which is what used to force a blind 10-minute wait here.
     - Before opening the terminal in this step, `rm -f` both `/tmp/.claude-self-review-chain-done-<owner>-<repo>-<number>` and `/tmp/.claude-self-review-rounds-<owner>-<repo>-<number>` so neither can be stale from an earlier run on this PR.
     - After opening the terminal, wait in a single backgrounded loop (you'll be notified when it exits). Use a self-contained bash time bound rather than the `timeout` command — it's GNU coreutils, not on macOS by default:
       ```bash
       end=$(( $(date +%s) + 7200 )); until [ -e /tmp/.claude-self-review-chain-done-<owner>-<repo>-<number> ] || [ "$(date +%s)" -ge "$end" ]; do sleep 10; done; [ -e /tmp/.claude-self-review-chain-done-<owner>-<repo>-<number> ] && echo MARKER_FOUND || echo TIMED_OUT
       ```
       Run with `run_in_background: true`, substituting the real owner/repo/number. The common case (a clean first pass) resolves within ~10s of the spawned pass finishing — no fixed grace window. **The `until` loop's own exit code is 0 either way** — `A || B` succeeding tells you nothing about which of `A` (marker appeared) or `B` (timeout elapsed) is what ended it, so the trailing `echo` is not optional decoration: it is the only reliable signal for which branch fired. Read it from the notification/output before concluding anything about the chain's outcome.
     - When the output is `MARKER_FOUND`: the chain has terminated. Read this PR's latest comments to classify the outcome for the final summary — "Self-review process finished. Nothing blocking or important left." (clean), "Self-review ran and implemented nothing this round … need a decision from you" (every item deferred), or one or more new `Self-review:` commits pushed to the branch (implemented; note how many rounds if the counter file shows it). Then move on to step 5.
     - When the output is `TIMED_OUT` instead: the marker never appeared — treat this exactly like a genuinely stuck chain (Terminal Bridge failed to open a follow-up round, or the spawned session itself stalled on something with no one to answer it). Do not describe this as "self-review finished clean" or infer any outcome from silence on the PR — a `TIMED_OUT` result means you don't know what happened. Stop waiting, note plainly in this PR's line of the final summary that the wait timed out after 2 hours with no completion signal, and proceed to step 5 anyway rather than hanging the whole batch.

5. **Move to the next PR only after this one is fully committed and pushed (or confirmed to have nothing pending) AND its self-review wait (if any) has resolved.** Do not start the next PR's review-implementation pass before both of those are true for the current PR — this is what prevents branch checkouts and uncommitted edits from colliding across PRs within this run's worktree, and what prevents this session and a self-review terminal from doing git operations in that same worktree at once.

## Step 3 — Tear down the worktree

Once every PR in the list has been processed — all committed+pushed or confirmed to have nothing pending, and every selected self-review wait resolved — call `ExitWorktree` with `action: "remove", discard_changes: true`. Any PR that had pending changes already had them committed and pushed to that PR's own remote branch back in step 3 of the loop above, so nothing is lost by removing the worktree now. `discard_changes: true` is expected to be needed here — the worktree's current branch (whichever PR was checked out last) carries commits relative to the throwaway branch `EnterWorktree` created at the start, which is normal and safe, not a sign anything is actually uncommitted. If `ExitWorktree` instead reports uncommitted files it didn't anticipate, stop and show the user what it found rather than silently discarding.

If `ExitWorktree` itself fails, note that in the final summary rather than leaving the user to discover a stray worktree later.

Then produce the final summary described below.

## Rules

- Never run PRs in parallel within a single invocation. Step 2 checks out each PR's branch directly inside this run's worktree (`gh pr checkout`) and leaves changes uncommitted until step 3 commits them — running two PRs from the same list at once means two branch checkouts and two sets of uncommitted edits fighting over that one worktree. Go sequential within a run. The `all-my-unreviewed-prs` flag (Step 0) is the one exception, and it isn't really an exception to this rule — it doesn't process multiple PRs in one run at all; it spawns N separate single-PR runs, each with its own worktree.
- Never operate outside this run's worktree. Everything — checkouts, edits, commits, pushes, the docs-sync script, the self-review terminal — happens inside the worktree entered at the start of Step 2. If a PR's review genuinely can't be finished without checking data or running something in the shared primary working directory or the running app itself, stop and flag it to the user instead of reaching outside the worktree to do it — that directory or app may be busy with something else, and this is exactly the collision worktree isolation exists to prevent.
- What this isolation buys you: multiple invocations of this skill — different terminals, different PR lists — can now run concurrently, since each has its own worktree instead of fighting over the shared primary working directory. A single invocation's own PR list is still processed strictly one at a time, per the rule above.
- Self-review is opt-in per PR and defaults to off (`none`) — a plain "implement review changes on PR #1, #2, #3" with no mention of self-review must behave exactly as it did before this option existed.
- Do not ask for confirmation between PRs — process the whole list unattended once started.
- If the review-implementation step (Step 2, item 1) fails outright for one PR (bad URL, PR not found, checkout fails), report the failure for that PR specifically and continue on to the next one rather than aborting the whole batch. Do not attempt its self-review step even if selected.
- If a PR has nothing pending, say so plainly in the final summary rather than silently skipping it — it may still get a self-review pass if selected.
- Never force-push.
- Never prefix `git`/`gh` commands with `cd /path/to/repo &&` — the working directory is already this run's worktree (entered in Step 2), not the main project root.
- Never raise or bypass the 6-round self-review auto-continue cap, and never skip the counter-file wait as a shortcut to reach the next PR sooner — the whole point of waiting is to keep this run's worktree conflict-free.
- At the end, first restate the resolved self-review directive from Step 1 (same line as before Step 2 — none / all / the specific subset), then report one line per PR covering all of: review-implementation outcome (implemented+pushed, nothing pending, or failed with reason), CI outcome after the push (`PR Policy`/`PR CI` green, or what was still red and why if it couldn't be fixed in-run), and, if selected, self-review outcome (chain finished clean, chain finished after N rounds, implemented nothing — N item(s) need a human decision (say what they are), hit the 6-round cap, terminal-bridge unreachable, or timed out after 2 hours). Also state whether the worktree was cleanly torn down in Step 3.

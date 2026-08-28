---
name: implement-multiple-reviews
description: Implement pending review changes on one or more GitHub PRs — reads all comments and reviews, implements unresolved items, posts a summary comment, then commits and pushes — with an optional self-review pass per PR. Use when asked to implement review changes, address review comments, or fix review feedback on a PR URL, or on several PRs at once, e.g. "implement review changes on PR #1, #2, #3" or given a list of PR URLs to address in bulk. Processes each PR one at a time (never in parallel, to avoid branch-checkout/working-tree collisions), committing and pushing before moving to the next. Optionally self-reviews some or all of the PRs afterward, each in its own fresh terminal, waiting for that PR's self-review chain to finish before moving on to the next PR.
argument-hint: <pr-url> [<pr-url> ...] [self-review: all|none|<pr-url-or-number>[,...]]
allowed-tools: Bash(gh *), Bash(git *), Bash(curl *), Bash(ps *), Bash(node *), Read, Glob, Grep, Edit, Write
---

Implement pending review changes across these PRs, one at a time: $ARGUMENTS

A single PR URL is a valid input — this skill handles one PR or many with the same flow. The per-PR review-implementation procedure is carried inline in Step 2 below (it used to be a separate `implement-review` skill, now consolidated here); this skill wraps that procedure with a commit+push step it doesn't do on its own. The optional self-review pass composes `self-review-multiple`, run in a separate terminal per PR.

This repo gates every PR on two checks read live from `main`, not from whatever existed when the PR was opened — `PR Policy` (Danger, `.github/danger/dangerfile.ts`/`rules.ts`: the PR body must carry all six required sections) and `PR CI`'s docs-sync gate (`scripts/check-docs-sync.mjs`: changed/added code must be covered by a docs page or exempted). Pushing here is expected to dismiss any existing approvals anyway (this repo's ruleset has `dismiss_stale_reviews_on_push: true`, and addressing review feedback is exactly the case reviewers expect to re-review) — the goal is a single push per PR that leaves both checks green, not a green-then-red-then-fixed cycle across multiple pushes.

## Step 1 — Parse the PR list and the self-review directive

Split `$ARGUMENTS` on whitespace and/or commas into individual PR URLs. Validate each looks like a GitHub PR URL (`https://github.com/<owner>/<repo>/pull/<number>`). If none are found, stop and ask the user for URLs.

Separately, look for a self-review directive anywhere in the free-form instruction — this is conversational input, not a strict CLI flag, so match on intent rather than exact syntax:

- **Not mentioned at all** → directive is `none`. This is the default and preserves this skill's original behavior exactly — no self-review happens unless asked for.
- **"self-review none" / "don't self-review" / "skip self-review" / equivalent** → directive is `none`, stated explicitly.
- **"self-review all" / "self-review everything" / "self-review all of them" / equivalent** → directive is `all`: every PR in the list gets a self-review pass after its review changes are implemented.
- **A specific subset named** (e.g. "self-review #491", "self-review only <url>", "self-review PR 491 and 502") → directive is that subset. Match named PRs against the parsed list by number or URL. If a named PR isn't in the parsed list, ignore the mismatch rather than failing the whole run — just don't self-review it (nothing to self-review since it isn't in the list).

Resolve this into a simple per-PR boolean before Step 2: for each PR URL in the list, `selfReview = true` if the directive is `all`, or if the directive's subset names this PR; `selfReview = false` otherwise (including the default `none` case).

**State the resolved directive out loud before starting Step 2** — one plain line, always, regardless of which case it resolved to: e.g. `Self-review: none (not requested)`, `Self-review: all N PRs`, or `Self-review: PR #491, #502 only (of N total)`. This must appear every run, including the default case — never leave it implicit just because nothing was mentioned.

## Step 2 — Process each PR strictly in order

For each PR URL, in the order given:

1. **Implement the review.** Run the full review-implementation procedure for this PR's URL:

   a. Parse the PR URL to determine owner, repository, and PR number.

   b. Collect all PR information using GitHub CLI:
      - PR title, description, and current diff (`gh pr view`, `gh pr diff`)
      - All issue-level comments (`gh api repos/<owner>/<repo>/issues/<number>/comments`)
      - All review comments on the diff (`gh api repos/<owner>/<repo>/pulls/<number>/comments`)
      - All submitted reviews (`gh api repos/<owner>/<repo>/pulls/<number>/reviews`)

   c. Identify pending items: only act on comments/reviews requesting changes that have NOT already been addressed in a subsequent commit or reply. Read ALL comments and reviews before touching any code. Never implement something that is already resolved.

   d. Check out the PR branch locally if not already on it: `gh pr checkout <number>`. If the branch does not exist locally, check it out automatically.

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
        {"name": "Self-review PR #<number>", "cmd": "claude \"/self-review-multiple <PR_URL>\"", "cwd": "<PROJECT_ROOT_ABSOLUTE_PATH>", "callerPids": [<PID_LIST_FROM_STEP_2>]}
        ```
        `<PROJECT_ROOT_ABSOLUTE_PATH>` is the current project root this skill is running in.
     4. Run a single flat `curl` command, with the token value from step 1 substituted in directly as literal text:
        ```bash
        curl -s -X POST http://127.0.0.1:61337/open-terminal -H "X-Token: <TOKEN_VALUE>" -H "Content-Type: application/json" -d @/private/tmp/claude-terminal-bridge-body.json
        ```
     If this curl call errors or fails (extension not installed, VS Code not running, wrong port), treat it as non-fatal: note it in the final summary and continue to step 5 without waiting — there is no terminal to wait on.
   - **Wait for this PR's self-review chain to finish before moving to the next PR.** `/self-review-multiple` in that other terminal invokes `self-review-pr`, which may hand off to `implement-self-review`'s auto-continue (further terminals, up to its own 6-round cap) — this is the part the user specifically asked for: the main terminal (this session) blocks here rather than starting the next PR's review-implementation pass while that chain might still be running.
     - Detect completion via the same round-counter file `self-review-pr`/`implement-self-review` maintain: `/tmp/.claude-self-review-rounds-<owner>-<repo>-<number>` (owner/repo with `/` replaced by `-`; `<number>` is this PR's number). Before opening the terminal in this step, check whether this file already exists from an unrelated earlier run on this PR — if so, delete it first, so its later absence can only mean "this run's chain hasn't started yet" or "this run's chain finished clean," never stale leftover state.
     - The terminal was just opened as a detached process — unlike `self-review-multiple`'s own internal wait (which checks the counter file immediately after synchronously calling `self-review-pr` in-process), this session has no signal for when the other terminal's `claude` process has even started, let alone finished its first pass. Handle this in two phases:
       1. **Startup phase:** wait for the counter file to first appear (non-empty), polling in a backgrounded loop, capped at a 10-minute grace window. Use a self-contained bash time bound rather than the `timeout` command — it's GNU coreutils and isn't installed on macOS by default:
          ```bash
          end=$(( $(date +%s) + 600 )); until [ -s /tmp/.claude-self-review-rounds-<owner>-<repo>-<number> ] || [ "$(date +%s)" -ge "$end" ]; do sleep 15; done
          ```
          Run with `run_in_background: true`. If it exits at the time bound without the file ever appearing, treat this as `self-review-pr`'s first pass having come back clean (nothing blocking/important found, exactly like it behaves when invoked directly) and move on to step 5 — do not treat a startup timeout as a failure.
       2. **Completion phase** (only if the file appeared): wait for it to clear or exceed the 6-round cap, same as `self-review-multiple` itself does:
          ```bash
          until [ ! -s /tmp/.claude-self-review-rounds-<owner>-<repo>-<number> ] || [ "$(cat /tmp/.claude-self-review-rounds-<owner>-<repo>-<number> 2>/dev/null)" -gt 6 ]; do sleep 60; done
          ```
          Run with `run_in_background: true`, substituting owner/repo/number in both phases. Cap the completion phase's total wait at 2 hours as a safety valve, in case something got stuck (e.g. the Terminal Bridge extension failing to open a follow-up terminal). If still unresolved after that, stop waiting, note it plainly in this PR's line of the final summary, and proceed to step 5 anyway rather than hanging the whole batch indefinitely.

5. **Move to the next PR only after this one is fully committed and pushed (or confirmed to have nothing pending) AND its self-review wait (if any) has resolved.** Do not start the next PR's review-implementation pass before both of those are true for the current PR — this is what prevents branch checkouts and uncommitted edits from colliding across PRs, and what prevents this session and a self-review terminal from doing git operations in the same working tree at once.

## Rules

- Never run PRs in parallel. Step 2 checks out each PR's branch directly in the shared working directory (`gh pr checkout`) and leaves changes uncommitted until step 3 commits them — running two PRs at once means two branch checkouts and two sets of uncommitted edits fighting over the same working tree. The only way to safely parallelize this would be to give each PR its own git worktree (a separate checkout of its branch backed by the same `.git`) and process each independently — real added complexity (worktree setup/teardown, per-worktree dependency installs, cleanup on failure) for a handful of PRs that mostly wait on `gh` API round-trips anyway. Not worth it here — go sequential.
- Self-review is opt-in per PR and defaults to off (`none`) — a plain "implement review changes on PR #1, #2, #3" with no mention of self-review must behave exactly as it did before this option existed.
- Do not ask for confirmation between PRs — process the whole list unattended once started.
- If the review-implementation step (Step 2, item 1) fails outright for one PR (bad URL, PR not found, checkout fails), report the failure for that PR specifically and continue on to the next one rather than aborting the whole batch. Do not attempt its self-review step even if selected.
- If a PR has nothing pending, say so plainly in the final summary rather than silently skipping it — it may still get a self-review pass if selected.
- Never force-push.
- Never prefix `git`/`gh` commands with `cd /path/to/repo &&` — the working directory is already the project root.
- Never raise or bypass the 6-round self-review auto-continue cap, and never skip the counter-file wait as a shortcut to reach the next PR sooner — the whole point of waiting is to keep the shared working directory conflict-free.
- At the end, first restate the resolved self-review directive from Step 1 (same line as before Step 2 — none / all / the specific subset), then report one line per PR covering all of: review-implementation outcome (implemented+pushed, nothing pending, or failed with reason), CI outcome after the push (`PR Policy`/`PR CI` green, or what was still red and why if it couldn't be fixed in-run), and, if selected, self-review outcome (chain finished clean, chain finished after N rounds, hit the 6-round cap, terminal-bridge unreachable, or timed out after 2 hours).

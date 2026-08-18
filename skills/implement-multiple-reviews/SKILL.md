---
name: implement-multiple-reviews
description: Sequentially implement pending review changes across multiple GitHub PRs, committing and pushing after each one, with an optional self-review pass per PR. Use when asked to implement reviews on several PRs at once, e.g. "implement review changes on PR #1, #2, #3" or given a list of PR URLs to address in bulk. Runs the implement-review skill for each PR one at a time (never in parallel, to avoid branch-checkout/working-tree collisions), then commits and pushes before moving to the next PR — unlike implement-review alone, which never commits or pushes. Optionally self-reviews some or all of the PRs afterward, each in its own fresh terminal, waiting for that PR's self-review chain to finish before moving on to the next PR.
argument-hint: <pr-url-1> <pr-url-2> [...] [self-review: all|none|<pr-url-or-number>[,...]]
allowed-tools: Bash(gh *), Bash(git *), Bash(curl *), Bash(ps *), Read, Glob, Grep, Edit, Write
---

Implement pending review changes across these PRs, one at a time: $ARGUMENTS

This skill composes the existing `implement-review` skill with a commit+push step it doesn't do on its own. Invoking it via the Skill tool rather than copying its steps here means this pipeline automatically stays in sync if `implement-review` is ever updated. The optional self-review pass composes `self-review-multiple` the same way, run in a separate terminal per PR.

## Step 1 — Parse the PR list and the self-review directive

Split `$ARGUMENTS` on whitespace and/or commas into individual PR URLs. Validate each looks like a GitHub PR URL (`https://github.com/<owner>/<repo>/pull/<number>`). If none are found, stop and ask the user for URLs.

Separately, look for a self-review directive anywhere in the free-form instruction — this is conversational input, not a strict CLI flag, so match on intent rather than exact syntax:

- **Not mentioned at all** → directive is `none`. This is the default and preserves this skill's original behavior exactly — no self-review happens unless asked for.
- **"self-review none" / "don't self-review" / "skip self-review" / equivalent** → directive is `none`, stated explicitly.
- **"self-review all" / "self-review everything" / "self-review all of them" / equivalent** → directive is `all`: every PR in the list gets a self-review pass after its review changes are implemented.
- **A specific subset named** (e.g. "self-review #491", "self-review only <url>", "self-review PR 491 and 502") → directive is that subset. Match named PRs against the parsed list by number or URL. If a named PR isn't in the parsed list, ignore the mismatch rather than failing the whole run — just don't self-review it (nothing to self-review since it isn't in the list).

Resolve this into a simple per-PR boolean before Step 2: for each PR URL in the list, `selfReview = true` if the directive is `all`, or if the directive's subset names this PR; `selfReview = false` otherwise (including the default `none` case).

## Step 2 — Process each PR strictly in order

For each PR URL, in the order given:

1. **Implement the review.** Invoke the `implement-review` skill via the Skill tool, passing this PR's URL as its argument. Let it run to completion — it checks out the PR's branch, reads all comments/reviews, implements pending items, and posts its own summary comment to the PR. It does not commit or push, by design.

2. **Check for changes.** Run `git status --porcelain`. If it's empty, nothing was pending for this PR — skip straight to step 4 (there's nothing to commit/push, but this PR may still be selected for self-review).

3. **Commit and push** (only if step 2 found changes).
   - Stage exactly the files `implement-review` modified, listed individually via `git add <file1> <file2> ...` — never `git add -A` or `git add .`.
   - Derive the commit message using the [git commit convention](../../ai/git-conventions.md): `<type>(<scope>): SHO-<number> <description>`. Infer the SHO number from the branch name, the scope from the changed files, and pick whichever `type` (usually `fix`) matches what was actually changed. Base the description on the summary `implement-review` just posted to the PR, e.g. `address pr review — <short summary>`. Lowercase, no trailing period, no `Co-Authored-By` line, no Claude attribution.
   - Write the message to a scratch file with the Write tool (not inline in the Bash command) and commit with `git commit -F <path>` — avoids quoting/heredoc issues.
   - Push to the PR's branch: `git push`.

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
   - **Wait for this PR's self-review chain to finish before moving to the next PR.** `/self-review-multiple` in that other terminal invokes `self-review-pr`, which may hand off to `implement-self-review`'s auto-continue (further terminals, up to its own 6-round cap) — this is the part the user specifically asked for: the main terminal (this session) blocks here rather than starting the next PR's `implement-review` pass while that chain might still be running.
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

5. **Move to the next PR only after this one is fully committed and pushed (or confirmed to have nothing pending) AND its self-review wait (if any) has resolved.** Do not start the next PR's `implement-review` pass before both of those are true for the current PR — this is what prevents branch checkouts and uncommitted edits from colliding across PRs, and what prevents this session and a self-review terminal from doing git operations in the same working tree at once.

## Rules

- Never run PRs in parallel. `implement-review` checks out each PR's branch directly in the shared working directory (`gh pr checkout`) and leaves changes uncommitted until this skill commits them — running two PRs at once means two branch checkouts and two sets of uncommitted edits fighting over the same working tree. The only way to safely parallelize this would be to give each PR its own git worktree (a separate checkout of its branch backed by the same `.git`) and process each independently — real added complexity (worktree setup/teardown, per-worktree dependency installs, cleanup on failure) for a handful of PRs that mostly wait on `gh` API round-trips anyway. Not worth it here — go sequential.
- Self-review is opt-in per PR and defaults to off (`none`) — a plain "implement review changes on PR #1, #2, #3" with no mention of self-review must behave exactly as it did before this option existed.
- Do not ask for confirmation between PRs — process the whole list unattended once started.
- If `implement-review` fails outright for one PR (bad URL, PR not found, checkout fails), report the failure for that PR specifically and continue on to the next one rather than aborting the whole batch. Do not attempt its self-review step even if selected.
- If a PR has nothing pending, say so plainly in the final summary rather than silently skipping it — it may still get a self-review pass if selected.
- Never force-push.
- Never prefix `git`/`gh` commands with `cd /path/to/repo &&` — the working directory is already the project root.
- Never raise or bypass the 6-round self-review auto-continue cap, and never skip the counter-file wait as a shortcut to reach the next PR sooner — the whole point of waiting is to keep the shared working directory conflict-free.
- At the end, report one line per PR covering both halves: implement-review outcome (implemented+pushed, nothing pending, or failed with reason) and, if selected, self-review outcome (chain finished clean, chain finished after N rounds, hit the 6-round cap, terminal-bridge unreachable, or timed out after 2 hours).

---
name: rebase-pr
description: Rebase a PR branch off main. Use when asked to "rebase this off main" with a PR URL. Runs entirely inside an isolated git worktree — never the shared primary working directory — so it never disturbs whatever branch or uncommitted work you currently have checked out. Interactively rebases off origin/main, explaining every conflict resolution, and never pushes. Pass the `all-my-open-prs` flag instead of a URL to find every open PR you authored that currently conflicts with main and rebase them all, one at a time, in the same worktree.
argument-hint: <pr-url> | all-my-open-prs
allowed-tools: Bash(git *), Bash(gh *), Read, Edit, EnterWorktree, ExitWorktree
---

## Step 0 — Determine mode

Check whether `$ARGUMENTS` carries the `all-my-open-prs` flag — match on intent (hyphens/spaces/case variations all count, e.g. "all my open prs") rather than requiring an exact token.

- **Present** → follow **Bulk mode** below.
- **Absent** → `$ARGUMENTS` is a single PR URL; follow **Single-PR mode** below. This is the default and preserves this skill's original behavior, just relocated into an isolated worktree per the rest of this document.

## Enter an isolated worktree (both modes)

**Before touching any PR:** call `EnterWorktree` with a descriptive `name` (e.g. `rebase-pr-<pr-number>` for single-PR mode, `rebase-pr-bulk-<short-id>` for bulk mode). This creates a fresh git worktree under `.claude/worktrees/` and switches this session's working directory into it — every subsequent `Bash`, `Read`, and `Edit` call in this skill operates inside it automatically, with no manual `cd` needed. This is what makes the whole skill safe to run while you have other work in progress in the shared primary working directory: nothing here ever checks out a branch, pulls, or rebases there.

If `EnterWorktree` itself fails, stop and report that to the user rather than falling back to running any of this in the shared primary working directory.

One worktree is entered **once per skill invocation** and reused for every PR processed (bulk mode loops the per-PR procedure below inside it rather than entering a new worktree per PR).

## Bulk mode — `all-my-open-prs`

a. Discover every open PR you authored that currently conflicts with main:
   ```bash
   gh pr list --author "@me" --state open --json number,url,headRefName,mergeable
   ```
   `gh` infers the repo from the working directory. Filter client-side to entries where `mergeable == "CONFLICTING"`. GitHub computes `mergeable` asynchronously, so a freshly-opened or freshly-pushed PR can briefly report `"UNKNOWN"` — re-query just that PR once before giving up on it.

b. If none are conflicting, say so plainly — "No open PRs of yours currently conflict with main." — and stop (no worktree has been touched yet if this is checked before entering one; if already inside one, exit it with `action: "remove"` since nothing was done in it).

c. **State the resolved list out loud** before doing anything else: e.g. `all-my-open-prs resolved to 3 PR(s) with conflicts: #501, #512, #530`.

d. **Process each one sequentially, never in parallel**, inside the single worktree entered above. For each PR in the list, in order:
   1. Run the **per-PR rebase procedure** below, using that PR's URL.
   2. If the procedure hits an ambiguous conflict it's not confident about, stop on that PR and ask the user whether to skip it and continue with the rest of the list, or halt the whole run. Do not guess.
   3. Never push, for any PR — the hard rules below apply identically in bulk mode.
   4. Move on to the next PR once the current one's report is shown or it's explicitly skipped by the user.

e. Once every PR in the list has been processed (or the run is halted early), go to **Finishing up** below.

## Single-PR mode

Run the **per-PR rebase procedure** below exactly once, using the PR URL in `$ARGUMENTS`. Then go to **Finishing up** below.

## Per-PR rebase procedure

### Step 1 — Parse the PR URL

Extract owner, repo, and PR number from the URL.

Use `gh pr view <number> --repo <owner>/<repo> --json headRefName` to get the branch name.

### Step 2 — Fetch main and check out the PR branch

```bash
git fetch origin main --quiet
gh pr checkout <number>
git pull origin <branch> --quiet
```

Rebasing onto `origin/main` (fetched fresh) rather than a local `main` branch means this never needs to create or update a local `main` ref — which could otherwise collide with a `main` branch checked out in the shared primary working directory or another worktree.

**If the checkout fails because `<branch>` is already checked out somewhere else** (the shared primary working directory, or a different worktree — including a leftover from a previous run of this skill): do not force it, and do not touch that other location. Stop and tell the user plainly which branch is blocking and where it appears to be checked out (`git worktree list` shows every worktree and its branch), and ask them to switch off that branch there before retrying. This skill cannot rebase a branch it cannot exclusively check out.

### Step 3 — Rebase onto main

```bash
git rebase origin/main
```

If the rebase completes with no conflicts, report that clearly and skip to Step 5.

### Step 4 — Resolve conflicts (repeat for each conflicted commit)

For every conflict that arises:

1. Run `git status` to list conflicted files.
2. Read each conflicted file with the Read tool.
3. Explain clearly:
   - **What the conflict is**: which changes are on main vs. the PR branch, and why they collide.
   - **How you are resolving it**: the reasoning — e.g. "keeping the PR change because main only added a whitespace fix", or "merging both sides because they edit different fields of the same object".
4. Apply the resolution using the Edit tool.
5. Stage the resolved file: `git add <file>`.
6. Once all files for this commit are resolved, continue: `git rebase --continue`.

If a conflict is ambiguous and you are not confident in the correct resolution, stop and explain the situation to the user before proceeding (in bulk mode: per Bulk mode step d.2). Do not guess on logic-affecting conflicts.

### Step 5 — Report this PR's result

- Show `git log --oneline origin/main..HEAD` so the user can verify the commit stack.
- Show `git diff origin/main...HEAD --stat` for a file-level summary.
- Note this PR's branch name (and whether it rebased clean or needed conflict resolution) — it feeds the consolidated command list printed once in **Finishing up**, rather than repeating the push reminder per PR.

## Finishing up (both modes)

Once all PR(s) for this invocation are done (or the run is halted early with work already applied), call `ExitWorktree` with `action: "keep"` — **never `"remove"`**. This skill never pushes, so a rebased branch exists nowhere but this worktree's local ref until the user pushes it; removing the worktree would delete whichever branch is currently checked out in it, discarding that unpushed rebase.

Report:
- In bulk mode, a summary of every PR processed: which rebased cleanly, which needed conflict resolution (and what was resolved), which were skipped and why.
- The worktree's absolute path, for the record (the user does not need to visit it otherwise).
- **A single consolidated, copy-pasteable command block** — this is the actionable output of the whole run, not just a reminder. List, in this order:
  1. One `git push --force-with-lease origin <branch>` line for **every** PR branch that came out of this run with rebased-but-unpushed commits (one line per branch — bulk mode can produce several; skip any PR that was skipped or hit an unresolved conflict).
  2. One trailing `git worktree remove <path>` line for this run's worktree, using its actual absolute path — this only becomes safe *after* every push above has landed, so say so plainly right above the block (e.g. "run the pushes first, then the worktree removal — removing it before pushing would discard the rebase").

  Example shape for a bulk run with two rebased PRs:
  ```bash
  git push --force-with-lease origin feat/sho-501-example
  git push --force-with-lease origin fix/sho-512-other-example
  git worktree remove /path/to/.claude/worktrees/rebase-pr-bulk-<short-id>
  ```
  These commands work from anywhere in the repo (no need to `cd` into the worktree first) — except `git worktree remove`, which can be run from anywhere *except* the worktree being removed.

If `ExitWorktree` itself fails, note that in the final summary rather than leaving the user to discover a stray worktree later.

## Hard rules

- **Never run `git push`** under any circumstances, in either mode.
- **Never run `git push --force`** or any push variant.
- **Never operate on `main` or any PR branch in the shared primary working directory.** Everything happens inside the worktree entered at the start — if any step seems to require touching the shared working directory, stop and ask the user instead.
- **Never call `ExitWorktree` with `action: "remove"`** — see Finishing up above.
- If the rebase produces a detached HEAD or unexpected state, stop and report it without taking further action. In bulk mode, do not continue to the next PR until the user says how to proceed.

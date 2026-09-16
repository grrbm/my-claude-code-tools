---
name: clean-worktree-force
description: Inspect exactly one stale git worktree — the worktree directory only, never its branch — for uncommitted/unpushed work, associated PR state, and how long since it was last touched, then hand back the exact `git worktree remove` command for the user to run themselves. Never runs the removal itself. Use when asked to clean up, check, or get the command for a specific worktree, or when a leftover worktree (e.g. from an old skill run) is found and needs clearing out. Does not touch branches — use a separate, explicit request for that.
argument-hint: <branch-name-or-worktree-directory-name>
allowed-tools: Bash(git *), Bash(gh *)
---

Inspect the single worktree identified by: $ARGUMENTS, and report the exact command to remove it yourself.

**This skill never deletes anything — it only inspects and reports.** It does not run `git worktree remove`, with or without `--force`, under any confirmation, no matter how clean the findings look. Its entire output is: the safety findings, plus the exact command line(s) for the user to copy and run themselves in their own terminal. Do not ask "should I go ahead and remove it?" — there is no "go ahead" this skill acts on; the answer is always "here's the command."

**This skill removes worktrees, not branches.** Those are two separate things in git: a worktree is a checked-out working directory; the branch it has checked out is a completely separate object that survives fine with no worktree attached to it at all. This skill's whole job ends at `git worktree remove` — it never runs `git branch -D`/`git branch -d`, on this branch or any other, under any confirmation. If the user also wants the branch deleted, that is a distinct request they need to make explicitly and separately; do not infer it from "clean up this worktree," do not offer it as a bundled follow-up step in the same confirmation, and do not do it "since it's already unmerged/unused anyway." A denied or unexpected `git branch -D` here is a sign this rule was violated, not a sign to retry with different phrasing.

This skill operates on **exactly one** worktree per invocation — never "all stale worktrees," never a bulk sweep. `$ARGUMENTS` may name the worktree either by its branch (e.g. `fix/sho-453-cart-ownership-ttl-sweep`) or by its worktree directory's basename (e.g. `pr-617-cart-ttl-ci-fix`, the last path segment shown by `git worktree list`) — people naturally refer to a worktree by whichever label they last saw. Naming it by branch is only ever used to *find* the right worktree row in Step 1 — it does not imply the branch itself is in scope for removal. If the user wants several cleaned up, that's several separate invocations, each with its own inspection and its own confirmation. Never infer or guess from partial input — if `$ARGUMENTS` doesn't clearly and uniquely identify one worktree, ask.

This is a different tool from `EnterWorktree`/`ExitWorktree`: those only ever touch a worktree the *current* session itself created. This skill exists specifically for the opposite case — a worktree left behind by a past session (crashed, interrupted, or from before some skill added its own cleanup step) — so it operates via a plain `git worktree` command, not those tools.

## Step 1 — Resolve the target worktree

```bash
git worktree list
```

Find the row where either the branch (the `[branch-name]` column) matches `$ARGUMENTS` exactly, or the worktree path's final segment (its directory basename) matches `$ARGUMENTS` exactly.

- **No match on either** → say so plainly ("No worktree matches `<name>` by branch or directory name.") and stop. Do not guess at a similarly-named branch or directory.
- **Matches more than one row** (shouldn't normally happen, but e.g. an ambiguous partial name) → stop and list the candidates; ask the user which one they mean rather than guessing.
- **The match is the main/primary working directory** (the first row, with no separate path under a worktree-specific location) → refuse. This skill only removes *linked* worktrees, never the repo's main checkout, regardless of what's on that branch. Stop and explain.
- **The match is the worktree this session is currently running in** (compare the resolved path against the current working directory) → refuse. Removing your own live working directory out from under yourself is not something to do automatically; tell the user to ask from a different session/directory instead.
- **Exactly one other match** → this is the target. Note its path and branch name; proceed to Step 2.

## Step 2 — Gather the safety signals

Run all of these against the target path (`git -C <path> ...`), never by `cd`-ing there:

1. **Uncommitted/untracked work**: `git -C <path> status --porcelain`. Any output at all is a red flag — list the files.
2. **Unpushed commits**: `git -C <path> fetch origin <branch> --quiet` then `git -C <path> log --oneline origin/<branch>..HEAD`.
   - If `origin/<branch>` doesn't exist at all (`fetch` reports the ref unknown), that means **this branch has never been pushed** — everything on it only exists in this worktree. Treat this as the highest-severity signal, not a minor note.
   - If it exists but the local branch is ahead, list the ahead commits (subject lines) — these would be lost too.
3. **Last local activity**: `git -C <path> log -1 --format='%h %cI %s' <branch>` for the last commit's date, and `stat -f '%Sm' -t '%Y-%m-%d %H:%M' <path>/.git/HEAD` (or the equivalent `HEAD` file under `.git/worktrees/<name>/HEAD` from the main checkout if `<path>/.git` is a file pointing there) for when the worktree last had a checkout/commit touch it. Report how long ago that was in plain terms ("last touched 34 days ago").
4. **Associated PR state**, best-effort: `gh pr list --head <branch> --state all --json number,url,state,mergedAt --repo <owner>/<repo>` (infer `<owner>/<repo>` from `git -C <path> remote get-url origin`). If a PR is found:
   - **Merged or closed** → reassuring signal, surface it as such ("PR #N is already merged/closed").
   - **Open** → flag it: removing the worktree doesn't touch the remote or the PR either way, but if unpushed commits exist (signal 2), that PR's remote state would no longer reflect this local work once the worktree holding it is gone.
   - **None found** → note it plainly; this branch was never opened as a PR, or none exists under this exact head ref.
5. **Can't detect**: be upfront in the warning that this skill cannot tell whether some *other* terminal or process currently has a shell `cd`'d into this worktree right now — only whether git itself has it locked (`git -C <path> worktree list` marks a locked worktree explicitly; if so, surface the lock reason and treat it as a strong reason to stop, not just warn).

## Step 3 — Present the findings and hand back the command

Summarize all of Step 2's signals plainly — don't bury a red flag in a wall of text. Lead with whichever is worst:

- If there are uncommitted changes, or the branch has never been pushed, or has unpushed commits, or is locked: state clearly that running the removal command **will permanently discard** that specific work, and name it. (The branch itself is never at risk here regardless — only files sitting uncommitted/unpushed in this checkout are.)
- Otherwise: state plainly that everything in this worktree already appears to be safely committed and pushed, so removal looks safe — but it's still a real, unrecoverable deletion of the local working directory once run.

Then give the exact command, ready to copy and run as-is, with the real resolved path substituted in:

```bash
git worktree remove <path>
```

If Step 2 found uncommitted/untracked files, note that plain `git worktree remove` will refuse for exactly that reason, and additionally give the force form for the user to use at their own discretion, clearly labeled as the more destructive option:

```bash
git worktree remove --force <path>
```

Do not run either command yourself, do not offer to run it, and do not treat any reply as authorization to run it — the only output of this skill is the findings plus the command text itself. If the user then explicitly asks you to run it as a separate, direct instruction, that is a new request outside this skill's own flow, not something this skill triggers on its own.

## Hard rules

- Never touch more than one worktree per invocation.
- **Never run `git worktree remove`, with or without `--force`, yourself — this skill only ever inspects and prints the command.** The user runs it in their own terminal.
- Never remove the main/primary working directory, and never remove the worktree the current session is itself running in. If Step 1 resolves to either, refuse (no command to hand back), don't just warn.
- **Never run `git branch -D`/`git branch -d`, on this branch or any other, for any reason.** This skill's scope ends at the worktree directory. Naming the target by its branch name is for lookup only (Step 1) and never implies the branch is in scope for deletion or for a command suggestion.
- Never force-push, push, or otherwise touch the remote — this skill's entire surface is read-only inspection plus printing a `git worktree remove` command line for someone else to run.
- If any command in Step 2 fails or is ambiguous, say so in the warning rather than silently treating the missing signal as "safe."

---
name: rebase-pr
description: Rebase a PR branch off main. Use when asked to "rebase this off main" with a PR URL. Checks out main, pulls it, checks out the PR branch, pulls it, then interactively rebases off main — explaining every conflict resolution. Never pushes.
argument-hint: <pr-url>
allowed-tools: Bash(git *), Bash(gh *)
---

Rebase the PR at: $ARGUMENTS off main.

## Step 1 — Parse the PR URL

Extract owner, repo, and PR number from the URL.

Use `gh pr view <number> --repo <owner>/<repo> --json headRefName` to get the branch name.

## Step 2 — Update main

```bash
git checkout main
git pull origin main
```

## Step 3 — Check out the PR branch and pull it

```bash
git checkout <branch>
git pull origin <branch>
```

## Step 4 — Rebase onto main

```bash
git rebase main
```

If the rebase completes with no conflicts, report that clearly and skip to Step 6.

## Step 5 — Resolve conflicts (repeat for each conflicted commit)

For every conflict that arises:

1. Run `git status` to list conflicted files.
2. Read each conflicted file with the Read tool.
3. Explain clearly:
   - **What the conflict is**: which changes are on main vs. the PR branch, and why they collide.
   - **How you are resolving it**: the reasoning — e.g. "keeping the PR change because main only added a whitespace fix", or "merging both sides because they edit different fields of the same object".
4. Apply the resolution using the Edit tool.
5. Stage the resolved file: `git add <file>`.
6. Once all files for this commit are resolved, continue: `git rebase --continue`.

If a conflict is ambiguous and you are not confident in the correct resolution, stop and explain the situation to the user before proceeding. Do not guess on logic-affecting conflicts.

## Step 6 — Report the result

After the rebase completes:

- Show `git log --oneline main..HEAD` so the user can verify the commit stack.
- Show `git diff main...HEAD --stat` for a file-level summary.
- Remind the user: **the branch has NOT been pushed**. They should inspect the result and then run `git push --force-with-lease origin <branch>` when satisfied.

## Hard rules

- **Never run `git push`** under any circumstances.
- **Never run `git push --force`** or any push variant.
- If the rebase produces a detached HEAD or unexpected state, stop and report it without taking further action.

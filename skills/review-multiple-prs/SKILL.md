---
name: review-multiple-prs
description: Review one or more GitHub pull requests. Use when asked to review a PR (or several at once) or given one or more PR URLs to review. For each PR, reads the full diff, all existing comments and reviews, and posts a single consolidated review comment. Multiple PRs are processed strictly one at a time, in the order given.
argument-hint: <pr-url-1> [pr-url-2] [...]
allowed-tools: Bash(gh *), Bash(unset GITHUB_TOKEN && gh *), Bash(touch *), Write(/private/tmp/pr-review-*.md)
---

Review the pull request(s) at: $ARGUMENTS

## Step 1 — Parse the PR list

Split `$ARGUMENTS` on whitespace and/or commas into individual PR URLs. Validate each looks like a GitHub PR URL (`https://github.com/<owner>/<repo>/pull/<number>`). If none are found, stop and ask the user for a URL. A single URL is valid input — everything below still applies with a list of one.

## Step 2 — Process each PR strictly in order

Never review PRs in parallel — process the list one PR at a time, start to finish, before moving to the next. This keeps output ordering predictable and avoids interleaving `gh` calls (and their console output) across unrelated PRs.

For each PR URL, in order:

1. Parse the URL to determine owner, repository, and pull request number.

2. Collect PR information:
   - title, description, changed files, full diff (`gh pr view`, `gh pr diff`)
   - existing issue comments (`gh api repos/<owner>/<repo>/issues/<number>/comments`)
   - existing review comments (`gh api repos/<owner>/<repo>/pulls/<number>/comments`)
   - all submitted reviews (`gh api repos/<owner>/<repo>/pulls/<number>/reviews`)

3. Read the entire diff before writing the review.

4. Read all previous comments and reviews first.

5. Verify whether previously reported issues are already resolved.

6. Write a consolidated review comment.

Requirements:

- Always read the diff before reviewing.
- Always read previous comments and reviews.
- Do not repeat feedback unless it is still unresolved.
- Base the review on the latest version of the PR.
- Focus on: bugs, regressions, edge cases, security, performance, maintainability, architecture.

Severity system:

Label every issue with one of the following severities:

- **[blocking]** — Must be fixed before merge. Bugs, regressions, security issues, data loss risks, or explicit violations of CLAUDE.md conventions.
- **[important]** — Should be fixed but won't block merge. Significant maintainability, performance, or correctness concerns.
- **[nit]** — Minor style, naming, or readability issue. Optional to address.

Do not invent issues to fill sections. Omit a section entirely if there is nothing to report.

Comment template:

Post the review using this exact structure:

```
## PR Review

### 📋 Summary
<1–3 sentence overview of what the PR does and your overall assessment.>

### 🚨 Blocking
<List of [blocking] issues. Each item: file path + line reference, clear description, and suggested fix.>
<If none: omit this section.>

### ⚠️ Important
<List of [important] issues with file path + line reference and explanation.>
<If none: omit this section.>

### 🔍 Nits
<List of [nit] items, grouped or brief.>
<If none: omit this section.>

### ✅ Strengths
<1–3 things done well. Always include this section.>
```

Posting behavior:
- Post a single consolidated PR comment using this exact two-step sequence:
  1. Use the Write tool with `file_path` set to exactly `/private/tmp/pr-review-<number>.md`, where `<number>` is this PR's number — no other path, no variation. This file is scoped per-PR so that reviewing multiple PRs in the same run (or in parallel terminals) never race on the same file. Only the `pr-review-*.md` glob is covered by the skill's allowed-tools; any other path will trigger a permission prompt.
  2. Post via exactly: `gh pr comment <number> -R <owner>/<repo> --body-file /private/tmp/pr-review-<number>.md`
  Never use `--body "..."` with inline multi-line text — markdown headers (`#`) after newlines in quoted arguments trigger a security prompt regardless of allow rules. Always use `--body-file /private/tmp/pr-review-<number>.md`.
- After posting the consolidated comment, determine the official GitHub review type:
  - If there are **no blocking issues**: submit an **approving** review via `unset GITHUB_TOKEN && gh pr review <pr-url> --approve --body "LGTM 🚀"`.
  - If there are **blocking issues**: submit a **comment** review via `unset GITHUB_TOKEN && gh pr review <pr-url> --comment --body "Reviewed"`. Never use `--request-changes` — it locks the PR merge gate requiring dismissal by the author, preventing them from re-requesting review.
- If review collection or posting fails outright for one PR (bad URL, PR not found, `gh` error), report the failure for that PR specifically and continue on to the next one rather than aborting the whole batch.

Move to the next PR only after this one's comment and official review are both posted (or the PR is confirmed to have failed).

## Step 3 — Signal completion

After every PR in the list has been processed (Step 2 complete for all), run: `touch "/tmp/.claude-review-done.${ITERM_SESSION_ID##*:}"`
This signals the Stop hook to close *this specific terminal window* once Claude finishes rendering its final response. The filename is scoped to this terminal's iTerm2 session ID so that when multiple review runs happen in parallel across different terminal windows, each one only closes its own window — never a sibling terminal that hasn't finished yet. Always run this once, as the very last command, after all PRs in the list are done — not per-PR. Do not use the bare `/tmp/.claude-review-done` path (no suffix); it is not scoped per-terminal and will race with other concurrent reviews.

## Rules

- Never process PRs in parallel — one at a time, in the order given.
- Do not ask for confirmation between PRs — process the whole list unattended once started.
- Never force-push or mutate the working tree — this skill is read-only against git (no checkout), it only reads via `gh` and posts comments/reviews.
- At the end, report one line per PR: approved (no blocking issues), commented (blocking issues found, listed), or failed (with reason).

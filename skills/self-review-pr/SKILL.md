---
name: self-review-pr
description: Review a GitHub pull request created by the user themselves. Use when the user asks to review "my PR", "my pull request", "the PR I created/opened/submitted", or asks for a "self-review". Acts as a second pair of eyes — reads the full diff and all existing comments, then writes a consolidated review focused on blind spots, missed edge cases, and things the author is likely to overlook due to familiarity with their own code, to a local file (never posted to the PR), and automatically implements the findings. Do NOT use this for reviewing someone else's PR — use the review-multiple-prs skill instead.
argument-hint: <pr-url>
allowed-tools: Bash(gh *), Bash(git *), Bash(touch *), Bash(curl *), Write(/private/tmp/self-review-*.md)
---

Review the pull request at: $ARGUMENTS

This is a self-review — you are acting as a second pair of eyes on the user's own code. The goal is to surface things the author is likely to miss because they wrote the code: assumed knowledge, overlooked edge cases, familiarity bias, and gaps in reasoning that feel obvious when you're in the middle of writing something but aren't obvious to anyone else.

Workflow:

1. Parse the PR URL to determine owner, repository, and pull request number.

2. Compute the review file path for this run: `/private/tmp/self-review-<project-slug>.md`, where `<project-slug>` is the basename of the current git repository root. Run this exact command, verbatim, character for character — do not substitute an equivalent like `${PWD##*/}`, `git rev-parse --show-toplevel` piped into a separate step, or any other rephrasing:
   ```bash
   basename "$(git rev-parse --show-toplevel)"
   ```
   A project-level `PermissionRequest` hook auto-allows exactly this command string (matched via `grep -q 'git rev-parse --show-toplevel'` against the raw command text); any rephrasing — even a semantically identical one — will not match and will force a manual permission prompt, breaking the "auto-approve everything" workflow this skill depends on. This keeps concurrent self-review sessions in different repos from clobbering each other's pending-findings file on the shared `/private/tmp` path. Use this exact path everywhere below that references "the review file" — never the bare `/private/tmp/self-review.md`.

3. Collect PR information:
   - title, description, changed files, full diff (`gh pr view`, `gh pr diff`)
   - existing issue comments (`gh api repos/<owner>/<repo>/issues/<number>/comments`)
   - existing review comments (`gh api repos/<owner>/<repo>/pulls/<number>/comments`)
   - all submitted reviews (`gh api repos/<owner>/<repo>/pulls/<number>/reviews`)
   - branch name (`gh pr view <number> -R <owner>/<repo> --json headRefName -q .headRefName`)

4. Check for merge conflicts with the base branch:
   - `gh pr view <number> -R <owner>/<repo> --json baseRefName,headRefName,mergeable -q '.'`
   - If `mergeable` is `"UNKNOWN"`, GitHub hasn't finished computing it yet — wait a couple seconds and re-check once before giving up.
   - If `mergeable` is `"CONFLICTING"`, find the exact conflicting files without touching the working tree or index:
     ```bash
     git fetch origin <baseRefName> <headRefName>
     git merge-tree --write-tree origin/<baseRefName> origin/<headRefName> | grep -P '\t' | cut -f2 | sort -u
     ```
     This lists every unmerged path (from the mode/oid/stage lines `git merge-tree` prints). Record these paths — they will be reported as a blocking issue below.
   - If `mergeable` is `"MERGEABLE"`, there is nothing to report here.

5. Find and fetch the linked Linear issue:
   - Scan the PR title, PR body, and branch name for a Linear issue identifier pattern (e.g. `SHO-123`, `[A-Z]+-\d+`). The branch name is often the most reliable source.
   - If found, fetch the full issue and all comments using `$LINEAR_API_KEY` directly (bare variable reference). Issue this `curl` as a single, standalone Bash command — exactly the lines below, nothing more:
     ```bash
     curl -s https://api.linear.app/graphql \
       -H "Content-Type: application/json" \
       -H "Authorization: $LINEAR_API_KEY" \
       -d '{ "query": "{ issues(filter: { number: { eq: <NUMBER> }, team: { key: { eq: \"<TEAM_KEY>\" } } }) { nodes { title description comments { nodes { body createdAt user { name } } } } } }" }'
     ```
     Do NOT modify this into a compound command: no `$(grep ...)` extraction in the same call, no `-o <file>` redirect, no piping into another command, no appended second statement (e.g. `echo done`) on a following line. Any of those turns it into a multi-statement script, which gets flagged as unanalyzable and forces a manual permission prompt on every run — even though `Bash(curl *)` is already allowed and the bare `$LINEAR_API_KEY` reference on its own is not the problem. Let curl print its JSON straight to stdout; if the response is large, read/filter it in a *separate*, subsequent tool call rather than folding that into this same command. Parse the team key (e.g. `SHO`) and issue number (e.g. `368`) from the identifier for the query above.
   - Read the full issue description and every comment. Comments often contain post-ticket decisions, scope changes, reviewer feedback, and clarifications that are just as authoritative as the original description.
   - If the key cannot be read or the issue cannot be found, skip this step gracefully.

6. Check for unanswered "Questions for your team":
   - In the Linear issue description, look for a section titled "Questions for your team" (or similar headings: "Questions ❓", "Open questions", "❓"). Extract each question.
   - For every question found, determine whether it has been answered in any of these places:
     a. The Linear issue comments (a reply that directly addresses the question counts)
     b. The PR description body
     c. The existing PR comments or reviews already collected
   - A question is "answered" if there is explicit text that responds to it — not just the passage of time or the PR being open.
   - Track which questions remain unanswered. These will be surfaced in the review comment.

7. Read the entire diff before writing the review.

8. Read all previous PR comments and reviews. Do not repeat feedback that is already addressed.

9. Review with an outsider's eye — imagine you are a teammate seeing this code for the first time, without any of the context the author had while writing it. Treat the Linear issue description and all its comments as authoritative context: they often contain design constraints, scope decisions, and known trade-offs that the PR description doesn't repeat.

Review focus (in priority order):

- **Correctness bugs**: Logic errors, off-by-one errors, wrong conditions, unintended mutations.
- **Edge cases the author likely didn't test**: Empty inputs, null/undefined, concurrent access, network failure mid-operation, large payloads, race conditions.
- **Familiarity blind spots**: Variable names or abstractions that make sense to the author but will confuse a reader. Missing comments where the *why* is non-obvious. Code that assumes context not present in the diff.
- **Error handling gaps**: Missing try/catch, unhandled promise rejections, silent failures, errors swallowed without logging.
- **Simplification opportunities**: Logic that could be expressed more clearly or with fewer moving parts — not style nitpicks, but genuine complexity reduction.
- **Security and data safety**: Injection risks, exposed secrets, unvalidated user input, unsafe use of eval or dynamic queries.
- **Missing tests or test gaps**: Cases that the test suite doesn't cover that could realistically break.

Severity system:

Label every issue with one of the following:

- **[blocking]** — Must be fixed before merge. Bugs, regressions, security issues, data loss risks, explicit violations of CLAUDE.md conventions, or merge conflicts with the base branch found in step 3.
- **[important]** — Should be fixed but won't block merge. Significant maintainability, performance, or correctness concerns.
- **[nit]** — Minor style, naming, or readability issue. Optional to address.

Do not invent issues to fill sections. Omit a section entirely if there is nothing to report.

Review template:

Write the review using this exact structure:

```
## Self-Review

### 📋 Summary
<1–3 sentence overview of what the PR does and your overall assessment as a second pair of eyes.>

### 🚨 Blocking
<If step 3 found merge conflicts, list this first: "Merge conflicts with <baseRefName> in: <file1>, <file2>, ..." with an instruction to merge <baseRefName> into the branch and resolve them.>
<[blocking] issues: file path + line reference, clear description, and suggested fix.>
<If none: omit this section.>

### ⚠️ Important
<[important] issues with file path + line reference and explanation.>
<If none: omit this section.>

### 🔍 Nits
<[nit] items, grouped or brief.>
<If none: omit this section.>

### 🕳️ Blind Spots
<Things the author likely didn't notice because they wrote the code: assumed context, unclear naming, missing "why" comments, edge cases that feel obvious from the inside but aren't. If none: omit this section.>

### ❓ Open Questions
<Questions from the Linear issue's "Questions for your team" section that have not been answered in the Linear comments or PR body. List each unanswered question verbatim and tag @team (or the relevant person if known) so the team knows these need resolution. Only include questions that are genuinely unanswered — do not repeat questions that already have replies. If all questions are answered, omit this section entirely. Do not add this section if no Linear issue was found.>

### ✅ What's working well
<1–3 things done well. Always include this section.>
```

Output behavior:
- Write the review using the Write tool with `file_path` set to the review file path computed in step 2 (`/private/tmp/self-review-<project-slug>.md`). This matches the skill's allowed-tools glob (`Write(/private/tmp/self-review-*.md)`). Always use this same path on every run within this project.
- The Write tool fully overwrites the file's contents on every call, which is what "always clear it completely before writing" means in practice — there is no separate delete/clear step. Just call Write with the new review content each time.
- Do NOT post the review content itself to the PR. Self-reviews stay local — this is intentional, since posting the full review as a PR comment on every round was bloating the PR. The only exception is the "nothing to implement" case below.

Branch on severity, after writing the file:

- **If the review has no `### 🚨 Blocking` section and no `### ⚠️ Important` section** (nits/blind spots/open questions don't count): this is the exception case. Post a single short comment and stop here — do NOT invoke `implement-self-review`:
  - `gh pr comment <number> -R <owner>/<repo> --body "Self-review process finished. Nothing blocking or important left."`
  - Clear the auto-continue round counter, since the chain ended cleanly: `rm -f /tmp/.claude-self-review-rounds-<owner>-<repo>-<number>` (same naming convention `implement-self-review` uses — replace any `/` in owner/repo with `-`). Without this, a stale count from this chain could wrongly cap a future, unrelated review chain on the same PR.
  - Then run `touch "/tmp/.claude-review-done.${ITERM_SESSION_ID##*:}"` as the last command. This filename is scoped to this terminal's iTerm2 session ID so the Stop hook closes only this window, not a sibling terminal running another review in parallel — do not use the bare `/tmp/.claude-review-done` path.
- **Otherwise** (at least one Blocking or Important item exists): do not post anything to the PR. Immediately invoke the `implement-self-review` skill with the same PR URL (`$ARGUMENTS`) as the argument. Do not ask the user for confirmation — proceed directly into implementation.
  - After the `implement-self-review` skill fully completes, run as the very last command: `touch "/tmp/.claude-review-done.${ITERM_SESSION_ID##*:}"`. Do NOT run this before implement-self-review finishes.

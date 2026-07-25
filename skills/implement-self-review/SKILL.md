---
name: implement-self-review
description: Implement pending self-review findings on a GitHub PR, then commit and push the fixes automatically. Use when asked to implement self-review feedback, or as the automatic follow-up invoked at the end of self-review-pr. Gathers full context — PR description, all PR comments/reviews, the linked Linear issue description and all its comments — plus the self-review written to /private/tmp/self-review-<project-slug>.md, implements unresolved items, then commits and pushes. After pushing, automatically opens a fresh VS Code terminal (via the Claude Terminal Bridge extension) to kick off the next self-review round, capped at 3 automatic rounds per PR. Never posts anything to the PR.
argument-hint: <pr-url>
allowed-tools: Bash(gh *), Bash(git *), Bash(curl *), Bash(ps *), Read, Glob, Grep, Edit, Write
---

Implement pending self-review findings for: $ARGUMENTS

Workflow:

1. Parse the PR URL to determine owner, repository, and PR number.

2. Collect PR information using GitHub CLI:
   - PR title, description, and current diff (`gh pr view`, `gh pr diff`)
   - All issue-level comments (`gh api repos/<owner>/<repo>/issues/<number>/comments`)
   - All review comments on the diff (`gh api repos/<owner>/<repo>/pulls/<number>/comments`)
   - All submitted reviews (`gh api repos/<owner>/<repo>/pulls/<number>/reviews`)
   - Branch name (`gh pr view <number> -R <owner>/<repo> --json headRefName -q .headRefName`)

3. Find and fetch the linked Linear issue:
   - Scan the PR title, PR body, and branch name for a Linear issue identifier pattern (e.g. `SHO-123`, `[A-Z]+-\d+`). The branch name is often the most reliable source.
   - If found, fetch the full issue description and ALL comments using `$LINEAR_API_KEY` directly (bare variable reference). Issue this `curl` as a single, standalone Bash command — exactly the lines below, nothing more:
     ```bash
     curl -s https://api.linear.app/graphql \
       -H "Content-Type: application/json" \
       -H "Authorization: $LINEAR_API_KEY" \
       -d '{ "query": "{ issues(filter: { number: { eq: <NUMBER> }, team: { key: { eq: \"<TEAM_KEY>\" } } }) { nodes { title description comments { nodes { body createdAt user { name } } } } } }" }'
     ```
     Do NOT modify this into a compound command: no `$(grep ...)` extraction in the same call, no `-o <file>` redirect, no piping into another command, no appended second statement (e.g. `echo done`) on a following line. Any of those turns it into a multi-statement script, which gets flagged as unanalyzable and forces a manual permission prompt on every run — even though `Bash(curl *)` is already allowed and the bare `$LINEAR_API_KEY` reference on its own is not the problem. Let curl print its JSON straight to stdout; if the response is large, read/filter it in a *separate*, subsequent tool call rather than folding that into this same command. Parse the team key (e.g. `SHO`) and issue number (e.g. `368`) from the identifier for the query above.
   - Read the full issue description and every comment — these often contain scope decisions, design constraints, and clarifications that are as authoritative as the PR description itself.
   - If the key cannot be read or the issue cannot be found, skip this step gracefully.

4. Compute the review file path: `/private/tmp/self-review-<project-slug>.md`, where `<project-slug>` is the basename of the current git repository root (`basename "$(git rev-parse --show-toplevel)"`, e.g. `shopit-monorepo`). This must match the path `self-review-pr` wrote to — both skills derive it the same deterministic way, so no explicit hand-off is needed. Never read the bare `/private/tmp/self-review.md` — that shared, non-project-scoped path can be overwritten by a concurrent self-review session in a different repo.

5. Read the file from step 4 if it exists and is non-empty. This is the list of pending action items for this round — it's the review self-review-pr just wrote. Treat every item under its `### 🚨 Blocking`, `### ⚠️ Important`, and `### 🔍 Nits` sections as pending work. Items under `### ❓ Open Questions` require team input and must never be auto-implemented. Items under `### 🕳️ Blind Spots` are observations — implement one only if it describes a concrete, unambiguous code fix; otherwise leave it as a carried-forward note.

6. If the review file is missing or empty (e.g. this skill was invoked standalone, not via the self-review-pr chain), use the PR comments/reviews collected in step 2 as the source of pending items instead: act only on comments/reviews requesting changes that have NOT already been addressed in a subsequent commit or reply.

7. Use the PR description, existing PR comments, and the Linear issue description + comments from steps 2–3 as context to resolve ambiguity while implementing — e.g. a judgment call between two approaches should follow a decision already recorded in a Linear comment rather than be re-litigated.

8. Check out the PR branch locally if not already on it:
   - `gh pr checkout <number>`

9. If the self-review's `### 🚨 Blocking` section lists merge conflicts with the base branch (e.g. "Merge conflicts with main in: <files>"), resolve them first, before any other finding:
   - `git fetch origin <baseRefName>` then `git merge origin/<baseRefName>`.
   - For each conflicting file, resolve the conflict markers using the surrounding code, the PR description, and the Linear issue context to determine correct intent — never blindly keep "ours" or "theirs" without reading both sides.
   - `git add <resolved files>` then `git commit` to complete the merge (accept git's default merge commit message). Do not combine this with the commit in step 11 — it must land as its own commit.
   - Push this merge commit to the PR branch before implementing other findings.

10. Implement all other pending requested changes.

11. Commit and push the changes — do NOT leave this to the user:
   - Stage exactly the files you modified using `git add <file1> <file2> ...` — never `git add -A` or `git add .`.
   - Write the commit message to `/private/tmp/self-review-commit-msg.txt` using the Write tool (not Bash). First line must start with `Self-review:`, followed by a one-bullet-per-item summary of what was changed and why, and any items intentionally skipped and the reason. End the message with `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`.
   - Commit using `git commit -F /private/tmp/self-review-commit-msg.txt` — never use `$(cat <<'EOF'...EOF)` or any other form of command substitution in the commit command; it makes the command unanalyzable and triggers a manual permission prompt.
   - Never prefix git commands with `cd /path/to/repo &&`. Run `git add`, `git commit`, and `git push` directly — the working directory is already the project root, and prefixing with `cd` breaks the `Bash(git *)` allow rule and triggers an "untrusted hooks" security warning.
   - Push to the PR branch.

12. Auto-continue the self-review chain, capped so it can't loop forever:
   - Counter file: `/tmp/.claude-self-review-rounds-<owner>-<repo>-<number>` (replace any `/` in owner/repo with `-`). This naming convention is shared with `self-review-pr`, which clears the file when a round comes back clean. Use the `Read` tool to check the current count (treat a missing file as `0`), then the `Write` tool to write the incremented value back — no `Bash` needed for the counter at all.
   - `MAX_AUTO_ROUNDS` is **6**. If the incremented count is greater than 6, stop here — do not open a terminal. Say so plainly in your final response (e.g. "Stopped the automatic self-review chain after 6 rounds — this PR may still need a manual look.").
   - Otherwise, open a fresh terminal via the Claude Terminal Bridge extension using four simple, statically-analyzable steps. Do NOT combine these into one multi-line Bash script with `$(...)` command substitution and an `if` guard — that shape gets flagged as "cannot be statically analyzed" and forces a manual permission prompt on every single run, no matter what's in `allowed-tools` or `settings.json`. A flat, literal command is what actually auto-approves:
     1. Use the `Read` tool to read `~/.claude-terminal-bridge-token`. If it's missing or empty, skip straight to the non-fatal handling below.
     2. Get the caller's process-ancestry chain, which the bridge uses to find the exact VS Code window this session is running in (its integrated terminal's shell PID will appear in this chain) — this is the precise routing signal, and works correctly even if the same folder happens to be open in more than one window. Get this with two flat, single-purpose `ps` commands instead of a loop/`if`/`$(...)` script — that compound shape is exactly what triggers "cannot be statically analyzed" and a manual approval prompt on every single run, even with `Bash(ps *)` already allowed:
        ```bash
        ps -o pid,ppid= -p $$
        ```
        A single flat command (no subshell, no control flow) that prints this shell's own PID and its immediate parent PID, e.g. `43989 40998`. Use this exact literal string every time — a `PermissionRequest` hook in `.claude/settings.local.json` auto-allows it by matching the fixed substring `pid,ppid= -p $$`; changing the flags here would silently break that auto-approval and reintroduce a manual prompt on every run.
        ```bash
        ps -A -o pid,ppid,comm
        ```
        Dumps the full process table in one flat call. Using the PID from the first command, walk the ancestry chain yourself by reading the second command's output — find the row whose `pid` matches the current PID, note its `ppid`, then find the row whose `pid` matches that `ppid`, and repeat. Stop after 8 hops or as soon as a `ppid` of `0`, `1`, or no match is reached, whichever comes first. Build the comma-separated PID list from this walk yourself, e.g. `43989,40998,40698,20164,19787` — do not try to compute it in the shell.
     3. Use the `Write` tool to write the request body as literal JSON to `/private/tmp/claude-terminal-bridge-body.json`. Substitute `<N>` with the exact incremented value you just wrote to the counter file — e.g. if the counter file now contains `3`, write `Self-review round 3`, not `2`, not `round 1+1`, the literal number from the file. Substitute the PR URL directly (plain JSON-string escaping only, e.g. escaping the `"` around `Self review this pr: ...`). Set `callerPids` to the JSON array from step 2. Also set `cwd` to the absolute path of the current project root (the working directory this skill is running in) as a fallback the bridge uses only if no window's terminal PIDs match `callerPids`:
        ```json
        {"name": "Self-review round <N>", "cmd": "claude \"Self review this pr: <PR_URL>\"", "cwd": "<PROJECT_ROOT_ABSOLUTE_PATH>", "callerPids": [<PID_LIST_FROM_STEP_2>]}
        ```
     4. Run a single flat `curl` command via `Bash`, with the token value from step 1 substituted in directly as literal text (not a shell variable):
        ```bash
        curl -s -X POST http://127.0.0.1:61337/open-terminal -H "X-Token: <TOKEN_VALUE>" -H "Content-Type: application/json" -d @/private/tmp/claude-terminal-bridge-body.json
        ```
        Because this has no `$(...)`, no `if`, and no pipes — just literal arguments — it matches this skill's `Bash(curl *)` allowed-tools entry and runs without a prompt.
   - The `callerPids` field exists so the bridge opens the terminal in the exact VS Code window this session is already running in, rather than guessing by folder path — this matters when the same project folder happens to be open in more than one window.
   - If the token file was missing/empty, or the `curl` call errors or fails (extension not installed, VS Code not running, wrong port), treat this as non-fatal: mention it in your final response, but do not treat the task as failed. The commit/push already succeeded — that's this skill's actual job; the auto-continue is a convenience layered on top.

Rules:

- Always read the full self-review file, the PR description/comments, and the Linear issue + its comments before touching any code.
- Never implement something that is already resolved in the current diff.
- If an item is ambiguous, make a reasonable judgment informed by the Linear/PR context and note it in the commit message.
- When listing skipped items in the commit message, the reason must accurately reflect WHY it was skipped. Never say "out of scope" for an open question — the real reason is that it requires team input that cannot be resolved by an implementation pass alone. Say that instead.
- Do not ask for confirmation before implementing — just do it.
- Do not leave placeholder TODOs; fully implement each change.
- Follow all existing code conventions.
- When running the linter/formatter, always use `bunx biome check --write <file>` — never `npx biome`. The project uses bun as the package manager.
- If the PR branch does not exist locally, check it out automatically.
- ALWAYS commit and push when finished — never leave that to the user. Never force-push.
- Do NOT post any comment or review to the PR. All output from this skill is the commit(s) pushed to the branch — nothing is written back to GitHub as a comment.
- ALWAYS attempt step 12 (auto-continue) after a successful push, respecting the 3-round cap. Never raise the cap or skip the counter file as a shortcut — the cap exists specifically to bound an otherwise-unattended loop of automatic `git push`es.

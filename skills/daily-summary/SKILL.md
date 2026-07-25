---
name: daily-summary
description: Generate a daily work summary. Use ONLY when the user asks what they did "today", "today and yesterday", "summarize my day", or similar. Do NOT trigger for weekly reports or general recent activity.
allowed-tools: Bash(git *), Bash(printf *), Bash(mkdir *), Bash(open *), Read
---

Generate a plain-English summary of what was worked on today (and yesterday if asked).

## Step 1 — Determine the date(s) to cover

Use the `currentDate` from context. If the user asked about "today and yesterday", cover both days. If just "today", cover today only.

## Step 2 — Read memory files

Read all files in:
`/Users/guilhermereis/.claude/projects/-Users-guilhermereis-Desktop-clones-shopit-monorepo/memory/`

Look for `project` type memory entries logged on the relevant date(s).

## Step 3 — Check git log and PRs as a supplement

```bash
git log --since="YYYY-MM-DD 00:00" --until="YYYY-MM-DD 23:59" --format="%s" --author="Guilherme"
```

Run once per day being covered. Use this to catch anything not in memory.

Also check PRs opened or merged on the target date using:
```bash
gh pr list --state=merged --limit=50 --json number,title,mergedAt,createdAt,author | jq '.[] | select(.author.login == "grrbm")'
```

## Step 4 — Synthesize

Write exactly two sentences:
- One sentence per day when covering two days.
- Two sentences total when covering one day.

Rules:
- No bullet points, no headers, no blank lines between sentences — just two plain lines.
- No technical terms, no function names, no file paths, no ticket/PR numbers, no jargon.
- Start each sentence with the action directly — never use "I" or "me".
- Focus on what changed from a product/user perspective, not implementation details.
- Never write filler sentences like "No other work was merged or started that day" or "X was focused on getting Y across the finish line." Every sentence must describe a concrete action.
- If the target day has only one distinct thing to say, fill the second sentence using this priority order:
  1. A different angle or detail from the same day's work (ideal)
  2. Something from the day before that hasn't already been said
  3. Something from the day after that hasn't already been said
- Never repeat content that was already used in the other sentence.

## Step 5 — Write and print

Write the two sentences to:
`/tmp/daily-summary.md`

Use `printf` via Bash to write the file (do NOT use the Write tool — it is not in allowed-tools):

```bash
printf '%s\n%s\n' "SENTENCE_ONE" "SENTENCE_TWO" > /tmp/daily-summary.md
```

Overwrite the file each time. Then open the file and print the same two sentences inline in the response:

```bash
open -a TextEdit /tmp/daily-summary.md
```

This path is fixed and reused across runs, so a TextEdit window left open from a previous run will not auto-reload — it keeps showing its old buffer even though the file on disk was just overwritten. If the user reports content that doesn't match what you just wrote, tell them to close and reopen the window rather than trusting what's on screen.

Always state the file's full absolute path (`/private/tmp/daily-summary.md`) at the end of the response — never omit this.

## Example output

```
Shipped infinite scroll and person search on the search tab, and added a contextual prompt at the end of the For You feed to encourage users to connect with friends.
Cleaned up the end-of-feed button to use the shared design system component and addressed review feedback to eliminate duplicated code.
```

---
name: daily-summary
description: Generate a daily work summary. Use ONLY when the user asks what they did "today", "today and yesterday", "summarize my day", or similar. Do NOT trigger for weekly reports or general recent activity.
allowed-tools: Bash(git *), Bash(printf *), Bash(mkdir *), Read
---

Generate a plain-English summary of what was worked on today (and yesterday if asked).

## Step 1 — Determine the date(s) to cover

Use the `currentDate` from context. If the user asked about "today and yesterday", cover both days. If just "today", cover today only.

## Step 2 — Read memory files

Read all files in:
`/Users/guilhermereis/.claude/projects/-Users-guilhermereis-Desktop-clones-shopit-monorepo/memory/`

Look for `project` type memory entries logged on the relevant date(s).

## Step 3 — Check git log as a supplement

```bash
git log --since="YYYY-MM-DD 00:00" --until="YYYY-MM-DD 23:59" --format="%s" --author="Guilherme"
```

Run once per day being covered. Use this to catch anything not in memory.

## Step 4 — Synthesize

Write exactly two sentences:
- One sentence per day when covering two days.
- Two sentences total when covering one day.

Rules:
- No bullet points, no headers, no blank lines between sentences — just two plain lines.
- No technical terms, no function names, no file paths, no ticket/PR numbers, no jargon.
- Start each sentence with the action directly — never use "I" or "me".
- Focus on what changed from a product/user perspective, not implementation details.
- If nothing was done on a given day, say so honestly in that sentence.

## Step 5 — Write and print

Write the two sentences to:
`/Users/guilhermereis/Desktop/clones/shopit-monorepo/.claude/daily-summary.md`

Use `printf` via Bash to write the file (do NOT use the Write tool — it is not in allowed-tools):

```bash
printf '%s\n%s\n' "SENTENCE_ONE" "SENTENCE_TWO" > /Users/guilhermereis/Desktop/clones/shopit-monorepo/.claude/daily-summary.md
```

Overwrite the file each time. Then print the same two sentences inline in the response.

## Example output

```
Shipped infinite scroll and person search on the search tab, and added a contextual prompt at the end of the For You feed to encourage users to connect with friends.
Cleaned up the end-of-feed button to use the shared design system component and addressed review feedback to eliminate duplicated code.
```

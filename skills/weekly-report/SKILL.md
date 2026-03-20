---
name: weekly-report
description: Generate a weekly work report based on PRs created by the user. Use ONLY when the user explicitly asks for a "weekly report" or asks what was done "this week" / "last week". Do NOT trigger for questions about today, a single day, or general recent activity.
allowed-tools: Bash(gh *), Bash(date *), Bash(python3 *)
---

Generate a weekly work report from PRs created by the authenticated GitHub user.

## Step 1 — Ask the user to pick a time range

Reply with exactly this:

> Which period would you like the report for?
>
> **1)** This week (since Monday $MONDAY_0)
> **2)** Last week (since Monday $MONDAY_1)
> **3)** Two weeks ago (since Monday $MONDAY_2)
> **4)** Three weeks ago (since Monday $MONDAY_3)
> **5)** Four weeks ago (since Monday $MONDAY_4)

To compute the dates, run:

```bash
python3 -c "
from datetime import datetime, timedelta
today = datetime.now()
days_since_monday = today.weekday()
mondays = [(today - timedelta(days=days_since_monday + 7*i)).strftime('%Y-%m-%d') for i in range(5)]
for i, d in enumerate(mondays):
    print(f'{i}: {d}')
"
```

Fill in the $MONDAY_N placeholders with the computed dates before presenting the options. Wait for the user to reply with a number (1–5).

## Step 2 — Compute the start timestamp

Based on the user's choice, compute the start date as the corresponding Monday at 00:01 AM local time, formatted as ISO 8601 (e.g. `2026-03-09T00:01:00`).

## Step 3 — Fetch the authenticated GitHub user

```bash
gh api user --jq '.login'
```

## Step 4 — Fetch all PRs created by the user since the start date

```bash
gh search prs --author=<login> --created=">YYYY-MM-DDTHH:MM:SS" --json number,title,body,url,repository,createdAt,mergedAt --limit 100
```

Use the start timestamp from Step 2. If the repo context is known, scope to the current repo with `--repo <owner>/<repo>` to avoid noise from other repositories.

## Step 5 — Read all PR descriptions

For each PR returned, note:
- PR title
- PR body / description (the full text)
- Repository name
- `mergedAt` date (use this as the display date; fall back to `createdAt` if not yet merged)

Ignore PRs whose body is empty or only contains template placeholders.

## Step 6 — Summarize

Write a concise, plain-English summary of what was worked on during the period. Format as a standup-style bullet list grouped by theme or feature area (not by PR number).

Rules for the summary:
- One bullet per meaningful area of work — not one per PR.
- Each bullet must start with the date in **Mar DD** format, followed by a dash, then the summary. Example: `- **Mar 17** — Webhook deduplication made persistent — Replaced...`
- If multiple PRs were grouped into one bullet, use the date of the most recent one in the group.
- No jargon, no file paths, no function names.
- Focus on the "what" and "why" from a product/user perspective.
- End with a count: "X PRs in total over this period."
- Do not mention PR numbers or URLs in the summary unless explicitly asked.

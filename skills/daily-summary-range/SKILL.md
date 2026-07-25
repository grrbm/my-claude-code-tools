---
name: daily-summary-range
description: Generate a plain-English daily work summary for every weekday across a date range (max 30 days) — one two-sentence entry per working day, no gaps, weekends skipped, days without direct evidence inferred from the nearest adjacent day — separated by dashed lines, written to a uniquely timestamped file. Use when the user asks for a summary "from X to Y", a "range" of days, or wants the daily-summary format repeated over multiple days. Do NOT trigger for a single day (use daily-summary) or for a calendar week (use weekly-report).
allowed-tools: Bash(git *), Bash(gh *), Bash(jq *), Bash(python3 *), Bash(printf *), Bash(date *), Bash(mkdir *), Bash(open *), Read
---

Generate a per-day plain-English work summary for every day in a date range, formatted as one two-sentence entry per day, separated by dashed lines, all written to a single timestamped file.

## Step 1 — Determine the date range

If the user's invocation already included both a start date and an end date, use them.

Otherwise ask exactly:

> What start and end date would you like the range summary for? (max 30 days)

Wait for the reply before continuing.

Once you have both dates, validate:
- End date must be on or after the start date.
- The range (inclusive) must not exceed 30 days. If it does, tell the user the max is 30 days and ask them to narrow the range — do not silently truncate it.

## Step 2 — Enumerate the days in the range

```bash
python3 -c "
from datetime import datetime, timedelta
start = datetime.strptime('YYYY-MM-DD', '%Y-%m-%d')
end = datetime.strptime('YYYY-MM-DD', '%Y-%m-%d')
d = start
while d <= end:
    if d.weekday() < 5:  # Mon=0 ... Fri=4, skip Sat/Sun
        print(d.strftime('%Y-%m-%d'))
    d += timedelta(days=1)
"
```

Fill in the actual start/end dates. Weekend dates (Saturday, Sunday) are excluded entirely — they never get an entry, even if a commit happens to be timestamped on one (fold any such commit into the nearest adjacent weekday when synthesizing). This gives you the ordered list of weekday-only days to cover.

## Step 3 — Gather signal for the whole range in one pass

Don't repeat lookups per day — fetch once for the full range, then bucket by date.

Read memory `project`-type entries from:
`/Users/guilhermereis/.claude/projects/-Users-guilhermereis-Desktop-clones-shopit-monorepo/memory/`
Note which ones fall within the range.

```bash
git log --all --since="START_DATE 00:00" --until="END_DATE 23:59" --format="%ad|%s" --date=format:"%Y-%m-%d" --author="Guilherme"
```

`--all` is required, not optional — a plain `git log` only walks commits reachable from the currently checked-out branch (typically `main`), so it silently misses everything sitting on an unmerged feature branch. Work-in-progress days (a branch with commits that hasn't merged yet within the range, or at all) will read as empty without it.

```bash
gh pr list --state=merged --limit=100 --json number,title,mergedAt,createdAt,author | jq '.[] | select(.author.login == "grrbm")'
```

Also check for PRs opened in-range but not yet merged, or merged after the range ends (both are easy to miss since the merged-PR query above filters on `mergedAt`):

```bash
gh pr list --state=all --limit=100 --json number,title,state,mergedAt,createdAt,author | jq '.[] | select(.author.login == "grrbm") | select(.createdAt >= "START_DATE" and .createdAt < "END_DATE_PLUS_ONE")'
```

Group every commit and PR by date using **both** fields — `mergedAt`/commit date (what shipped) and `createdAt` (what started). A day where a PR was opened but not yet merged still counts as an activity day: it just gets framed as work-in-progress rather than something that shipped. Without this, a day where work began but nothing landed until later reads as empty, which is wrong — the day was not idle. If a PR's `createdAt` day differs from its `mergedAt`/commit day, both days get an entry: the earlier day frames it as started/in-progress, the later day frames it as shipped, and neither repeats the other's exact phrasing. A PR that merges after the range ends still gets an in-progress entry on the day(s) it had commits inside the range.

Note: a commit's date can shift by one calendar day depending on whether it's read in the committer's recorded timezone offset (what `git log` shows by default) versus UTC (what the GitHub API returns for `mergedAt`/`createdAt`). If the same underlying merge appears to land on two different adjacent days across these two sources, that's a timezone artifact, not separate work — attribute it once, to the day the commit itself shows.

## Step 4 — Synthesize exactly two sentences for every weekday

Every weekday enumerated in Step 2 gets an entry — never skip one. The user works two shifts each working day, so every entry is two one-liner sentences, one shift's worth of substance apiece. The only days excluded are weekends (already dropped in Step 2); there is no such thing as an empty working day in the output.

Write each entry using the same tone rules as the `daily-summary` skill:
- No bullet points, no headers, no blank line between the two sentences.
- No technical terms, function names, file paths, ticket numbers, or PR numbers.
- Start each sentence with the action directly — never "I" or "me".
- Focus on product/user-visible impact, not implementation detail.
- Never write filler sentences ("no other work was done", "focused on getting X across the line").

When a weekday has direct signal (a commit, PR, or memory entry dated that day):
- If there are two or more distinct things, one per sentence.
- If there's only one distinct thing, fill the second sentence with a different angle or detail from that same day's work — don't repeat the first sentence's content.

When a weekday has **no** direct signal of its own, it still must not be skipped — infer its two sentences from the nearest day that does have signal:
1. Prefer the closest day *after* it within the range that has signal, framing the entry as the lead-up to what shipped then (e.g., "was underway", "in progress on", "continued building toward").
2. If no day after it in the range has signal, fall back to the closest day *before* it, framing the entry as the work still being carried forward/refined from there.
3. Every inferred sentence must be grounded in a real commit, PR, or memory entry that exists somewhere in the range — paraphrase and reframe that real evidence, never invent unrelated work.
4. Don't reuse the exact same sentence text as the adjacent day's own entry — describe the same underlying work from a different angle so the two entries read as distinct days, not a copy-paste.

## Step 5 — Write the file

Build a filename unique to this run, timestamped:

```bash
mkdir -p /tmp
TS=$(date +%Y%m%d_%H%M%S)
FILE="/tmp/daily-summary-range-${TS}.md"
```

Each day's entry is three lines: a date header formatted `Month/DD/YYYY` (e.g. `July/01/2026` — full month name, zero-padded day, four-digit year), then the two one-liner sentences. Separate consecutive day-entries with a line of exactly 63 dashes. Do not add a trailing separator after the last entry. Use `printf` (do NOT use the Write tool — it is not in allowed-tools), appending one day at a time in chronological order, e.g.:

```bash
printf '%s\n%s\n%s\n' "July/01/2026" "SENTENCE_ONE_DAY_1" "SENTENCE_TWO_DAY_1" > "$FILE"
printf '%s\n' "---------------------------------------------------------------" >> "$FILE"
printf '%s\n%s\n%s\n' "July/02/2026" "SENTENCE_ONE_DAY_2" "SENTENCE_TWO_DAY_2" >> "$FILE"
```

Continue this pattern (separator, then date header, then entry) for every weekday in the range — no gaps — stopping after the last day's entry with no trailing separator. To derive the `Month/DD/YYYY` header from a `YYYY-MM-DD` day, use:

```bash
date -j -f "%Y-%m-%d" "YYYY-MM-DD" "+%B/%d/%Y"
```

## Step 6 — Open and print

```bash
open -a TextEdit "$FILE"
```

TextEdit does not auto-reload a window that's already open on this path when the file changes on disk underneath it. If a prior run already opened this same filename, `open` will surface the stale window instead of the new content — always use a freshly timestamped filename per run (Step 5) so this can't happen, and if you ever reuse a path, tell the user to close and reopen the window rather than trusting what's already on screen.

Then print the full contents of the file inline in the response, and always state the file's full absolute path (e.g. `/private/tmp/daily-summary-range-<timestamp>.md`) at the end of the response — never omit this.

## Example output

```
July/01/2026
Added prefetching of the For You feed during the app splash screen and onboarding flow so the feed feels instant when users land on it.
The change shipped the following day, with the work having been in progress across the surrounding days.
---------------------------------------------------------------
July/02/2026
Shipped prefetching of the For You feed during the app splash screen and onboarding so the feed loads instantly when users arrive.
Improved first-time and returning users no longer see a loading state when they hit the main feed for the first time.
---------------------------------------------------------------
July/03/2026
Product images across the cart and main feed are now loaded ahead of time, making browsing feel faster and more fluid.
Unified the address entry form into a single shared component used across all checkout and address-management screens.
```

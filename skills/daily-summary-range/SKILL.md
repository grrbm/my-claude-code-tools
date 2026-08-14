---
name: daily-summary-range
description: Generate a plain-English daily work summary for every weekday across a date range (max 30 days) — one two-sentence entry per working day, no gaps, weekends skipped, days without direct evidence inferred from the nearest adjacent day — separated by dashed lines, written to a uniquely timestamped file. Optionally also writes the two per-day sentences into a Google Sheets timesheet, one sentence per shift-row, aligned against that sheet's own date column — in which case the date range is inferred from the sheet instead of asked. Use when the user asks for a summary "from X to Y", a "range" of days, or wants the daily-summary format repeated over multiple days. Do NOT trigger for a single day (use daily-summary) or for a calendar week (use weekly-report).
allowed-tools: Bash(git *), Bash(gh *), Bash(jq *), Bash(python3 *), Bash(printf *), Bash(date *), Bash(mkdir *), Bash(open *), Read
---

Generate a per-day plain-English work summary for every day in a date range, formatted as one two-sentence entry per day, separated by dashed lines, all written to a single timestamped file. Optionally, also push the two per-day sentences into a Google Sheets timesheet, one per matching shift-row.

## Step 1 — Determine the date range

The invocation may already specify **either** of two things — a plain start/end date, **or** a Google Sheets destination (a subsheet/tab name like `August 2026`, plus a single-column cell range like `E2:E21`, also written as `E2 to E21` — treat `X to Y` as equivalent to `X:Y`). These are alternatives, not both-required: whichever one the invocation gives you, use it and skip straight to the matching branch below.

If the invocation gives you **neither**, ask exactly this (plain text, not a multi-choice prompt — this skill has no preset ranges like "last two weeks" or "month-to-date", so don't invent quick-reply shortcuts implying it does):

> What date range should this cover? Reply with either a start and end date (max 30 days), or a Google Sheets subsheet name and cell range to pull the dates from instead — e.g. `August 2026`, `E2:E21`.

Wait for the reply, then route it: a date pair goes to "No Sheets destination" below; a subsheet name + range goes to "Sheets destination given" below.

### Sheets destination given

- Both a subsheet name and a **single-column** cell range must be present. If only one of the two is given (from the initial invocation or from the reply above), ask the user for the missing piece before proceeding — don't guess a range or a tab name.
- Do **not** ask the user for a start/end date. The destination sheet is a timesheet: column A holds one date per row (format `Weekday, Month D, YYYY`), typically with each weekday's date repeated once per shift-row (e.g. a morning shift and an evening shift). The date range is inferred by reading column A over the same row span as the given range (e.g. if the range is `E2:E21`, read `A2:A21`) — see the read snippet in Step 7, first block. Run it now, before Step 2.
- The earliest date found is the start date, the latest is the end date. Validate: the derived range (inclusive) must not exceed 30 days — if it does, tell the user and stop; do not silently truncate.
- Keep the parsed column-A read (dates in row order) — Step 7 needs it again to align each sentence to the correct row. Re-reading it there is cheap and keeps the steps independent.

### No Sheets destination

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

If a subsheet name and cell range were captured in Step 1, continue to Step 7. Otherwise you're done.

## Step 7 — Optional: write to Google Sheets

Only run this step if Step 1 captured both a subsheet name and a single-column cell range. Skip it entirely otherwise.

The destination is a timesheet, not a plain log: column A holds one date per row, usually with each weekday's date repeated once per shift-row. So sentences don't get blind-filled top to bottom — each of a day's two sentences is placed on the row where that day's Nth shift actually lives (sentence 1 → that day's first occurrence in column A, sentence 2 → its second occurrence), read fresh from the sheet so the write can't drift out of sync with the real row layout even if it isn't a strict two-rows-per-day pattern. Credentials come from the service account defined in `.claude/.env` (`SERVICE_ACCOUNT_*` vars); the target spreadsheet is `DESTINATION_SPREADSHEET_ID` from the same file (may hold a raw spreadsheet ID or a full URL — the scripts below handle either). No extra packages are available (no `google-auth`, `requests`, or `pyjwt`), so both scripts build and sign the OAuth JWT themselves by shelling out to `openssl` for the RSA-SHA256 signature, then talk to the Google OAuth and Sheets REST APIs directly via `urllib` — all from inside the single already-allowed `python3` invocation, so no new tool permissions are needed.

### Read snippet — column A over the range's row span (used in Step 1, and again here)

```bash
python3 - "$SHEET_NAME" "$CELL_RANGE" <<'PYEOF'
import sys, os, re, json, time, base64, tempfile, subprocess
import urllib.request, urllib.parse, urllib.error
from datetime import datetime

sheet_name, cell_range = sys.argv[1], sys.argv[2].replace(" to ", ":").replace(" To ", ":").strip()
rm = re.match(r"^[A-Za-z]+(\d+):[A-Za-z]+(\d+)$", cell_range)
if not rm:
    sys.exit(f"ERROR: expected a single-column range like 'E2:E21', got '{cell_range}'")
r1, r2 = rm.groups()

ENV_PATH = "/Users/guilhermereis/Desktop/clones/shopit-monorepo/.claude/.env"

def load_env(path):
    env = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                val = val[1:-1]
            env[key] = val.replace("\\n", "\n")
    return env

env = load_env(ENV_PATH)
client_email = env["SERVICE_ACCOUNT_CLIENT_EMAIL"]
private_key = env["SERVICE_ACCOUNT_PRIVATE_KEY"]
token_uri = env.get("SERVICE_ACCOUNT_TOKEN_URI", "https://oauth2.googleapis.com/token")
raw_dest = env["DESTINATION_SPREADSHEET_ID"]
m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", raw_dest)
spreadsheet_id = m.group(1) if m else raw_dest.strip()
safe_sheet = sheet_name.replace("'", "''")
a1_range = f"'{safe_sheet}'!A{r1}:A{r2}"

def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

now = int(time.time())
header = {"alg": "RS256", "typ": "JWT"}
claims = {"iss": client_email, "scope": "https://www.googleapis.com/auth/spreadsheets.readonly",
          "aud": token_uri, "iat": now, "exp": now + 3600}
signing_input = b64url(json.dumps(header, separators=(",", ":")).encode()) + "." + \
                b64url(json.dumps(claims, separators=(",", ":")).encode())
with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as kf:
    kf.write(private_key)
    key_path = kf.name
os.chmod(key_path, 0o600)
try:
    proc = subprocess.run(["openssl", "dgst", "-sha256", "-sign", key_path],
                           input=signing_input.encode(), capture_output=True, check=True)
finally:
    os.unlink(key_path)
jwt = f"{signing_input}.{b64url(proc.stdout)}"

token_req = urllib.request.Request(
    token_uri,
    data=urllib.parse.urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": jwt,
    }).encode(), method="POST",
)
try:
    with urllib.request.urlopen(token_req) as resp:
        access_token = json.loads(resp.read())["access_token"]
except urllib.error.HTTPError as e:
    sys.exit(f"TOKEN_ERROR: {e.read().decode()}")

url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{urllib.parse.quote(a1_range, safe='')}"
req = urllib.request.Request(url, method="GET", headers={"Authorization": f"Bearer {access_token}"})
try:
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
except urllib.error.HTTPError as e:
    sys.exit(f"SHEETS_ERROR: {e.read().decode()}")

dates = []
for row in result.get("values", []):
    if not row or not row[0].strip():
        continue
    raw = row[0].strip()
    d = None
    for fmt in ("%A, %B %d, %Y", "%B %d, %Y", "%Y-%m-%d"):
        try:
            d = datetime.strptime(raw, fmt)
            break
        except ValueError:
            continue
    if d is None:
        sys.exit(f"ERROR: could not parse date '{raw}' in column A")
    dates.append(d)

if not dates:
    sys.exit(f"ERROR: no dates found in '{a1_range}' — is the range right?")

start, end = min(dates), max(dates)
span_days = (end - start).days + 1
print(f"START_DATE={start.strftime('%Y-%m-%d')}")
print(f"END_DATE={end.strftime('%Y-%m-%d')}")
print(f"SPAN_DAYS={span_days}")
if span_days > 30:
    sys.exit(f"ERROR: derived range is {span_days} days, exceeding the 30-day max.")
PYEOF
```

In Step 1, run this to get `START_DATE`/`END_DATE` for Step 2 (and stop if it errors). No further action needed there.

### Write — align sentences to the correct shift-rows and push them

```bash
python3 - "$SHEET_NAME" "$CELL_RANGE" "$FILE" <<'PYEOF'
import sys, os, re, json, time, base64, tempfile, subprocess
import urllib.request, urllib.parse, urllib.error
from datetime import datetime

sheet_name, cell_range, file_path = sys.argv[1], sys.argv[2], sys.argv[3]
cell_range = cell_range.replace(" to ", ":").replace(" To ", ":").strip()
rm = re.match(r"^([A-Za-z]+)(\d+):([A-Za-z]+)(\d+)$", cell_range)
if not rm or rm.group(1).upper() != rm.group(3).upper():
    sys.exit(f"ERROR: Step 7 needs a single-column range like 'E2:E21', got '{cell_range}'")
col, r1, r2 = rm.group(1), int(rm.group(2)), int(rm.group(4))
n_rows = r2 - r1 + 1

ENV_PATH = "/Users/guilhermereis/Desktop/clones/shopit-monorepo/.claude/.env"

def load_env(path):
    env = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                val = val[1:-1]
            env[key] = val.replace("\\n", "\n")
    return env

env = load_env(ENV_PATH)
client_email = env["SERVICE_ACCOUNT_CLIENT_EMAIL"]
private_key = env["SERVICE_ACCOUNT_PRIVATE_KEY"]
token_uri = env.get("SERVICE_ACCOUNT_TOKEN_URI", "https://oauth2.googleapis.com/token")
raw_dest = env["DESTINATION_SPREADSHEET_ID"]
m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", raw_dest)
spreadsheet_id = m.group(1) if m else raw_dest.strip()
safe_sheet = sheet_name.replace("'", "''")

def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def get_access_token(scope):
    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    claims = {"iss": client_email, "scope": scope, "aud": token_uri, "iat": now, "exp": now + 3600}
    signing_input = b64url(json.dumps(header, separators=(",", ":")).encode()) + "." + \
                    b64url(json.dumps(claims, separators=(",", ":")).encode())
    with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as kf:
        kf.write(private_key)
        key_path = kf.name
    os.chmod(key_path, 0o600)
    try:
        proc = subprocess.run(["openssl", "dgst", "-sha256", "-sign", key_path],
                               input=signing_input.encode(), capture_output=True, check=True)
    finally:
        os.unlink(key_path)
    jwt = f"{signing_input}.{b64url(proc.stdout)}"
    req = urllib.request.Request(
        token_uri,
        data=urllib.parse.urlencode({
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": jwt,
        }).encode(), method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())["access_token"]
    except urllib.error.HTTPError as e:
        sys.exit(f"TOKEN_ERROR: {e.read().decode()}")

def sheets_call(a1_range, method, access_token, body=None, extra_query=""):
    url = (f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
           f"/values/{urllib.parse.quote(a1_range, safe='')}{extra_query}")
    req = urllib.request.Request(
        url, method=method, data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"SHEETS_ERROR: {e.read().decode()}")

# 1. Parse the deliverable file (Step 5) into {date: [sentence1, sentence2]}.
with open(file_path) as f:
    blocks_raw = f.read().split("-" * 63)
by_date = {}
for block in blocks_raw:
    block_lines = [l for l in block.strip("\n").split("\n") if l.strip()]
    if len(block_lines) < 3:
        continue
    date_str, s1, s2 = block_lines[0], block_lines[1], block_lines[2]
    d = datetime.strptime(date_str, "%B/%d/%Y").date()
    by_date[d] = [s1, s2]

# 2. Re-read column A for the same row span, and walk it in order to align each
#    day's Nth occurrence to its matching sentence (1st occurrence -> sentence 1, etc).
access_token = get_access_token("https://www.googleapis.com/auth/spreadsheets")
col_a = sheets_call(f"'{safe_sheet}'!A{r1}:A{r2}", "GET", access_token).get("values", [])

occurrence = {}
values = []
unmatched = 0
for i in range(n_rows):
    raw = col_a[i][0].strip() if i < len(col_a) and col_a[i] else ""
    cell_val = ""
    if raw:
        d = None
        for fmt in ("%A, %B %d, %Y", "%B %d, %Y", "%Y-%m-%d"):
            try:
                d = datetime.strptime(raw, fmt).date()
                break
            except ValueError:
                continue
        if d is not None and d in by_date:
            occurrence[d] = occurrence.get(d, 0) + 1
            idx = occurrence[d] - 1
            if idx < len(by_date[d]):
                cell_val = by_date[d][idx]
            else:
                unmatched += 1  # 3rd+ shift-row for a day that only has 2 sentences
        else:
            unmatched += 1  # row's date wasn't in the generated range (or unparsable)
    values.append([cell_val])

target_range = f"'{safe_sheet}'!{col}{r1}:{col}{r2}"
result = sheets_call(target_range, "PUT", access_token, body={"values": values}, extra_query="?valueInputOption=RAW")
print(f"OK wrote {result.get('updatedCells')} cells to {result.get('updatedRange')}")
if unmatched:
    print(f"WARNING: {unmatched} row(s) in the range had no matching date/sentence and were left blank.")
PYEOF
```

Fill in `$SHEET_NAME` and `$CELL_RANGE` from Step 1, and `$FILE` from Step 5.

If this prints `SHEETS_ERROR` with a 403/permission-denied response, the sheet has not been shared with the service account's `client_email` — tell the user to share the spreadsheet (Editor access) with that address and re-run. If it prints `TOKEN_ERROR`, the credentials in `.claude/.env` are invalid or expired. If it reports unmatched rows, say which rows/dates and why (a shift-row whose date fell outside the generated range, or a day with more than two shift-rows). Either way, the local file from Step 5/6 was already written successfully regardless of whether this step succeeds — report the Sheets outcome (success with the range written, an unmatched-rows warning, or the specific error) without implying the whole run failed.

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

---
name: report-with-videos
description: Produce a video QA report — a short screen recording of each test item actually being performed against the real running app — then open a draft PR with that report, videos uploaded and linked automatically. Use when asked to "record videos of the tests", "make a video report", "show a recording of each test", or when a written test-results table (a "Results" section with numbered items) already exists and needs a video per row. Sibling to report-with-pictures — same PR/upload mechanics, video instead of screenshots.
allowed-tools: Bash(agent-browser:*), Bash(npx agent-browser:*), Bash(gh *), Bash(git *), Bash(python3:*), Bash(ffprobe:*), Bash(ffmpeg:*)
---

# Skill: Report With Videos

Produces a video test/QA report — one short screen recording per test item, each showing the actual browser performing that exact test against the real running app — and lands it as a draft PR body with working video links, uploaded automatically. Same upload mechanics as `report-with-pictures` (verified to work for video too, see Step 4), but recording itself has sharp edges that skill doesn't have — read Step 1 before running anything.

## Step 0 — Get the test list

This skill records one video **per row** of an existing (or about-to-be-written) "Results" table — the same numbered list `report-with-pictures` would screenshot. If the user hasn't given you one, derive it the same way that skill would (what was built/tested this session). Number and name videos to match: `1-<slug>.webm`, `2-<slug>.webm`, matching the table row order — the upload step relies on this ordering.

## Step 1 — Record each video (read this fully before starting)

Reuse a running dev server the same way `report-with-pictures` does (`lsof -iTCP:<port> -sTCP:LISTEN`, don't launch a duplicate). For each test item:

```bash
agent-browser open <url>              # navigate FIRST
agent-browser wait --load networkidle
agent-browser wait 1000               # let it fully settle
agent-browser record start <N>-<slug>.webm
agent-browser wait 500
agent-browser snapshot -i             # get FRESH refs — see the two gotchas below
# ... perform the actual test steps ...
agent-browser record stop
```

### Gotcha 1: `record start` forces an internal page reload

Confirmed by testing: starting a recording reloads the page to attach the capture pipeline. Two consequences:

- **Refs taken before `record start` go stale.** Always `snapshot -i` again *after* `record start`, not before — reusing pre-recording refs silently fills the wrong field (this happened: two form fields' values landed concatenated in one input because the second `fill` resolved to the same stale ref as the first).
- **Auth-gated pages can bounce to login.** If the target page has any client-side "redirect if not authenticated yet" check that races its own hydration (reads `loginToken` before it's finished loading from storage), the forced reload can retrigger that race and land you back on `/login` — even though you were already correctly authenticated a second earlier. This is a real interaction with the app's existing hydration timing, not an agent-browser bug, but you have to design around it:
  - **Prefer starting the recording *before* navigating to the sensitive page at all**, and do any needed login *inside* the same continuous recording — e.g. start on `/login`, log in, then navigate to the target page, all in one take. This sidesteps the race entirely because there's no second reload of an already-authenticated page.
  - If a take does bounce to login mid-recording, don't fight it — `record stop`, discard that take, and redo it starting one step earlier (from the login page) rather than trying to patch around the failure.
  - After the real login `click`, wait for the actual destination URL (`wait --url "**/<expected-path>"`), not just `--load networkidle` — a client-side "logged in, redirecting..." transition can outlast the network-idle signal.

### Gotcha 2: verify before you trust a recording

`record stop` can occasionally report success with zero real content (e.g. if a navigation raced the stop). After each stop:

```bash
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 <file>.webm
```

A near-zero or missing duration means redo it. For anything unexpectedly long, pull a frame or two from partway through and actually look at them before moving on:

```bash
ffmpeg -y -v error -ss <seconds> -i <file>.webm -frames:v 1 <frame>.png
```

Then read the frame image. Don't assume a long recording is "probably fine" — check.

### General recording tips (also in agent-browser's own video-recording reference)

- Add small `wait <ms>` pauses around key actions (fills, clicks) so the recording is legible to a human watching it back, not just technically correct.
- Descriptive, numbered filenames matching the report's row order — the upload step depends on this.

### Show the current URL in the recording

Headless Chrome captures page content only — there's no real browser chrome (no address bar) to show which URL is loaded. Confirmed working fix: inject a small fixed-position overlay showing `location.href` via `eval --stdin`, **after `record start`** (its reload would otherwise wipe it) and **after every subsequent full navigation** (a real `open`/`reload` wipes all page JS state, overlay included — confirmed by testing, it does not survive):

```bash
cat <<'EOF' | agent-browser eval --stdin
(function() {
  const ID = '__agent_browser_url_overlay__';
  window.__ensureUrlOverlay = function() {
    let el = document.getElementById(ID);
    if (!el) {
      el = document.createElement('div');
      el.id = ID;
      el.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:2147483647;background:rgba(0,0,0,0.8);color:#39FF14;font:13px/1.4 -apple-system,monospace;padding:5px 10px;pointer-events:none;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;';
      document.documentElement.appendChild(el);
    }
    el.textContent = location.href;
    return el.textContent;
  };
  window.__ensureUrlOverlay();
  const origPush = history.pushState;
  history.pushState = function() { origPush.apply(this, arguments); window.__ensureUrlOverlay(); };
  const origReplace = history.replaceState;
  history.replaceState = function() { origReplace.apply(this, arguments); window.__ensureUrlOverlay(); };
  window.addEventListener('popstate', window.__ensureUrlOverlay);
  window.__urlOverlayInterval = setInterval(window.__ensureUrlOverlay, 500);
  return "overlay installed: " + window.__ensureUrlOverlay();
})();
EOF
```

The `pushState`/`replaceState` patch and `popstate` listener keep it current across client-side (SPA) navigations within a take, since those don't reload the page and so don't wipe the injected script. A full `open`/`reload` mid-recording still needs a fresh re-injection of this same snippet afterward — verified: the overlay is simply gone after a real navigation, re-running the snippet is what brings it back, there's no way to make it survive a real page load.

`pointer-events:none` keeps it from ever intercepting a click meant for the page underneath. Use it whenever the video's destination matters to a viewer at a glance (most reports) — skip it only if the test item is a single page with no navigation, where it'd be static noise.

## Step 2 — Open the draft PR with placeholders

**Videos must NOT go inside a markdown table cell.** Confirmed by direct comparison on a real PR: GitHub only auto-renders an uploaded video as an inline `<video>` player when its link is a bare URL on its own paragraph line. The exact same link syntax (`[filename](url)`, or even just the bare URL) placed inside a table cell renders as plain text instead — no player, no thumbnail. This isn't about file format (`.webm` vs `.mp4`) or upload method (drag vs programmatic) — a manually-dropped video and a programmatically-uploaded one produced byte-identical markdown, and only the one sitting in its own paragraph embedded.

So: keep the "Results" table for the What/Result columns only (no Video column), then add a separate `## Videos` section below with one heading + one bare link per item:

```
## Results

| # | What | Result |
|---|---|---|
| 1 | ... | ✅ Pass |

## Videos

### 1. <what>

**[Attach video: 1-community-desktop-empty-state.webm here]**
```

The placeholder itself can live in its own paragraph even though it's not a real URL yet — just make sure Step 4's replacement keeps it on its own line too, not wrapped back into anything.

Create a branch + `reports/<topic>-video-qa-<date>.md` file with this content (placeholders included) if there's no code diff to attach to, `gh pr create --draft` targeting `testnew`. Keep the placeholder text on disk for Step 4.

## Step 3 — Find an authenticated Chrome profile

Identical to `report-with-pictures` Step 3 — `agent-browser profiles`, cross-reference against Chrome's `Local State` file for the actual account email, ask the user if ambiguous. Falls back to manual hand-off (open the videos folder, tell the user where it is) if no authenticated profile is available.

## Step 4 — Upload the videos and assemble the final report

This is the part that needed to be verified, not assumed — it was, end to end, and works:

```bash
export AGENT_BROWSER_SESSION="report-video-upload-$(date +%s)"
agent-browser --profile "<ProfileName>" open <PR_URL>
```

1. Edit the description via **"Show options" (⋯) → "Edit comment"** on your own comment (disambiguate from other comments — e.g. the Vercel bot's — by checking which "Show options" button sits under *your* username's heading).
2. Find the real hidden file input the same way as `report-with-pictures`: `fc-` + the textarea's own id (list `input[type="file"]` via `eval --stdin` rather than assuming the numeric id).
3. Upload **all videos in one call**:
   ```bash
   agent-browser upload "#fc-issue-<N>-body" 1-foo.webm 2-bar.webm 3-baz.webm
   ```
4. Upload inserts a plain markdown link — `[filename.webm](https://github.com/user-attachments/assets/<uuid>)`, same shape for `.webm`/`.mp4`/`.mov` alike. That's fine and expected; it's the *placement*, not this syntax, that determines whether it renders as a player (see Step 2).
5. Read the textarea value back and extract URLs in upload order, same regex as the image skill: `https://github.com/user-attachments/assets/[a-f0-9-]*`.
6. Replace each placeholder with the **bare URL alone on its own line** — do not wrap it in `[label](url)` link syntax and do not put it back inside a table. A bare `https://github.com/user-attachments/assets/<uuid>` on its own paragraph is what actually triggers GitHub's inline player; a markdown link with custom label text may not (untested whether custom-labeled-but-still-standalone links embed too — bare URL is the confirmed-working form, use that).
7. Write the final content back via the native `HTMLTextAreaElement` value setter + a dispatched `input` event — **never `fill <ref> --stdin`**, which isn't a real flag and will type the literal string into the field. See `report-with-pictures` for the exact snippet; it's identical here.
8. Verify before saving: zero `[Attach` occurrences, zero `--stdin` occurrences, expected `user-attachments` count.
9. Click **"Update comment"**, then screenshot the saved result and confirm every video actually shows as a player with controls and a nonzero duration, not a bare filename link — that's the concrete pass/fail signal, not just "the URL is present somewhere."

## Step 5 — Hand back the link

Give the user the PR URL as a plain link — don't auto-open it.

## Notes

- Write the report from what you actually recorded, including anything that went wrong while recording (a hydration race, a flaky retry) as its own finding — that's real signal about the app, not just meta-commentary about the tooling.
- A real, authenticated Chrome profile is a real credentialed session — same care as `report-with-pictures`: don't navigate it anywhere beyond the PR you're editing.
- If a target page requires login and the app's session doesn't survive `record start`'s reload reliably, that's worth surfacing as its own report finding (see Gotcha 1) — it's a real characteristic of the app, discovered by actually trying to record it, not something to silently work around and never mention.

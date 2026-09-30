---
name: post-screenshots-to-pr
description: Given a plain-English description of what to capture and a target GitHub PR, take the screenshot(s) and embed them in that PR's description — uploaded and rendering inline, no manual drag-and-drop. Use when asked to "screenshot X and put it in the PR", "add a screenshot of Y to PR #N's description", "attach this to the PR body", or "post screenshots to the PR". Pass the `video` flag with one or more local video file paths instead of a capture description to post those videos into the PR description instead of screenshots, each with a generated title and description. For a full written QA report + a new draft PR, use report-with-pictures instead; this skill only edits an existing PR's description. Composes the agent-browser skill for the upload only.
argument-hint: video: <video-path-1> [<video-path-2> ...] [<pr-url-or-number>] | <what to screenshot> [<pr-url-or-number>]
allowed-tools: Bash(agent-browser:*), Bash(npx agent-browser:*), Bash(gh *), Bash(git *), Bash(python3:*), Bash(xcrun *), Bash(sips *), Bash(ffprobe *), Bash(ffmpeg *), Read
---

> **Headful simulator only.** Never drive, screenshot or record a headless simulator. On Xcode 27 the simulator
> window is hosted by **DeviceHub** (`/Applications/Xcode.app/Contents/Applications/DeviceHub.app`, bundle id
> `com.apple.dt.Devices`); there is no `Simulator.app` any more. Before touching the device, make sure it is running:
> `pgrep -x DeviceHub || open -b com.apple.dt.Devices` (older Xcode: `open -a Simulator`), and that the iPhone 16e is
> booted. `bun run ios` (`expo run:ios`) also opens it. If the window host cannot be opened, **stop and tell the
> user**; do not continue headless. (Headless also hides the QWERTY keyboard until text is typed, which makes
> keyboard checks and recordings misleading.)

# Skill: Post Screenshots To PR

Takes a description of what the user wants a screenshot of, captures it, and writes it into an
existing PR's **description** (not a comment), image uploaded and rendering. With the `video` flag
and one or more local video paths instead, it posts those videos into the same description, each
with a generated title and description, rendering as inline players instead of images.

## The one hard constraint

GitHub has **no API** to upload an image to a PR body. The only thing that can mint a
`https://github.com/user-attachments/assets/<uuid>` URL is a real, authenticated browser session
POSTing to the markdown editor's hidden `<input type="file">`. `agent-browser` driving a logged-in
Chrome does that.

**But the browser is used ONLY to mint that URL.** Everything else — reading the current body,
assembling the new body, saving it — goes through `gh`. Do **not** read the body back out of the
browser textarea and do **not** type the new body into it. That path corrupted PR #572 once:
`agent-browser eval` JSON-encodes its own return value, so `eval("JSON.stringify(ta.value)")` comes
back **double-encoded**, and one decode leaves literal `\n` and wrapping quotes in the text.

## Video mode is a different asset shape, not just a different Step 2

When the `video` flag is supplied, the whole flow is the same (resolve inputs → get the current
body via `gh` → get an authenticated browser session → upload → assemble → cancel-and-`gh pr edit`
→ verify), but two things genuinely differ, confirmed working end to end by `report-with-videos`
(this skill's sibling — same upload mechanics, read there for the original verification):

- **Upload inserts a markdown link for video, not `![]()`** — `[filename.mp4](https://github.com/user-attachments/assets/<uuid>)`, same shape for `.mp4`/`.mov`/`.webm`.
- **GitHub only renders it as an inline `<video>` player when that URL sits bare, alone, on its
  own paragraph line.** The exact same link placed inside anything else — a table cell, wrapped in
  `[label](url)`, wrapped in an `<img>` or `<video>` tag — renders as plain text/a dead link
  instead. So Step 6's video branch replaces the whole uploaded link with the bare URL alone, on
  its own line under a heading; it does **not** reuse the `<img width=N>` sizing trick Step 6 uses
  for images, because that trick doesn't apply here — a video attachment gives you no equivalent
  sizing control, and wrapping it in `<img>` breaks the embed instead of resizing it.

---

## Step 0 — Resolve inputs

- **Video mode check first**: does the input start with the literal token `video:` (or does the
  user's request plainly hand over existing video file(s) to post, e.g. "post this video to PR
  #N", "add these two recordings to the PR description")? If so this is video mode — the rest of
  this step still applies (target PR resolution, `unset GITHUB_TOKEN`), but skip straight to Step
  2's video branch instead of the screenshot branch; there is nothing to capture.
  - Collect every path after `video:` up to the first argument that isn't an existing local file
    (that remaining argument, if any, is the target PR). Reject and ask the user to fix the path if
    any given file doesn't exist — don't silently skip it.
  - Each file must actually be a video `ffprobe` can read (`ffprobe -v error -show_entries
    format=duration -of default=noprint_wrappers=1:nokey=1 <path>` succeeds with a nonzero
    duration). A file that fails this is not silently treated as an image — stop and tell the user.
- **What to capture** (non-video mode only): the user's description (e.g. "the phone-only auth
  sheet", "the empty cart"). If it names a screen that isn't currently on screen, navigation is out
  of scope — ask the user to get the app there, or hand off to `screenshot-screen` (iOS simulator)
  to navigate + capture, then resume at Step 2 with its PNG.
- **Target PR**: URL or number if given; else the PR for the current branch
  (`gh pr view --json number,url,headRefName`). Confirm with the user if the branch has no PR.
- `unset GITHUB_TOKEN` before every `gh` call (a PAT in env overrides the keyring OAuth token and
  404s on private repos).

## Step 1 — Capture the current body via `gh` (NOT the browser)

```bash
gh pr view <N> --repo <owner>/<repo> --json body -q .body > /tmp/psp-body-original.md
```

This is the canonical, clean source. Keep it untouched; Step 6 builds the new body from this file.

## Step 2 — Capture the screenshot(s), or gather the given video(s)

**Image mode:** default source in a mobile repo is the booted **iOS simulator**:

```bash
xcrun simctl io booted screenshot /tmp/psp-1.png
```

Save each final image with **descriptive, numbered names in display order**:
`1-auth-sheet-phone-only.png`, `2-cart-empty.png`, … — the upload step derives URLs from upload
order, so this ordering is mechanical.

`Read` each PNG and write a one-line **factual** alt/caption (what is on screen). No editorializing.
If the user wants the files too, `SendUserFile` them.

**Video mode:** nothing to capture — the user already gave you the file(s) in Step 0. Copy or
symlink each into **descriptive, numbered names in display order** the same way (`1-checkout-happy-
path.mp4`, `2-error-state.mp4`, …), matching the order the user gave them in unless they said
otherwise. For each video, before writing anything:

```bash
DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 1-foo.mp4)
ffmpeg -y -v error -ss "$(python3 -c "print(float('$DUR')/2)")" -i 1-foo.mp4 -frames:v 1 /tmp/psp-video-1-frame.png
```

`Read` that middle frame — actually look at what the video shows, don't title it from the filename
alone. Then write, per video, unlike the factual-only image captions: a short **title** (a few
words, e.g. "Checkout completes with a saved card") and a one-to-two-sentence **description** of
what happens in it, worth an actual reader's few seconds — this is the "nice titles and
description" the video path is for. Round `$DUR` to a sensible unit (e.g. "0:14") if you want to
mention length; it's a nice-to-have, not required. If the user already told you what a video shows,
use their words as the source of truth over your own read of one frame.

## Step 3 — Get an authenticated GitHub browser session

`agent-browser` launches a **fresh, empty Chromium profile** by default — not your everyday Chrome,
no logins. A private repo then renders as "Page not found". Modern Chrome (**136+**, so anything
current) **ignores `--remote-debugging-port` on the default profile** — a deliberate
anti-cookie-theft mitigation — so `--auto-connect` / `state save` against your real running Chrome
**do not work** and no restart changes that. The two paths that do:

| Path | Touches your Chrome? | Setup | Repeatable silently? |
|---|---|---|---|
| **Dedicated profile** | never | one-time GitHub login in a visible window (~1 min + 2FA) | ✅ fully headless after |
| **Quit-Chrome + real binary** | quits it ~15s per run | none | n/a |

**Dedicated profile (preferred):**
```bash
mkdir -p ~/.agent-browser-profiles
# First time only — visible window, user signs in to github.com once:
agent-browser --profile ~/.agent-browser-profiles/github --headed open https://github.com/login
# Every run after (headless, silent):
agent-browser --profile ~/.agent-browser-profiles/github open "<PR_URL>"
```

**Quit-Chrome fallback** (Chrome ≥129 app-bound cookie encryption means agent-browser's bundled
Chrome can't decrypt your real profile's cookies — must use the real Chrome binary, and it must not
be already running):
```bash
osascript -e 'tell application "Google Chrome" to quit'    # clean quit; tabs restore later
# poll until the process is gone, then:
agent-browser close --all
agent-browser --executable-path "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --profile "Default" open "https://github.com/settings/profile"
```
After the run: `agent-browser close --all` then `open -a "Google Chrome"`.

**Never quit the user's Chrome without asking.** Present both paths and let them pick. Confirm the
GitHub-authed profile has write access to the target repo (Chrome's
`~/Library/Application Support/Google/Chrome/Local State` → `profile.info_cache` maps profile dirs
to emails). Verify login after opening:
```bash
agent-browser eval --stdin <<'EOF'
document.querySelector('meta[name="user-login"]')?.content || null
EOF
```
Expect the user's GitHub login, not `null`.

Gotcha: `--profile` / `--executable-path` are **ignored if an agent-browser daemon is already
running** ("⚠ --profile ignored: daemon already running"). `agent-browser close --all` first.

## Step 4 — Open the description editor and find the file input

```bash
export AGENT_BROWSER_SESSION="psp-$(date +%s)"
agent-browser open "<PR_URL>"
agent-browser wait --load networkidle
agent-browser snapshot -i -c
```

- The PR description is the **first comment, by the PR author**. Its `button "Show options"` sits
  right after `heading "<author> commented …"` and before the first body heading in the snapshot.
  Do **not** pick a bot comment's "Show options" (Vercel/Danger), and do **not** use
  `button "Edit title"`.
- `agent-browser click @e<N>` on that button → then `click` the `menuitem "Edit comment"`.
- Enumerate inputs (ids are per-issue — never hardcode the number):
  ```bash
  agent-browser eval --stdin <<'EOF'
  JSON.stringify({
    textareas:[...document.querySelectorAll('textarea')].map(t=>({id:t.id,name:t.name})),
    fileInputs:[...document.querySelectorAll('input[type=file]')].map(i=>i.id)
  })
  EOF
  ```
  Description textarea: `issue-<N>-body` (name `pull_request[body]`). Its file input:
  `fc-issue-<N>-body` (same id, `fc-` prefix).

## Step 5 — Upload the images or videos (this is all the browser is for)

```bash
agent-browser upload "#fc-issue-<N>-body" 1-foo.png 2-bar.png     # all in one call
```

Each image upload fires an immediate POST and inserts
`![](https://github.com/user-attachments/assets/<uuid>)` into the textarea. **The asset is minted
on GitHub's CDN the moment it uploads — it persists even if you never save the comment.** That is
why Step 7 can cancel the editor and still use the URLs.

**Video mode:** the same `agent-browser upload` call works for `.mp4`/`.mov`/`.webm` files — pass
all of them in one call the same way. The only differences: the inserted text is a markdown **link**
(`[1-foo.mp4](https://github.com/user-attachments/assets/<uuid>)`), not `![]()`, and the upload
itself is slower and size-dependent, so give the poll below more headroom (start at `seq 1 90` with
a 2s sleep instead of 30×1s) rather than raising `<IMAGE_COUNT>`'s threshold early and missing a
still-uploading file.

Poll for the URLs, extracting **only the asset URLs** (ASCII, no newlines — safe to read back):
```bash
for i in $(seq 1 30); do
  URLS=$(agent-browser eval --stdin <<'EOF'
(document.getElementById('issue-<N>-body').value.match(/https:\/\/github\.com\/user-attachments\/assets\/[a-f0-9-]+/g)||[]).join('\n')
EOF
)
  n=$(printf '%s\n' "$URLS" | grep -c .)
  [ "$n" -ge <IMAGE_OR_VIDEO_COUNT> ] && break
  sleep 1
done
printf '%s\n' "$URLS"    # one asset URL per line, in upload order
```
`agent-browser eval` wraps its output in one JSON layer, so `URLS` here is a quoted string with
`\n` escapes — pipe it through `python3 -c 'import json,sys;print(json.loads(sys.stdin.read()))'`
if you need it literal, or just `grep -o` the asset-URL regex again. Either way: only ever pull the
**URLs** out of the browser, never the whole body.

## Step 6 — Assemble the new body from `/tmp/psp-body-original.md` (in Python)

**Image mode:** use an **HTML `<img>` tag with an explicit `width`**, not `![alt](url)` markdown —
bare markdown renders a phone screenshot (e.g. 1170×2532) at full column width, which is enormous
and pushes the rest of the description off-screen. `<img width=N>` still links to the full-size
image on click.

Get each image's real pixel size with `sips` (always on macOS) and pick a display width by
orientation:

```bash
for f in /tmp/psp-*.png; do
  read -r W H < <(sips -g pixelWidth -g pixelHeight "$f" | awk '/pixelWidth/{w=$2}/pixelHeight/{h=$2}END{print w, h}')
  echo "$f $W $H"
done > /tmp/psp-dims.txt
```

```bash
python3 - <<'PY'
import json
orig = open("/tmp/psp-body-original.md").read().rstrip("\n")
urls = [u for u in open("/tmp/psp-urls.txt").read().split() if u.startswith("https://")]
caps = json.load(open("/tmp/psp-captions.json"))            # ["factual alt 1", ...] in upload order
dims = {}
for line in open("/tmp/psp-dims.txt"):
    p = line.split()
    if len(p) == 3: dims[p[0]] = (int(p[1]), int(p[2]))
files = sorted(dims)                                        # same numbered order as upload

def display_width(w, h):
    if h > w:            # portrait — phone screenshot
        return 300
    return min(w, 760)   # landscape / desktop — cap column width, never upscale

section = "\n\n---\n\n## Screenshots\n"
for f, u, c in zip(files, urls, caps):
    w, h = dims[f]
    section += f'\n### {c}\n\n<img src="{u}" alt="{c}" width="{display_width(w, h)}">\n'
# If the caller pre-placed "**[Attach: N-name.png here]**" markers, replace those with the same
# <img ...> lines instead of appending a new section.
open("/tmp/psp-body-new.md", "w").write(orig + section)
print(open("/tmp/psp-body-new.md").read()[-700:])
PY
```

Sanity-check the file: first char is not `"`, `grep -c '\\n'` is 0 (no literal backslash-n),
`## ` heading count matches expectation, every asset URL appears inside a `<img ... width=...>` tag.

**Video mode:** do **not** reuse the `<img>` wrapper above — per the "Video mode is a different
asset shape" note near the top, a video attachment only renders as a player when its URL is bare
and alone on its own paragraph line. Each entry is a heading, the description written in Step 2,
a blank line, then the bare URL alone:

```bash
python3 - <<'PY'
import json
orig = open("/tmp/psp-body-original.md").read().rstrip("\n")
urls = [u for u in open("/tmp/psp-urls.txt").read().split() if u.startswith("https://")]
videos = json.load(open("/tmp/psp-videos.json"))
# [{"title": "Checkout completes with a saved card", "description": "..."}, ...] in upload order

section = "\n\n---\n\n## Videos\n"
for v, u in zip(videos, urls):
    section += f"\n### {v['title']}\n\n{v['description']}\n\n{u}\n"
# If the caller pre-placed "**[Attach video: N-name.mp4 here]**" markers, replace each whole
# placeholder line with "{title heading}\n\n{description}\n\n{bare url}" instead of appending a
# new section — same rule as report-with-videos Step 2, keep the URL on its own line either way.
open("/tmp/psp-body-new.md", "w").write(orig + section)
print(open("/tmp/psp-body-new.md").read()[-700:])
PY
```

Sanity-check the file the same way, plus: every asset URL appears **bare** — not inside `[]()`,
not inside any HTML tag, and with a blank line both above and below it.

## Step 7 — Cancel the browser editor, then save via `gh`

```bash
agent-browser snapshot -i -c            # fresh ref for the Cancel button
agent-browser click @e<cancel-ref>      # discard the browser edit — nothing typed back through it
gh pr edit <N> --repo <owner>/<repo> --body-file /tmp/psp-body-new.md
```

`gh pr edit --body-file` is the only writer. No native-setter, no `fill --stdin`, no React-input
tricks — that whole class of bug is gone because the browser never writes the body.

## Step 8 — Verify

```bash
gh pr view <N> --repo <owner>/<repo> --json body -q .body | python3 -c "
import sys; b=sys.stdin.read()
assert not b.lstrip().startswith('\"'), 'body got JSON-wrapped'
assert b.count(chr(92)+'n')==0, 'literal backslash-n in body'
print('h2 headings:', b.count(chr(10)+'## '))
print('asset URLs:', b.count('user-attachments/assets/'))
"
agent-browser open "<PR_URL>"          # reload the rendered page
agent-browser eval --stdin <<'EOF'
JSON.stringify([...document.querySelectorAll('.markdown-body img')].map(i=>({alt:i.alt,ok:i.complete&&i.naturalWidth>0})))
EOF
agent-browser screenshot /tmp/psp-rendered.png
```
GitHub rewrites `user-attachments/assets/<uuid>` → `private-user-images.githubusercontent.com/…?jwt=…`
on render — expected. Pass = every `.markdown-body img` has `ok:true`. `Read` `/tmp/psp-rendered.png`
and actually look.

**Video mode:** check for rendered `<video>` elements instead — an `<img>` count of zero is expected
and not a failure here.
```bash
agent-browser eval --stdin <<'EOF'
JSON.stringify([...document.querySelectorAll('.markdown-body video')].map(v=>({src:v.currentSrc||v.src,readyState:v.readyState})))
EOF
```
Pass = one `<video>` per uploaded file, each with `readyState >= 1` (metadata loaded — a broken
embed stays at `0`). A video that rendered as a bare link/filename instead of a player means Step 6
left it wrapped in something or off its own line — go back and fix the markdown, don't re-upload.
`Read` `/tmp/psp-rendered.png` and actually look: a real player has a thumbnail and play controls,
a failed embed looks like plain link text.

## Step 9 — Clean up and report

- Quit-Chrome path was used → `agent-browser close --all` then `open -a "Google Chrome"`.
- Otherwise → `agent-browser close --all`.
- Give the user the PR URL as a plain link. **Do not auto-open it.** State that the images (or
  videos) are embedded and rendering, not just linked. In video mode, name each video's generated
  title so the user can tell at a glance whether it matches what they meant to post.

## Notes

- A real Chrome profile / dedicated-profile session is a live authenticated session as that person.
  Navigate it only to the PR being edited.
- Only ever edit the description. Never post a comment, change the title, or push.
- No authenticated session and the user won't set one up → `SendUserFile` the screenshots or videos,
  give the user the PR edit URL and the exact block you would have written (`<img ...>` for images,
  the heading/description/bare-URL shape for video), stop. Don't fabricate an upload.
- Leaving `--remote-debugging-port` open on a working (non-default) profile exposes full control of
  that browser to any local process — enable only for a run, drop it after. The dedicated-profile
  path doesn't use the port at all.
- **Never compress or re-encode a video before posting it — post it exactly as given, every time.**
  This isn't just about not doing it silently: don't do it at all, even if offering first. Compression
  has repeatedly turned out not to help here. If the upload fails because the file is too large for
  GitHub, say so plainly and ask the user how they want to proceed — trimming, a different host,
  whatever they pick — rather than reaching for `ffmpeg` yourself.

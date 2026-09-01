---
name: post-screenshots-to-pr
description: Given a plain-English description of what to capture and a target GitHub PR, take the screenshot(s) and embed them in that PR's description — uploaded and rendering inline, no manual drag-and-drop. Use when asked to "screenshot X and put it in the PR", "add a screenshot of Y to PR #N's description", "attach this to the PR body", or "post screenshots to the PR". For a full written QA report + a new draft PR, use report-with-pictures instead; this skill only edits an existing PR's description. Composes the agent-browser skill for the image upload only.
allowed-tools: Bash(agent-browser:*), Bash(npx agent-browser:*), Bash(gh *), Bash(git *), Bash(python3:*), Bash(xcrun *), Read
---

# Skill: Post Screenshots To PR

Takes a description of what the user wants a screenshot of, captures it, and writes it into an
existing PR's **description** (not a comment), image uploaded and rendering.

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

---

## Step 0 — Resolve inputs

- **What to capture**: the user's description (e.g. "the phone-only auth sheet", "the empty cart").
  If it names a screen that isn't currently on screen, navigation is out of scope — ask the user to
  get the app there, or hand off to `screenshot-screen` (iOS simulator) to navigate + capture, then
  resume at Step 2 with its PNG.
- **Target PR**: URL or number if given; else the PR for the current branch
  (`gh pr view --json number,url,headRefName`). Confirm with the user if the branch has no PR.
- `unset GITHUB_TOKEN` before every `gh` call (a PAT in env overrides the keyring OAuth token and
  404s on private repos).

## Step 1 — Capture the current body via `gh` (NOT the browser)

```bash
gh pr view <N> --repo <owner>/<repo> --json body -q .body > /tmp/psp-body-original.md
```

This is the canonical, clean source. Keep it untouched; Step 6 builds the new body from this file.

## Step 2 — Capture the screenshot(s)

Default source in a mobile repo is the booted **iOS simulator**:

```bash
xcrun simctl io booted screenshot /tmp/psp-1.png
```

Save each final image with **descriptive, numbered names in display order**:
`1-auth-sheet-phone-only.png`, `2-cart-empty.png`, … — the upload step derives URLs from upload
order, so this ordering is mechanical.

`Read` each PNG and write a one-line **factual** alt/caption (what is on screen). No editorializing.
If the user wants the files too, `SendUserFile` them.

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

## Step 5 — Upload the images (this is all the browser is for)

```bash
agent-browser upload "#fc-issue-<N>-body" 1-foo.png 2-bar.png     # all in one call
```

Each upload fires an immediate POST and inserts `![](https://github.com/user-attachments/assets/<uuid>)`
into the textarea. **The asset is minted on GitHub's CDN the moment it uploads — it persists even if
you never save the comment.** That is why Step 7 can cancel the editor and still use the URLs.

Poll for the URLs, extracting **only the asset URLs** (ASCII, no newlines — safe to read back):
```bash
for i in $(seq 1 30); do
  URLS=$(agent-browser eval --stdin <<'EOF'
(document.getElementById('issue-<N>-body').value.match(/https:\/\/github\.com\/user-attachments\/assets\/[a-f0-9-]+/g)||[]).join('\n')
EOF
)
  n=$(printf '%s\n' "$URLS" | grep -c .)
  [ "$n" -ge <IMAGE_COUNT> ] && break
  sleep 1
done
printf '%s\n' "$URLS"    # one asset URL per line, in upload order
```
`agent-browser eval` wraps its output in one JSON layer, so `URLS` here is a quoted string with
`\n` escapes — pipe it through `python3 -c 'import json,sys;print(json.loads(sys.stdin.read()))'`
if you need it literal, or just `grep -o` the asset-URL regex again. Either way: only ever pull the
**URLs** out of the browser, never the whole body.

## Step 6 — Assemble the new body from `/tmp/psp-body-original.md` (in Python)

Use an **HTML `<img>` tag with an explicit `width`**, not `![alt](url)` markdown — bare markdown
renders a phone screenshot (e.g. 1170×2532) at full column width, which is enormous and pushes the
rest of the description off-screen. `<img width=N>` still links to the full-size image on click.

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

## Step 9 — Clean up and report

- Quit-Chrome path was used → `agent-browser close --all` then `open -a "Google Chrome"`.
- Otherwise → `agent-browser close --all`.
- Give the user the PR URL as a plain link. **Do not auto-open it.** State that the images are
  embedded and rendering, not just linked.

## Notes

- A real Chrome profile / dedicated-profile session is a live authenticated session as that person.
  Navigate it only to the PR being edited.
- Only ever edit the description. Never post a comment, change the title, or push.
- No authenticated session and the user won't set one up → `SendUserFile` the screenshots, give the
  user the PR edit URL and the exact `![alt](path)` block, stop. Don't fabricate an upload.
- Leaving `--remote-debugging-port` open on a working (non-default) profile exposes full control of
  that browser to any local process — enable only for a run, drop it after. The dedicated-profile
  path doesn't use the port at all.

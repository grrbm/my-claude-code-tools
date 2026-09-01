---
name: post-screenshots-to-pr
description: Given a plain-English description of what to capture and a target GitHub PR, take the screenshot(s) and embed them directly in that PR's description — uploaded and rendering inline, no manual drag-and-drop. Use when asked to "screenshot X and put it in the PR", "add a screenshot of Y to PR #N's description", "attach this to the PR body", or "post screenshots to the PR". For a full written QA report + a new draft PR, use report-with-pictures instead; this skill only edits an existing PR's description. Composes the agent-browser skill for the upload.
allowed-tools: Bash(agent-browser:*), Bash(npx agent-browser:*), Bash(gh *), Bash(git *), Bash(python3:*), Bash(xcrun *), Read
---

# Skill: Post Screenshots To PR

Takes a description of what the user wants a screenshot of, captures it, and writes it into an
existing PR's **description** (not a comment) with the image uploaded and rendering — the same
result a human gets by dragging a file into GitHub's markdown editor.

GitHub has **no API** for uploading images to a PR body. The only mechanism is a real,
authenticated browser session POSTing to the hidden `<input type="file">` wired to the markdown
editor. `agent-browser` driving a logged-in Chrome does exactly that. This was verified working
end-to-end on 2026-09-01 (ShopIt PR #572).

---

## Step 0 — Resolve inputs

- **What to capture**: the user's description (e.g. "the phone-only auth sheet", "the empty cart",
  "the gift claim screen after claiming"). If it names a specific screen that isn't currently on
  screen, navigation is out of scope here — either ask the user to get the app to that screen, or
  (for the iOS simulator) hand off to the `screenshot-screen` skill to navigate + capture, then
  come back to Step 3 with its PNG.
- **Target PR**: a URL or number if given. Otherwise default to the PR for the current branch:
  `gh pr view --json number,url,headRefName`. Confirm with the user if there's no PR for the branch.
- Always `unset GITHUB_TOKEN` before any `gh` call (a PAT in the env overrides the keyring OAuth
  token and can 404 on private repos).

## Step 1 — Capture the screenshot(s)

Default source for this monorepo is the booted **iOS simulator**:

```bash
xcrun simctl io booted screenshot /tmp/shot.png
```

Save each final image into the harness scratchpad (or `~/Desktop/<project>-shots-<date>/` if the
user wants to keep them) with **descriptive, numbered filenames in the order they'll appear**:
`1-auth-sheet-phone-only.png`, `2-cart-empty.png`, … — the upload step re-derives URLs from upload
order, so this ordering is mechanical, not cosmetic.

Read each PNG back with the Read tool and write a one-line factual alt/caption for each (what is
actually on screen). Don't editorialize.

If the user also wants the files delivered to them, use `SendUserFile`.

## Step 2 — Get an authenticated GitHub browser session

`agent-browser` launches a **fresh, empty Chromium profile by default** — it is *not* your everyday
Chrome and has none of your logins. Plain headless will always load GitHub logged-out (a private
repo then renders as "Page not found"). Pick one of these, in order of preference:

1. **`--auto-connect` to your already-running Chrome** (nothing to quit, if it was started with a
   debug port):
   ```bash
   # one-time, in a terminal the user runs — restarts their Chrome with a debug port:
   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9222
   # then:
   agent-browser --auto-connect open "<PR_URL>"
   ```
   ⚠️ `--remote-debugging-port` exposes full control of that Chrome to any local process. Trusted
   machines only; close it when done.

2. **Persistent dedicated profile** — a Chrome user-data dir that is *not* your main one, logged in
   to GitHub once:
   ```bash
   agent-browser --profile ~/.agent-browser-profiles/github --headed open https://github.com/login
   # user logs in + 2FA once in the visible window; reused on every later run
   agent-browser --profile ~/.agent-browser-profiles/github open "<PR_URL>"
   ```

3. **Export cookies once, then load state** (lighter than #1 long-term):
   ```bash
   agent-browser --auto-connect state save ~/.agent-browser-profiles/github-auth.json
   agent-browser --state ~/.agent-browser-profiles/github-auth.json open "<PR_URL>"
   ```

4. **Fallback that worked 2026-09-01 — real Chrome binary, Chrome fully quit.** Chrome ≥129 on
   macOS uses **app-bound cookie encryption**: agent-browser's bundled Chrome-for-Testing binary
   *cannot* decrypt your real `Default` profile's cookies, so `--profile "Default"` alone yields a
   logged-out session. Pointing `--executable-path` at the real Chrome binary *can* decrypt them,
   but only if your everyday Chrome is not holding the profile lock:
   ```bash
   osascript -e 'tell application "Google Chrome" to quit'   # clean quit, session restorable
   # wait for the process to exit, then:
   agent-browser close --all
   agent-browser --executable-path "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
     --profile "Default" open "https://github.com/settings/profile"
   # verify: eval `document.querySelector('meta[name="user-login"]').content` is the expected login
   ```
   After the upload: `agent-browser close --all` then `open -a "Google Chrome"` so the user gets
   their browser back (tabs restore via "Continue where you left off").

**Never quit the user's Chrome without asking.** Present options 1–4 and let them choose.
Confirm which profile has GitHub write access to the target repo (Chrome's
`~/Library/Application Support/Google/Chrome/Local State` → `profile.info_cache` maps profile dirs
to account emails). Wrong profile → "Page not found" on a private repo, a cheap safe signal.

Gotcha: `--profile` / `--executable-path` are **ignored if an agent-browser daemon is already
running** ("⚠ --profile ignored: daemon already running"). Run `agent-browser close --all` first.

## Step 3 — Open the PR and the description editor

```bash
export AGENT_BROWSER_SESSION="psp-$(date +%s)"
agent-browser open "<PR_URL>"
agent-browser wait --load networkidle
agent-browser snapshot -i -c
```

- The PR description is the **first comment, authored by the PR author**. In the snapshot its
  `button "Show options"` sits right after the `heading "<author> commented …"` and before the
  first body heading. Do **not** grab a bot comment's "Show options" (Vercel/Danger/etc.), and do
  **not** use `button "Edit title"` (that's the title pencil).
- `agent-browser click @e<N>` on that "Show options" button → then `click` the `menuitem "Edit comment"`.

## Step 4 — Find the real hidden file input

After the editor opens, enumerate — don't hardcode the numeric id (it's per-issue):

```bash
agent-browser eval --stdin <<'EOF'
JSON.stringify({
  textareas: [...document.querySelectorAll('textarea')].map(t=>({id:t.id,name:t.name,len:t.value.length,vis:t.offsetParent!==null})),
  fileInputs: [...document.querySelectorAll('input[type=file]')].map(i=>({id:i.id,vis:i.offsetParent!==null}))
})
EOF
```

The description textarea is `issue-<N>-body` (name `pull_request[body]`); its file input is the
same id with an `fc-` prefix: `fc-issue-<N>-body`.

## Step 5 — Save the current body, then upload

```bash
# 1. save current body verbatim (rebuild from this, don't diff the live textarea later)
agent-browser eval --stdin <<'EOF' > /tmp/pr-body.json
JSON.stringify(document.getElementById('issue-<N>-body').value)
EOF
python3 -c "import json;open('/tmp/pr-body.md','w').write(json.load(open('/tmp/pr-body.json')))"

# 2. upload ALL images in one call
agent-browser upload "#fc-issue-<N>-body" 1-foo.png 2-bar.png

# 3. wait until the markdown resolves — poll the textarea value for user-attachments/assets/
```

Each upload inserts `![](https://github.com/user-attachments/assets/<uuid>)` at the cursor
(usually the top), not at any placeholder — expected, fixed next.

## Step 6 — Assemble the final body

Extract the uploaded URLs in upload order:

```bash
agent-browser eval --stdin <<'EOF'
JSON.stringify(document.getElementById('issue-<N>-body').value.match(/https:\/\/github\.com\/user-attachments\/assets\/[a-f0-9-]+/g))
EOF
```

Build the final body **in a script** (Python — the body is long and full of backticks/quotes):
take the saved `/tmp/pr-body.md` and either

- replace each `**[Attach: N-name.png here]**` placeholder the caller pre-placed with
  `![<caption>](<Nth URL>)`, or
- if there are no placeholders, append a new trailing section:
  ```
  \n\n---\n\n## Screenshots\n\n### <caption>\n\n![<factual alt>](<URL>)\n
  ```

## Step 7 — Write the body back (native setter, NOT `fill`)

`fill <ref> --stdin` is not a real flag — it types the literal string `--stdin` into the field.
GitHub's editor is a controlled React input, so a plain `.value =` reverts. Use the native setter
+ a dispatched `input` event:

```bash
python3 -c "import json;print(json.dumps(open('/tmp/pr-body-final.md').read()))" > /tmp/final.json
cat > /tmp/set.js <<JSEOF
(function(){
  var ta=document.getElementById("issue-<N>-body");
  var setter=Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,"value").set;
  setter.call(ta, $(cat /tmp/final.json));
  ta.dispatchEvent(new Event("input",{bubbles:true}));
  return JSON.stringify({len:ta.value.length,
    leftoverPlaceholder: ta.value.includes("[Attach"),
    stdinArtifact: ta.value.includes("--stdin"),
    imgCount:(ta.value.match(/user-attachments\/assets\//g)||[]).length});
})();
JSEOF
cat /tmp/set.js | agent-browser eval --stdin
```

Verify: `leftoverPlaceholder:false`, `stdinArtifact:false`, `imgCount` == number of files uploaded.
Re-read `ta.value` once more to confirm it stuck (don't trust the a11y snapshot — it **truncates**
long textarea text and will look like your section is missing when it isn't).

## Step 8 — Save

The button label is **"Update comment"** (editing an existing description), not "Save". It's usually
below the fold:

```bash
agent-browser eval --stdin <<'EOF'
(function(){var b=[...document.querySelectorAll('button')].find(x=>x.textContent.trim()==='Update comment');b.scrollIntoView({block:'center'});return b.getBoundingClientRect().y})()
EOF
agent-browser snapshot -i -c        # get the fresh @ref for "Update comment"
agent-browser click @e<N>           # click by REF — `find role button click --name` reported success without submitting this session
```

## Step 9 — Verify it rendered

```bash
agent-browser eval --stdin <<'EOF'
JSON.stringify([...document.querySelectorAll('.markdown-body img')].map(i=>({src:i.currentSrc,alt:i.alt,w:i.naturalWidth,h:i.naturalHeight,ok:i.complete&&i.naturalWidth>0})))
EOF
agent-browser screenshot /tmp/pr-rendered.png
```

GitHub rewrites `user-attachments/assets/<uuid>` → `https://private-user-images.githubusercontent.com/…?jwt=…`
on render — that's expected. Pass condition: an `<img>` in `.markdown-body` with `ok:true`
(nonzero `naturalWidth`, `complete`). Read `/tmp/pr-rendered.png` and actually look at it.

## Step 10 — Clean up and report

- If Step 2 option 4 (quit Chrome) was used: `agent-browser close --all` then `open -a "Google Chrome"`.
- `agent-browser close --all` otherwise.
- Give the user the PR URL as a plain link. **Do not auto-open it.** State plainly that the images
  are embedded and rendering, not just linked.

## Notes

- A real Chrome profile / `--auto-connect` session is a live authenticated session as that person.
  Navigate it only to the PR being edited; don't touch anything else.
- Only edit the description. Never post a separate comment, never change the title, never push.
- If no authenticated session is available and the user won't set one up: fall back to a manual
  hand-off — `SendUserFile` the screenshots, give the user the PR edit URL and the exact
  `![alt](path)` markdown block, and stop. Don't fabricate an upload.

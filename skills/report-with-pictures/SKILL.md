---
name: report-with-pictures
description: Produce a visual QA report (screenshots + written findings) for what was just built or changed, then open a draft PR with that report — including the screenshots themselves, uploaded and embedded automatically. Use when asked to "screenshot everything we built", "make a report with pictures", "document this visually", or "create a draft PR with a report and screenshots". Composes the agent-browser skill for both the screenshots and the upload.
allowed-tools: Bash(agent-browser:*), Bash(npx agent-browser:*), Bash(gh *), Bash(git *), Bash(python3:*)
---

# Skill: Report With Pictures

Produces a visual test/QA report — real screenshots of the actual running app plus written notes on what was verified — and lands it as a draft PR body, **images embedded and rendering**, no manual drag-and-drop required.

Claude has no *API* for uploading images to GitHub — but a real, authenticated browser session does, because that's exactly what a human dragging a file into GitHub's comment box triggers under the hood: a POST to a hidden `<input type="file">` wired to the markdown editor. `agent-browser` driving a logged-in Chrome profile can do the same thing directly. This was verified working end-to-end (see below) — prefer it over the manual hand-off path.

## Step 1 — Take the screenshots

Invoke the `agent-browser` skill (`Skill({skill: "agent-browser"})`) with a concrete brief: what was built this session, which pages/states are screenshotable, and where dev servers already are (reuse a running one if `lsof -iTCP:<port> -sTCP:LISTEN` shows a live server serving the right app — don't launch a duplicate). Cover, for each screenshotable piece:

- The default/empty state
- A realistic filled/success state (submit real forms against a real backend when one is safely available — e.g. a staging DB, never production, and confirm with the user first if unsure which DB a running backend is pointed at)
- Both desktop and mobile viewports for anything user-facing
- Auth-gated pages: ask the user for test credentials if needed (never guess or reuse credentials from elsewhere in the transcript without confirming they're meant for this)

Save every screenshot to one clearly-named local directory (not the harness scratchpad, which is ephemeral) — e.g. `~/Desktop/<project>-report-<date>/`. Use descriptive, numbered filenames (`1-community-page-desktop.png`) matching the order they'll appear in the report — the upload step re-derives image URLs from upload order, so this ordering matters mechanically, not just for readability.

Also use `SendUserFile` to deliver the files to the user's client, so they have a copy regardless of what happens next.

## Step 2 — Open the draft PR with placeholder text

Write the report body with a placeholder at each spot a screenshot belongs — exactly this format, so Step 4's find/replace can match it:

```
**[Attach: 1-community-page-desktop.png here]**
```

Choose a PR title matching this repo's `create-pr` convention (`<type>(<scope>): <description>`, referencing a Linear issue if applicable) — usually `docs` type. If there's no code diff to attach the report to, create a small branch with a report markdown file (e.g. `reports/<topic>-<date>.md`, same content, placeholders included) so the PR has a valid diff, then `gh pr create --draft` from that branch targeting `testnew`. Keep a copy of the exact report text (with placeholders) on disk — Step 4 reads it back to build the final version.

## Step 3 — Find an authenticated Chrome profile

```bash
agent-browser profiles
```

Map profile directories to account emails (profile names alone are often generic like "Profile 4"):

```bash
python3 -c "
import json
with open('/Users/<user>/Library/Application Support/Google/Chrome/Local State') as f:
    data = json.load(f)
for key, info in data.get('profile', {}).get('info_cache', {}).items():
    print(key, '->', info.get('user_name'), '|', info.get('gaia_name'), '|', info.get('name'))
"
```

If it's not obvious which profile is logged into GitHub with write access to this repo, ask the user rather than guessing — trying the wrong profile just shows "Page not found" on a private repo, which is a cheap, safe way to confirm it's wrong.

If no profile is authenticated to the right GitHub account, fall back to the manual hand-off: open the screenshots folder (`open <directory>`), tell the user where it is and that the PR has placeholders, and stop there. Don't attempt to guess or fabricate an upload path.

## Step 4 — Upload the screenshots and assemble the final report

```bash
export AGENT_BROWSER_SESSION="report-upload-$(date +%s)"
agent-browser --profile "<ProfileName>" open <PR_URL>
```

1. Open the description's edit mode via its **"Show options" (⋯) menu → "Edit comment"** — not the "Edit title" pencil, and not `find role button click --name "Edit"` alone (it's ambiguous on a PR page; snapshot first and disambiguate).
2. Locate the real hidden file input. It shares the textarea's id with an `fc-` prefix (e.g. textarea `id="issue-5166052958-body"` pairs with file input `id="fc-issue-5166052958-body"`) — confirm by listing `input[type="file"]` via `eval --stdin` rather than assuming the numeric id, since it's per-issue:
   ```js
   Array.from(document.querySelectorAll('input[type="file"]')).map(i => ({id: i.id, visible: i.offsetParent !== null}))
   ```
3. Upload **all screenshots in one call** — `upload` accepts multiple file args:
   ```bash
   agent-browser upload "#fc-issue-<N>-body" 1-foo.png 2-bar.png 3-baz.png 4-qux.png
   ```
   Each upload inserts an `<img width=... height=... alt="..." src="https://github.com/user-attachments/assets/<uuid>">` tag at the current cursor position (typically the top), not at your placeholders — that's expected, fix it in the next step.
4. Read the textarea's value back and extract the uploaded URLs, in order:
   ```bash
   agent-browser get value @<ref-of-comment-body-textbox> | grep -o 'https://github.com/user-attachments/assets/[a-f0-9-]*'
   ```
   URLs come back in upload order, so the Nth URL corresponds to the Nth file you passed to `upload`.
5. Take your saved placeholder-report text (Step 2) and replace each `**[Attach: N-name.png here]**` with `![<description>](<Nth URL>)`, in a script (Python/Node — not by hand, the content is long and has backticks/quotes that break naive shell quoting).
6. **Write the final content back with the native setter + input event — never `fill <ref> --stdin`.** `fill` has no `--stdin` flag; passing it literally types the four characters `--stdin` into the field and destroys your content (this happened once — recover by rebuilding and re-setting, not by trying to patch around it). Instead, JSON-encode the final text and inject it via `eval --stdin`:
   ```bash
   python3 -c "import json; print(json.dumps(open('final-report.md').read()))" > /tmp/report.json
   cat > /tmp/set.js <<JSEOF
   (function() {
     const ta = document.getElementById("issue-<N>-body");
     const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
     setter.call(ta, $(cat /tmp/report.json));
     ta.dispatchEvent(new Event("input", { bubbles: true }));
     return ta.value.length;
   })();
   JSEOF
   cat /tmp/set.js | agent-browser eval --stdin
   ```
   The native-setter + dispatched `input` event is required because GitHub's editor is a controlled React input — a plain `.value = "..."` assignment updates the DOM but not the app's state, so it'd silently revert or fail to save.
7. Verify before saving: re-read the textarea value, confirm zero occurrences of `[Attach` and zero occurrences of `--stdin`, and confirm the expected image count (`grep -c user-attachments`).
8. Click the save button (its label is "Update comment" when editing an existing PR description, not "Save").
9. Screenshot the saved, rendered result and look at it — confirm all images actually render (not broken links) and are in the right order before calling this done.

## Step 5 — Hand back the link

Give the user the PR URL as a plain link in your reply — do not auto-open it in a browser, let them open it themselves. Confirm plainly that the images are already embedded and rendering, not just referenced.

## Notes

- If the user already told you what was tested/built (e.g. earlier in the same session), don't re-derive it — write the report from what you actually did, including any bugs found along the way (even ones fixed before this point) and any real backend/DB interactions, not just a list of pages visited.
- Treat this as a documentation artifact: don't editorialize beyond what was actually verified, and don't claim something was tested if it was only visually inspected.
- Using a real Chrome profile means a real, cookie-authenticated session as that person — treat it with the same care as any other credential-bearing action. Don't navigate it anywhere beyond the PR you're editing, and don't leave it logged into anything the user didn't already have open.

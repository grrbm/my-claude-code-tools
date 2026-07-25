---
name: format-pr-screenshots
description: Reformat and organize the "Screenshots or Video" section of a GitHub PR description — labeling each image/video, laying them out cleanly, and shrinking oversized dimensions — without touching any other part of the PR body. Use whenever asked to format PR screenshots, organize/clean up the screenshots or media section of a PR, add labels to PR images, or make a wall of unlabeled screenshots in a PR readable. Triggers on phrases like "format the PR screenshots", "organize screenshots on PR X", "clean up the media section of this PR", "label these PR images", "the screenshots section is a mess".
argument-hint: <pr-url>
allowed-tools: Bash(gh *), Bash(unset GITHUB_TOKEN && gh *), Bash(curl *), Bash(rm /private/tmp/pr-format-img-*.png), Read, Write(/private/tmp/pr-format-*.md)
---

Reformat the "Screenshots or Video" section of a PR description: $ARGUMENTS

This skill touches a *shared* PR body via `gh pr edit --body`, which replaces the entire
description text — there is no way to patch just one section server-side. That single fact
drives every safety rule below: get the full current body into hand before composing anything,
and reassemble the *whole* body (untouched sections + reformatted section) before writing back.
Losing someone's screenshot links or silently mangling their "How to manually test this" section
because you only had half the body in context would be a real regression, not a cosmetic one.
Fetching the images themselves (Step 5) only ever reads bytes to look at them — never write,
re-upload, or alter a URL.

## Step 1 — Get the PR

If `$ARGUMENTS` contains a PR URL or number, use it. Otherwise ask the user for the PR link
before doing anything else — don't guess which PR from branch context alone, since this command
mutates a real PR.

## Step 2 — Read the full current body first

Before composing any edit:

```bash
gh pr view <pr> --json number,url,title,body -R <owner>/<repo>
```

Read the entire `body` field. This is the one step that must happen before anything else touches
the PR — it's the only way to guarantee the reassembled body in Step 7 is complete.

## Step 3 — Locate the screenshots/video section

Find the heading that starts the media section. It's usually `## Screenshots or Video`, but be
flexible — also match `## Screenshots`, `## Screenshots/Videos`, `## Media`, or similar, case
insensitively. The section runs from that heading to the next `##` heading (or end of body if
it's the last section).

If no such section exists, tell the user and stop rather than inventing one.

## Step 4 — Parse out the individual media items

Within the section, each item is typically one of:

- An HTML `<img ... src="..." ... />` tag (this repo's screenshots come from pasting into GitHub,
  which produces `<img width="NNN" height="NNN" alt="..." src="https://github.com/user-attachments/assets/...">`)
- A markdown image `![alt](url)`
- A video — either a `<video>` tag or a bare `user-attachments` asset link GitHub auto-embeds as a player

Keep the original `src`/`href` URL of every item byte-for-byte. These are GitHub-hosted asset
links tied to the PR — they cannot be regenerated, re-uploaded, or guessed, so treat them as
opaque and immutable. Only the surrounding formatting (labels, size, layout) is yours to change.

## Step 5 — Look at each image to write an accurate label

`alt` text on these images is usually just a camera-roll filename/timestamp (e.g. "Screenshot
2026-07-01 at 21 35 24") — it carries no information about what's on screen, so don't rely on it.
To label well you need to actually see what each screenshot shows.

Fetch each image and read it:

```bash
TOKEN=$(gh auth token)
curl -sL -H "Authorization: Bearer $TOKEN" -o /private/tmp/pr-format-img-<n>.png "<src url>"
```

`user-attachments` asset URLs require this authenticated request to resolve at all — an
unauthenticated `curl` returns a "Not Found" HTML page, not the image. Then use the Read tool on
each downloaded file to view it (this also OCRs any on-screen text — button labels, headings,
form field values — which is usually the strongest signal for what a screen represents).

For each image, combine what you see (on-screen headings, button text, form state, badges like
"Default") with the surrounding PR context — the title, "What should reviewers focus on?", and
the numbered steps in "How to manually test this" — to write a short, confident label (2–4 words,
e.g. "Empty state", "Add address form", "2 saved addresses", "Delete confirmation"). Seeing the
actual screen beats guessing from context alone, but the PR text is what turns "a form" into "the
add-address form" versus "the edit-address form" when two screens look similar.

If, after looking, two images are still genuinely indistinguishable, it's fine to fall back to
"Screenshot 1", "Screenshot 2", etc., or ask the user for a one-line hint — better an honest
generic label than a confident wrong one.

Delete the downloaded images from `/private/tmp` once you've written the labels — they were only
scratch material for reading, not something to keep around or reference again.

## Step 6 — Lay out the section

Default to a markdown table: one column per image, the label as that column's header, the image
in the row below. This reads as a horizontal strip a reviewer can scan left-to-right in one
glance, which is why it's preferred over stacking labeled images vertically — vertical lists force
a lot of scrolling for what's usually a short, comparable set of screens.

```
| Empty state | Add address form | 2 saved addresses |
|---|---|---|
| <img width="150" alt="Empty state" src="https://github.com/user-attachments/assets/..." /> | <img width="150" alt="Add address form" src="https://github.com/user-attachments/assets/..." /> | <img width="150" alt="2 saved addresses" src="https://github.com/user-attachments/assets/..." /> |
```

Put all images in a single table row when there are roughly 5 or fewer — that's the common case
for a feature PR's before/after/states sequence. If there are meaningfully more (say 8+), split
into multiple table blocks of a handful of columns each rather than one very wide table, so each
group still reads without horizontal scrolling.

Fall back to a vertical labeled list (bold label above each item) only when a table genuinely
doesn't fit the content — e.g. the section mixes images with a video (videos don't sit inside a
table cell cleanly), or there's just one item and a table would be pointless overhead.

Sizing: this repo's pasted screenshots typically carry oversized explicit dimensions like
`width="331" height="698"`, which makes the rendered PR body sprawl. Shrink the `width` attribute
to something compact — around 150px inside a table cell (narrower than a standalone image needs,
since several sit side by side), or 180–220px for a standalone image in the vertical-list
fallback. Drop the explicit `height` so the aspect ratio scales naturally. Don't enlarge anything
— the whole point of this pass is a *more* compact, scannable section, not a bigger one.

Videos generally can't be resized the same way (GitHub renders the embed itself); just add the
label above the existing video markup/link unchanged.

## Step 7 — Reassemble the full body

New body = (everything before the media section heading) + (the heading) + (your reformatted
section) + (everything from the next `##` heading onward, or nothing if it was the last section).
Everything outside the media section must be preserved exactly — same wording, same whitespace,
same emoji, same checkbox states. Diff your reassembled body against the original mentally (or
literally) and confirm the only delta is inside the media section before moving on.

## Step 8 — Preview and confirm

Show the user a before/after of just the screenshots section (not the whole body — they already
know the rest didn't change). Ask for explicit confirmation before writing anything back to
GitHub — this mutates a PR other people may be watching, so don't `gh pr edit` on your own
judgment call alone.

## Step 9 — Apply

```bash
cat > /private/tmp/pr-format-<number>.md << 'EOF'
<full reassembled body>
EOF
unset GITHUB_TOKEN && gh pr edit <number> -R <owner>/<repo> --body-file /private/tmp/pr-format-<number>.md
```

Use `--body-file`, never inline `--body "..."` — a multi-line body with markdown headers breaks
shell quoting. `unset GITHUB_TOKEN` first: a stale personal access token in the environment can
shadow the correct authenticated `gh` keyring token and cause the edit to fail or hit the wrong
account.

## Step 10 — Confirm

Report success and print the PR URL so the user can glance at the result.

---
name: verify-against-linear-design
description: Given a GitHub PR URL, find the Linear ticket it implements, hunt that ticket (description, every comment, every attachment) for design pictures, re-upload those pictures into a new PR comment so they're visible without a Linear login, then drive the iOS Simulator on the PR's own branch to compare the shipped UI against each design image and write up exactly where it matches and where it deviates. Use when asked to "/verify-against-linear-design", "check this PR against its Linear design", "did we actually build what the mockup showed", "copy the Figma/design screenshots into the PR and check compliance", or similar — this is a compliance audit of an already-open PR, not a step in implementing or reviewing code changes generally.
argument-hint: <pr-url>
allowed-tools: Bash(curl *), Bash(gh *), Bash(git *), Bash(agent-browser:*), Bash(xcrun *), Read
---

Verify the PR at $ARGUMENTS matches its Linear ticket's design pictures, copy those pictures into a PR comment, and report exactly how closely the shipped UI follows them.

This composes three things this repo already has working mechanics for, rather than re-deriving any of them: `linear-implement-task`'s design-hunt technique (Step 3a — find every design picture in a Linear ticket, not just the description), `ios-simulator` for driving the app to capture the current UI, and `post-screenshots-to-pr`'s upload technique for minting real `user-attachments/assets/` URLs GitHub will render inline. Read those if a mechanic below is unclear — don't guess at a shape this repo has already solved.

## Step 1 — Resolve the PR and its Linear ticket

```bash
unset GITHUB_TOKEN && gh pr view <pr> --json number,url,title,body,headRefName -R <owner>/<repo>
```

`create-pr`'s template guarantees a `## Linear Issue` section on every PR opened through it. Extract the issue URL/identifier from it. If that section is missing, empty, or literally `N/A` (this repo's `hotfix-pr` skill produces exactly that for tickets that were never meant to have one) — say so plainly and stop. There is nothing to verify a hotfix against.

## Step 2 — Hunt the Linear ticket for design pictures

Read the `LINEAR_API_KEY` and query the issue exactly as `linear-implement-task` does in its Step 2-3:

```bash
grep '^LINEAR_API_KEY=' /Users/guilhermereis/Desktop/clones/shopit-monorepo/.env.local | tail -1 | cut -d'=' -f2
```

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: <key>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ issue(id: \"<IDENTIFIER>\") { id identifier title description attachments { nodes { title url subtitle } } comments { nodes { body createdAt user { name } } } } }"
  }'
```

Scan the `description`, **every** comment `body`, and every `attachments` entry — the same three places `linear-implement-task` scans, for the same reason (SHO-420/PR #616: a design posted mid-thread as a comment was missed because only the description was treated as authoritative). Collect every `uploads.linear.app` (or otherwise directly fetchable) image URL you find.

If a design reference is a Figma/Zeplin/etc. link rather than a directly fetchable image, note that plainly in the eventual report ("a Figma link was found at <url> but could not be rendered/copied automatically") rather than silently skipping it.

**If this scan turns up zero design pictures** — not in the description, not in any comment, not in attachments — **this is a hard stop, not a "proceed with caveats" situation.** Tell the user plainly: "No design picture found in <ticket identifier> — checked the description, every comment, and attachments." Then finish the run there. Do not check out the branch, do not touch the simulator, do not post a comment — there is nothing to copy over and nothing to compare against, so every later step would either be a no-op or, worse, an analysis that looks substantive but is actually comparing the build against nothing. A Figma/Zeplin/etc. link (Step 2's other case, above) is not "zero" — that's a found-but-unfetchable reference, and still gets named in a report; this stop is specifically for the case where the hunt across all three locations comes back completely empty.

## Step 3 — Download every design picture found

```bash
curl -s -L -o <scratchpad>/verify-design-<owner>-<repo>-<pr>/linear-design-<n>.png "<image-url>"
```

Use the same collision-proof, per-PR-numbered scratch folder pattern `do-all-manual-testing` uses, so a batch of these across several PRs never mixes images up. `Read` each downloaded image before moving on — you need to have actually looked at it to compare it against anything later.

## Step 4 — Bring up the PR branch, backend, and simulator

Check out `<pr>`'s branch and get the app running on the iPhone 16e simulator in the same order `do-all-manual-testing` uses in its own Setup note (checkout branch → Convex dev watcher → Metro → boot iPhone 16e → launch app, confirming the running build actually reflects this branch before trusting any screenshot). Don't re-derive that sequence here — read that skill's Step 4 if you need the exact commands. Load the `ios-simulator` skill before touching the simulator, same as that skill does.

Navigate to whatever screen(s) the design pictures depict — infer this from the ticket title/description and the pictures themselves (a picture of a product detail page means navigate to a product detail page). If it's unclear which screen a picture is meant to represent, say so rather than guessing at a screen and comparing against the wrong one.

## Step 5 — Capture the current UI and compare against each design picture

For each design picture from Step 3, capture a matching screenshot of the current implementation in the same state (same screen, same data conditions where feasible — e.g. an empty state design needs an empty-state screenshot, not a populated one). Then compare the two directly — you have native image understanding, use it, the same way `linear-implement-task`'s own Step 9 already expects a side-by-side comparison before calling a build done.

For each pair, note specifically:
- **Layout & structure** — same components, same order, same grouping.
- **Colors** — background, text, accent/CTA colors; call out an actual mismatch, not a lighting/screenshot artifact.
- **Spacing & sizing** — obviously-off padding, margins, image/button proportions.
- **Copy** — exact text where the design shows real copy, not lorem-ipsum-style placeholders.
- **States** — if the design shows a state (empty, error, loading, disabled) that you didn't capture or that the build doesn't actually implement, say so explicitly rather than comparing only the happy path.

Judge fidelity like a design reviewer, not a pixel-diff tool: minor anti-aliasing or a slightly different stock photo isn't a deviation; a different layout, wrong color, missing state, or changed copy is.

## Step 6 — Copy the design pictures into a PR comment

Upload every downloaded design picture (Step 3) and every current-UI screenshot (Step 5) so they render inline for anyone viewing the PR — a Linear-hosted image URL requires a Linear login and won't render for a reviewer without one, which is the whole reason to "copy them over" rather than link to them.

Use `post-screenshots-to-pr`'s upload mechanics, but targeting a **new comment**, not the PR description:

1. `agent-browser --profile ~/.agent-browser-profiles/github open "<PR_URL>"`, confirm `meta[name=user-login]` isn't `null`.
2. The comment box at the bottom of the PR conversation has textarea `#new_comment_field` and file input `#fc-new_comment_field` — enumerate inputs to confirm before relying on this if the page layout looks different than expected.
3. `agent-browser upload "#fc-new_comment_field" <path>` once per image (multi-file calls are unreliable — see `post-screenshots-to-pr`). Each upload mints a real `user-attachments/assets/<uuid>` URL immediately, before the comment is ever submitted.
4. Read the URLs back out of `#new_comment_field`'s value, mapped to files by the `alt=` filename each upload inserts.
5. **Never submit the browser's comment box and never read its body as the source of truth.** Navigate away (or reload) to discard it — the minted URLs already persist on GitHub's CDN. Assemble the actual comment yourself (Step 7) and post it with `gh`, the same "browser only mints, `gh` performs the real write" split this repo uses everywhere else it uploads images.

## Step 7 — Assemble and post the comment

```markdown
## Design compliance check — against <Linear ticket identifier and title>

### From Linear
<the copied-over design pictures, one per row/table, each labeled with what it depicts>

### Current implementation
<the matching current-UI screenshots, labeled the same way so a reader can pair them by eye>

### Analysis
<one paragraph or bullet list per design picture: what matches, what deviates, using Step 5's findings — be specific and cite the concrete difference, not "looks close">

### Overall
<one line: fully compliant / minor deviations / significant deviations, plus a one-sentence reason>
```

```bash
unset GITHUB_TOKEN && gh pr comment <pr> -R <owner>/<repo> --body-file <tmp-file>
```

This posts a comment — never a review (`gh pr review`), and never `--request-changes`, per this repo's own review-posting convention. A design deviation is worth surfacing, not blocking on unilaterally.

## Rules

- Do not fabricate a comparison for a design picture you didn't actually download and look at, or against a screen you didn't actually navigate to and screenshot.
- Do not silently skip a Figma/Zeplin/other non-image design link — name it in the report as something that needs manual comparison.
- If the simulator/backend can't be made to reflect this PR's branch (mirrors `do-all-manual-testing`'s own failure mode), report that plainly and still post whatever the Linear-side hunt found — a partial report (designs found, but current UI unverified) is more useful than nothing.
- Post exactly one comment per run. If re-run on the same PR, that's a fresh comment, not an edit to the previous one — compliance can change between runs and the history is itself useful.

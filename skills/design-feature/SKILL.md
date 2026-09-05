---
name: design-feature
description: >-
  Figure out the design changes and net-new screens a feature needs, then build a
  publicly-shareable review page — real screenshots for every screen that already exists
  (changes screenshotted from a throwaway spike), HTML mockups only for genuinely new screens —
  optionally plus an editable Claude Design canvas. Use this
  whenever the user points at a feature — a GitHub PR, a Linear
  ticket, or a plain-English description — and asks you to "figure out the design changes or
  additions", "design this feature", "what needs to change in the UI for X", "mock up the
  screens for Y", "sketch the received-shelf / thank-you flow", or otherwise wants a visual
  proposal grounded in what the app already has. Also trigger when the user wants to explore
  the current UI for a feature before deciding what to build. This is a mobile app (Expo / React
  Native, `apps/mobile`); the mockups are HTML/CSS artboards, not native code. Don't use this for
  implementing a feature in code (that's linear-implement-task) or for pure written research
  with no visual output.
---

# Design a feature

The goal is a **visual proposal a human can react to and forward**: a publicly-shareable review
page that puts the app's current screens next to the proposed ones. A screen that already
exists — current, or a change to it — is a **real screenshot** (the change screenshotted from a
throwaway implementation spike); only a genuinely **new** screen is an HTML mockup. The written
brief — what changes, what's new, what can be reused — goes in the **conversation, never on the
page**. Optionally also an editable Claude Design canvas for hands-on iteration. Implementation
happens later, in code, against the approved screens.

**The review page carries only screens and concise titles.** No AI-written thesis, captions,
explanations, rationale, or footnotes — ever. A short factual title per screen plus a
`CURRENT` / `NEW` tag is the whole of the page's text. Everything you'd want to say *about* the
design is said in the conversation alongside the link.

Work in this order. Each step feeds the next — skipping the grounding steps produces
generic-looking mockups that ignore the design system and reinvent things the app already has.

---

## 1. Gather the feature context

Resolve whatever the user pointed you at into a concrete picture of the feature.

- **GitHub PR** (`#572`, a PR URL): `unset GITHUB_TOKEN; gh pr view <n> --repo ShopIt-LLC/shopit-monorepo --json title,body,headRefName,files`. Groundwork PRs on this repo often carry a full written map of the current flow in the body (see `fix/thank-you-received-shelf-groundwork` / PR #572) — mine it, it saves you the code archaeology.
- **Linear ticket** (`SHO-123`, a Linear URL): invoke the `linear` skill to fetch the issue description and every comment. Decisions and scope cuts usually live in the comment thread.
- **Plain description**: use it as-is, but ask one or two sharpening questions if the surface area is unclear ("Is this a new tab, or does it live inside an existing screen?").

Then load the guardrails the mockups must respect:

- `.claude/ai/design-system.md` — `Button` and `Input` are standardized and locked; use their real variants/sizes, don't invent new ones.
- `apps/mobile/components/ui/` — the actual primitives (buttons, inputs, sheets, cards).
- Skim two or three existing screens in the same area of the app so the proposal matches established layout, spacing, and navigation patterns rather than a generic mobile aesthetic.

Write down, in a sentence or two: what the feature is, who the user is in that moment, and which flows/screens it touches.

## 2. Map the current UI from the code

Before any simulator work, find the relevant screens and components by reading the repo. This is
free, needs no permission, and tells you exactly what "current state" means.

- `apps/mobile/app/` — routes/screens (expo-router). 
- `apps/mobile/components/` — sheets, cards, heroes, flow pieces.
- Grep for the feature's nouns (`grep -ri "gift" apps/mobile/app --include=*.tsx -l`) and for existing data hooks / Convex queries that already return something close to what the feature needs.

Produce a concrete list: `apps/mobile/app/gift/[giftId].tsx` (the claim screen), `components/sheets/OrderSheet.tsx` (where a received gift is shown read-only), etc. Note any **reuse candidates** — a component, a query, a notification type, a copy string that already exists and is close to what's needed. The feature is almost always "recombine what's there", not "build from zero".

## 3. Capture the current screens as real screenshots

Every panel that will be labelled `CURRENT` / "ships today" on the review page **must be a real
screenshot from the running app**. Code reconstructions of current screens do not go in the
final artifact. This is a gate for the CURRENT panels — not an optional enhancement. (The
NEW/CHANGED panels never touch the simulator.)

This repo's rule still holds: **never drive, screenshot, or look at the iOS simulator unless the
user explicitly asks you to** (`.claude/CLAUDE.md`). So ask once, up front, framed as required
input — using the screen list from step 2:

> The current-state panels have to be real screenshots. I need to drive the simulator to walk
> these screens and capture them: [list]. OK to go ahead? Or capture them yourself and drop
> them here.

- **Green light**: use the `ios-simulator` skill to open the app and navigate, or the
  `screenshot-screen` skill for a batch capture. Walk to each current screen from step 2 and
  capture it. **Two-user flows** (gifting, follows, notifications): both dev accounts are in
  `packages/convex/.env.local` (`DEV_ACC_1_*` / `DEV_ACC_2_*`) — sign in via the dev-only
  "Continue with email" button, act from one account, switch, screenshot the receiving side.
  Dismiss any OS overlay (rating prompt, permission dialog) before the shot. Save PNGs to
  `.claude/skills/design-feature/design-feature-workspace/<feature-slug>/screens/` with names
  that map to the brief (`current-gift-claimed.png`, `current-order-history.png`). Keep this
  simulator session alive — step 5 reuses it to screenshot the CHANGE screens.
- **Declined, or the simulator can't be reached**: you cannot finish the CURRENT panels. Say so
  plainly. Either wait for the user to hand you screenshots, or ship an interim page with those
  panels stamped "reconstructed from code — not verified on device" and tell the user they are
  placeholders until real captures land.

## 4. Decide: what changes vs. what's new

This is the deliverable the user actually asked for. Write it before building the page — the
page visualizes this breakdown, it doesn't replace it. **The brief lives in the conversation.**
None of its prose is copied onto the review page (see step 5).

Use this structure:

```
## Design brief: <feature>

**What it is:** <one or two sentences — the user's goal in this moment>

**Current state:** <what exists today for this flow, with file references. If nothing
exists, say so plainly — "there is no thank-you screen today" — that's a valid finding.>

**Changes to existing screens**
- `<screen / component>` — CHANGE: <what's different and why>. Reuses <existing component/prop>.
- ...

**New screens / components**
- `<name>` — NEW: <what it is, where it sits in navigation, what it shows>. Built from
  <existing primitives>. Data comes from <existing query, or "needs a new query">.
- ...

**Reuse notes:** <components, queries, notification types, copy strings already in the repo
that this feature should lean on instead of duplicating>

**Open questions:** <scope ambiguities, anything needing a product call before implementation>
```

Keep every "CHANGE"/"NEW" line tied to a real file or a real design-system primitive. Vague
lines ("improve the layout") are a sign you haven't looked hard enough yet.

## 5. Build the shareable review page

A single static HTML artifact: a grid of screens, current next to proposed. Two hard
constraints:

> **1. Screens and titles only.** The only text on the page is a concise factual title per
> screen (`A1 · app/gift/[giftId].tsx`, `Order History`, `gift_thanked notification`) plus a
> `CURRENT` / `NEW` tag. No thesis, no legend sentences, no captions describing the change, no
> footnotes, no rationale — nothing an AI wrote *about* the design. If it's a sentence, it
> belongs in the conversation, not on the page. The one exception is the user's own commentary
> section, added on request after publish (see the end of this step) — their words, not yours.
>
> **2. Publicly shareable.** Publish with **no `capabilities`** — no `assets`, no file
> downloads, no `<a download>` links. An artifact that offers downloads can't be shared
> publicly, and that's why the `design`-skill canvas (step 6) can never be the shared artifact:
> its "download canvas files" feature greys the toggle out permanently.

Build it:

- **Load the `artifact-design` skill first** (required before writing any artifact HTML), then
  write to `.claude/skills/design-feature/design-feature-workspace/<feature-slug>/share/<feature-slug>.html`.
- **Layout**: a 2-column grid, current-state screen on the left, proposed on the right, one row
  per flow, in the order the user moves through them. For an all-new flow, two proposed screens
  side by side, both tagged `NEW`. Each cell = the concise title line + the screen. Nothing
  else between cells.

Render each cell by its kind — from step 4's brief, a screen is CURRENT, a CHANGE to an existing
screen, or a NEW screen:

- **CURRENT cell → real screenshot** (step 3). Embed each PNG as a base64 `data:` URI inline in
  the HTML (keeps the page free of the `assets` capability, so it stays publicly shareable).
  Downscale first — `sips --resampleWidth 640 in.png --out out.png` — so the whole file stays
  well under the 16 MB artifact limit. Frame each in a phone-proportioned box the same width as
  the other cells.
- **CHANGE cell → the real screen with only the delta.** The screen already exists, so a
  from-scratch HTML redraw is never acceptable — it drifts from the real thing in a dozen small
  ways and buries the one change that matters. Two ways to do it right, best first:
  1. **Implement the change on the mockup branch, run it, screenshot it** (same simulator
     session as step 3). This is the highest fidelity — it *is* the app plus the delta — and it
     shows states a screenshot of today can't (a new filter active, a new row type). It doubles
     as an implementation spike.
     - **Always cut a dedicated branch** off the working branch's `HEAD`, named
       `mockup/<feature-slug>`, and **commit** the spike edits there so the screenshots stay
       reproducible. Commit subject `spike(design): <feature> mockup changes for review
       screenshots`, body noting it is a throwaway visual spike, not for merge. Never PR or
       merge it. Never add assistant attribution (CI gate). On this repo the husky pre-commit
       hook needs `node` on PATH, which this machine lacks — commit the spike with
       `--no-verify`.
     - Keep the edits **client-only**: never touch the shared Convex schema or write junk data
       to the shared dev backend — inject any sample data (a synthetic notification row, a
       stubbed filter result) on the client, and mark it with a `// design spike` comment.
     - The spike needs Metro hot-reload: `cd apps/mobile && bun run start`. On this repo Metro
       needs Watchman or it crashes on the first file change with
       `TypeError ... 'changes.addedFiles'` — if `watchman` isn't installed, `brew install
       watchman`, `watchman watch-project <repo>`, then start Metro. Relaunch the dev build
       (`xcrun simctl launch <udid> mobile.shopit.store.dev`) so it attaches.
     - After screenshotting every CHANGE screen, `git checkout` back to the working branch. The
       `mockup/<feature-slug>` branch stays for re-takes (step 7).
  2. **Overlay the delta on the CURRENT screenshot.** Only when the diff is too big for a quick
     spike. Position the new elements with percent coords over the screenshot `<img>`, take
     colours from the design tokens the screenshot already uses, ring the added element and pin
     a small `NEW` on it, and redraw only the region that actually reflows. An overlay lies if
     the addition pushes existing content around — if it does, fall back to option 1.
- **NEW cell → HTML mockup.** No counterpart in the app, so fidelity is to the design system,
  not to a screenshot. Each artboard is standalone HTML with its own `<style>` and colliding
  class names (`.phone`, `.title`, `.btn`…), so isolate each in its own `<iframe>` via `srcdoc`
  (`iframe.srcdoc = '<!doctype html>…<style>'+css+'</style>'+body`). The boards are 430px wide.
  Wrap each in a box with `aspect-ratio: 430 / 950; overflow: hidden`, and scale the iframe to
  the box: on load **and on `resize`/`orientationchange`**, set
  `iframe.style.transform = 'scale(' + (box.clientWidth / 430) + ')'` (`transform-origin: top
  left`; keep a static `transform: scale(0.72)` in CSS as the first-paint fallback). Never put a
  length inside `scale()` or `calc(430px * …)` — a viewport-derived `--s` is a length and
  silently voids both. Reuse step 6's canvas markup if there is one.
- **Design system** for the mockups and the page frame: palette and type from
  `.claude/ai/design-system.md` (button `#D34006`, brand `#FF591F`, ground `#FAF9F7`); design
  light and dark.
- **Responsive — always.** The page is forwarded and opened on phones. Build it mobile-safe from
  the start, don't bolt it on:
  - Grid tracks are `minmax(0, 1fr)`, never bare `1fr`; every flex/grid child that holds a
    screen (`figure`, the `.shot` screenshot box, the mockup box) gets `min-width: 0`. Bare
    `1fr` + default `min-width: auto` lets a wide screenshot blow the column past the viewport.
  - A `@media` breakpoint (~640px) drops to one column, makes the screenshot/mockup boxes
    `width: 100%`, tightens page padding, bumps the mono captions up a point and lets them wrap,
    and removes any `max-width` cap on the commentary card.
  - `body { overflow-x: hidden }` as a backstop; `img { max-width: 100% }` on every screenshot.
  - Before handing over the link, check the page once at a real narrow width (~390–430px), not
    just desktop.

Publish with the Artifact tool (no `capabilities`). Post the step-4 brief in the **conversation**
next to the link, and tell the user how to open sharing: **artifact → share menu → Share
publicly → copy link.**

> **The public link is a frozen snapshot, not a live mirror.** Re-publishing through the tool
> updates the private artifact only — a logged-out visitor keeps seeing whatever version was
> public when sharing was first turned on. The tool cannot push a new version to the public
> link; only the user can, from the share menu. So **every time you redeploy the review page
> (here or in step 7), end your message by telling the user to re-publish the latest version as
> the public one** (share menu → publish/update the current version) and hard-refresh. Say it
> even if they haven't mentioned the public link — a stale share is the default failure mode.

**Then always ask (via `AskUserQuestion`): do they want a personal commentary section on the
page?** This is the one block of prose allowed on the review page — because the user writes it,
not you.

- If yes: they give you the text. Add it **verbatim** as a card at the very top of the page,
  above the screen grid, headed `<Name>'s commentary` (e.g. `Guilherme's commentary`). Style it
  in the page's own tokens (`--card` / `--line` / `--ink`, mono uppercase heading). Treat each
  line break they mark as a paragraph break. Do not edit, tighten, or summarise their words.
  Redeploy to the same URL.
- If no: leave the page as screens-and-titles only.

## 6. Optional: an editable canvas for hands-on iteration

If the user wants to drag artboards around and edit them directly, also invoke the **`design`**
skill to build a Claude Design canvas — same layout logic (current left as the step-3
screenshots, proposed right as the HTML artboards, flow order; match the real `Button`/`Input`
specs and the spacing from step 1). The canvas is a working surface where annotations and notes
are fine; it is **not** the shareable artifact (see step 5). Keep its proposed-artboard markup
identical to what the review page embeds.

Only do this when the user asks for an editable canvas or you expect several rounds of
structural change. For a one-shot proposal, the review page is enough.

## 7. Iterate

Small tweaks: edit the artboard markup and redeploy the review page to the same URL (and the
canvas, if there is one). Structural rethinks (a screen splits in two, the flow reorders):
update the brief first, then re-seed the affected artboards so brief, review page, and canvas
stay in sync.

Every redeploy: remind the user to re-publish the latest version as the public snapshot (see
the callout in step 5) — the tool only moves the private artifact forward.

**When the app itself changes**, re-capture the affected CURRENT screenshots (step 3), then
`git checkout mockup/<feature-slug>`, rebase or re-apply the spike if it drifted, reload the
app, and re-screenshot every CHANGE screen (step 5) — screenshots are the source of truth for
current *and* changed state, and stale ones defeat the point. NEW-screen HTML stays as-is
unless the proposal moved.

Stop when the user says the direction is right. Implementation happens later, in code, against
the approved screens — that's `linear-implement-task`, not this skill.

---

## Notes

- **Two-user features** (gifting, follows, notifications) have current-state UI on both sides.
  Decide with the user whose experience the feature is about, screenshot and mock that side;
  note the other side's touchpoints in the brief (conversation, not the page).
- **"There is no screen for this today"** is a common and legitimate current state. Each flow
  still needs a left cell — screenshot the nearest thing the user sees instead (an inbox row,
  an orders-list entry). It's still a real capture, not a reconstruction.
- **Nothing AI-written reaches the page.** Titles are factual labels (a filename, a screen
  name, a notification type), never a sentence. All analysis, rationale, and open questions
  stay in the conversation with the brief.
- If the user only wants the written breakdown and no mockups, stop after step 4 and say so —
  don't force the review page.

---
name: design-feature
description: >-
  Figure out the design changes and net-new screens a feature needs, then mock them up on a
  Claude Design canvas. Use this whenever the user points at a feature — a GitHub PR, a Linear
  ticket, or a plain-English description — and asks you to "figure out the design changes or
  additions", "design this feature", "what needs to change in the UI for X", "mock up the
  screens for Y", "sketch the received-shelf / thank-you flow", or otherwise wants a visual
  proposal grounded in what the app already has. Also trigger when the user wants to explore
  the current UI for a feature before deciding what to build. This is a mobile app (Expo / React
  Native, `apps/mobile`); the canvas is HTML/CSS artboards, not native code. Don't use this for
  implementing a feature in code (that's linear-implement-task) or for pure written research
  with no visual output.
---

# Design a feature

The goal is a **visual proposal a human can react to**: a Claude Design canvas that puts the
app's current screens next to proposed new-or-changed screens, plus a short written brief
explaining what changes, what's new, and what can be reused. The person then refines the canvas
by hand and you implement against the approved artboards later.

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

## 3. Explore the live app — only with an explicit green light

Seeing the real screens running beats reading JSX for judging spacing, density, and what a
screen actually feels like. But this repo has a hard rule: **never drive, screenshot, or look at
the iOS simulator unless the user explicitly asks you to** (`.claude/CLAUDE.md`). That includes
"just to confirm the layout".

So pause here and hand the user a choice. Show them the screen list from step 2 and say
something like:

> To ground the mockups in the real UI I'd like to walk these screens on the simulator and
> screenshot them: [list]. Want me to? Or if you'd rather, drive it yourself and drop the
> screenshots here.

- **If they green-light it**: use the `ios-simulator` skill to open the app and navigate, or the
  `screenshot-screen` skill for a batch capture of specific screens. Save the images into the
  workspace (see step 5) so they can go on the canvas as current-state artboards.
- **If they pass or don't answer**: proceed from the code reading alone. Rebuild the
  current-state artboards from the JSX — layout, components, copy — and label them
  "reconstructed from code, not verified on device" so the user knows what they're looking at.

Never block the whole skill waiting for simulator access; it's an enhancement, not a gate.

## 4. Decide: what changes vs. what's new

This is the deliverable the user actually asked for. Write it before opening the canvas — the
canvas visualizes this breakdown, it doesn't replace it.

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

## 5. Build the design canvas

Now invoke the **`design`** skill to create the canvas. Seed it deliberately:

- **Workspace for assets**: put screenshots and any working files in
  `.claude/skills/design-feature/design-feature-workspace/<feature-slug>/` so they're easy to
  find and reference from the artboards.
- **Layout**: left-to-right as a flow. Current-state artboards on the left (screenshots, or
  code-reconstructed screens), proposed artboards to their right in the order the user moves
  through them. Group "changed" screens next to their "before"; put "new" screens in flow
  position.
- **Fidelity**: match the app — the real `Button` variants and `rounded-full`, the real
  `Input` (48px, `rounded-2xl`), iOS-style nav and sheets, the spacing you saw in step 1.
  These are HTML/CSS artboards standing in for React Native, so aim for "clearly this app",
  not pixel-perfect native chrome.
- **Annotations**: on each changed/new artboard, call out what's different — a short caption or
  a callout layer. The canvas should be readable as "here's the change" without the written
  brief next to it.
- **Scope**: mock the screens in the brief and the immediately adjacent ones. Don't redesign
  neighboring flows that aren't part of the feature.

Post the written brief in the conversation and the canvas as its Artifact.

## 6. Iterate

The user refines elements directly on the canvas and tells you what to change. Small tweaks:
adjust the artboards in place and redeploy to the same canvas. Structural rethinks (a screen
splits in two, the flow reorders): update the brief first, then re-seed the affected artboards
so the canvas and the brief stay in sync.

Stop when the user says the direction is right. Implementation happens later, in code, against
the approved artboards — that's `linear-implement-task`, not this skill.

---

## Notes

- **Two-user features** (gifting, follows, notifications) have current-state UI on both sides.
  Decide with the user whose experience the feature is about and mock that side; note the other
  side's touchpoints in the brief.
- **"There is no screen for this today"** is a common and legitimate current state. The canvas
  still needs a left side — use the nearest thing the user sees instead (an inbox row, an
  orders-list entry) so the proposal has a "from" as well as a "to".
- If the user only wants the written breakdown and no canvas, stop after step 4 and say so —
  don't force the `design` step.

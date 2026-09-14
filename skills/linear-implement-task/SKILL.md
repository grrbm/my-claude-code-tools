---
name: linear-implement-task
description: Implement a Linear task given its URL. Use when asked to implement a Linear task or given a Linear issue URL. Fetches the issue, all comments, and all attachments — hunting specifically for design references (mockups, Figma links, screenshots) wherever they're posted — then creates a branch from main and implements the feature to match those designs precisely.
argument-hint: <linear-issue-url>
allowed-tools: Bash(curl *), Bash(git *), Read, Glob, Grep, Edit, Write
---

Implement the Linear task at: $ARGUMENTS

## Why this skill front-loads a design hunt

On SHO-420 (PR #616), the ticket's design decisions were posted as a Linear **comment**, not in the description. The comment was never read closely enough to notice the images, the feature was built to an approximate/incorrect interpretation, and the mistake was only caught after a large PR had already been reviewed and partially reworked. Designs are a first-class requirement of a Linear task, wherever they're posted — a description, a comment, an attachment — and missing one is not a minor gap, it's building the wrong thing. Step 3 below exists specifically so this cannot happen silently again.

## Workflow

1. Parse the Linear issue URL.
2. Read the `LINEAR_API_KEY` by running:
   ```bash
   grep '^LINEAR_API_KEY=' /Users/guilhermereis/Desktop/clones/shopit-monorepo/.env.local | tail -1 | cut -d'=' -f2
   ```
   Use this value directly in the Authorization header — never use `$LINEAR_API_KEY` from the environment, as it may be stale.
3. Fetch the issue details, all comments, **and all attachments** from Linear in a single request using the key from step 2. Attachments (e.g. a linked Figma file) are a separate field from comments — a query that omits them silently misses issue-level design links:

   ```bash
   curl -s -X POST https://api.linear.app/graphql \
     -H "Authorization: <key>" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "{ issue(id: \"<IDENTIFIER>\") { id identifier title description priority estimate state { name } assignee { name } labels { nodes { name } } attachments { nodes { title url subtitle } } comments { nodes { body createdAt user { name } } } } }"
     }'
   ```

   Read every comment — they often contain the most current requirements and scope clarifications that supersede the original description.

### Step 3a — Hunt for design references (mandatory, do not skip)

Before doing anything else, scan the issue `description`, **every** comment `body`, and every `attachments` entry for design artifacts. Treat each of these as a design reference:

- Inline images — markdown `![...](...)` syntax, especially URLs under `uploads.linear.app` (these are pasted screenshots/mockups and are directly viewable).
- Links to a design tool: Figma, Zeplin, Sketch Cloud, Framer, InVision, Miro, Abstract, Adobe XD.
- Any `attachments` node — these are almost always a linked design file.
- Phrasing like "see design", "per Figma", "as designed", "mockup attached", "spec attached", "final frames", even without an actual link right next to it — if a comment *references* a design, keep reading nearby comments for the actual link/image before concluding there isn't one.

Do this scan across the **whole thread**, not just the description and the most recent comment — the incident this skill is fixed against happened because a design was posted mid-thread and only the description was treated as authoritative.

**For every design artifact found:**

- An `uploads.linear.app` (or otherwise directly fetchable) image: download it and actually look at it before writing any code.
  ```bash
  curl -s -L -o /tmp/linear-design-<n>.png "<image-url>"
  ```
  Then `Read` the downloaded file — the Read tool renders images. Do not skip this because the URL is present in the text you already "read"; text containing an image link is not the same as having looked at the image.

  Once you've looked at it, invoke the `screenshot-to-code` skill on this downloaded image before hand-writing the UI yourself — it exists specifically to turn a UI screenshot into an accurate structural/styling breakdown (layout, components, spacing, colors) rather than relying on an unaided visual read. Tell it explicitly that the target is this repo's Expo/React Native app (`apps/mobile`), not web React/Tailwind — its default output — so it should describe the design in those terms (React Native primitives, this repo's existing components/design tokens, no HTML/CSS/Tailwind). Treat its structural breakdown as an input to Step 8's implementation, not a drop-in file — still follow this app's own component conventions and locked-component rules.
- A Figma/Zeplin/etc. link that can't be fetched and rendered this way: state plainly in your response that a design-tool link was found and you cannot render it directly — ask the user for a screenshot/export of the relevant frame(s), or use a configured Figma/design-tool MCP or plugin if one is available in this session. Never silently proceed as if the link weren't there.

**If a UI-touching ticket has no design reference anywhere** (description, comments, or attachments), say so explicitly before implementing — "no design reference found in the ticket or its comments" — rather than silently assuming none exists and improvising the UI from the prose alone.

Once found, treat every design as **authoritative and binding** for anything it actually specifies: exact copy, spacing, layout, field order, states (empty/error/loading), and colors. "Close enough" or a plausible-looking alternative is not acceptable where a design exists — match it precisely. Where the design is silent on something (e.g. an error state it doesn't show), use judgment and say so, but never let judgment override a detail the design actually shows.

4. Checkout `main` and pull the latest from origin.
5. Create a branch from the updated `main` using:

   ```
   feat/<issue-key-lowercase>-<kebab-case-title>
   ```

   Example: `feat/sho-114-cart-replace-hardcoded-tax-and-shipping-pricing`

6. Checkout the new branch.
7. Review the issue description, all comments, and every design reference found in Step 3a together — use the latest clarified requirements from the task discussion, matched against the actual designs.
8. Implement the feature to match the designs precisely wherever they specify something concrete.
9. If the change is UI-facing and a design reference exists, before declaring the task done, compare the built UI against the design side by side (e.g. a simulator screenshot next to the downloaded design image) and call out explicitly whether it matches or where it deviates and why — don't just assert it matches without having actually looked at both side by side.

## Rules

- Always base the branch on the latest `main`.
- Always read the Linear task, all comments, and all attachments before coding.
- Do not skip clarifying comments or implementation notes.
- **Never treat a comment or attachment containing an image or design-tool link as optional context.** It is a requirement, not background reading.
- If a design image was found, you must have actually opened it (via download + Read) before implementing — referencing that the link exists is not the same as having looked at it.
- If a design image was found and downloaded, you must have run it through the `screenshot-to-code` skill before implementing — don't skip straight from "I looked at it" to hand-writing the UI from memory.
- Do not ask whether to checkout `main`, pull, or create the branch — do it automatically.
- Start implementation after the branch is ready and task context — including the design hunt — is fully read.
- If an existing local branch for the same issue exists, mention it before creating a duplicate.
- If access/authentication fails, explain the exact missing command, credential, or permission.

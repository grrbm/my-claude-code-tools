---
name: architecture-meeting-suggestions
description: Generate concrete talking points for Guilherme to bring to the Monday architecture sync meeting. Use this skill whenever the user asks for meeting ideas, what to bring to architecture sync, suggestions for the Monday meeting, or what to discuss with the team this week. Explores the actual codebase (mobile app + convex backend) plus recent commits, open PRs, and Linear tickets to surface grounded, systemic observations — not invented busywork, not one-off bug fixes. Also surfaces 3 "fresh feature" ideas — completely new features borrowed from other apps that Shopit doesn't have yet. Pass a bare number to get only that many fresh feature ideas, with no systemic suggestions.
allowed-tools: Bash(git *), Bash(curl *), Bash(gh *), Bash(open *), Bash(printenv *)
argument-hint: [N — fresh-feature-ideas-only count, e.g. "8"; omit for the default: 3 fresh feature ideas + 3-5 systemic suggestions]
---

Generate exactly 3 "fresh feature" ideas (a distinct category, see below) **first**, followed by 3-5 concrete suggestions grounded in what's actually in the codebase. The fresh feature ideas serve a different goal: inject completely new feature concepts, borrowed from other apps, that nobody on the team has proposed yet. The goal of the systemic suggestions that follow is to surface non-obvious observations the team should weigh in on — not tasks already being done, not abstract ideas, and NOT one-off bug-fix reminders (see "altitude" below).

## Custom count mode

If the arguments contain a bare integer N (e.g. `/architecture-meeting-suggestions 8`), switch to **fresh-ideas-only mode**: generate exactly N fresh feature ideas and skip systemic suggestions entirely — do not run Step 4, and Step 5's output (both the printed response and the file/PR) contains only the fresh feature ideas block, no "## Systemic suggestions" header at all. Every other rule for fresh feature ideas (variety, novelty verification, discarded-ideas memory) still applies, just repeated N times instead of 3. If no bare integer is present, run the default mode (3 fresh feature ideas + 3-5 systemic suggestions) as described below.

## Guilherme's focus areas

You're building these suggestions for Guilherme, whose role is:
- **User-facing app flows** — how new users onboard, how existing users navigate, where flows break or feel incomplete
- **Prototypes** — quick experiments worth building to validate ideas before committing to full implementation
- **Product polish** — visual consistency, interaction quality, edge cases that make the product feel unfinished

Each suggestion should come from one of these angles, but don't self-censor backend/convex findings — if a backend pattern (e.g. duplicated logic, missing schema field, missing scheduled job) has a direct, nameable cost to shipping user-facing features or to product growth, it's fair game. Frame it from that impact ("every feature I ship has to be built twice"), not as generic backend architecture commentary. Avoid pure build/release/CI topics (Wolfgang's territory) or deep AI-infra internals (Jason's) with no user-facing angle.

## Fresh feature: what counts

This is a distinct category from the systemic suggestions below, with the opposite grounding rule — instead of deriving from a codebase pattern, it derives from **outside** Shopit. A fresh feature idea is something Shopit doesn't have at all yet, that you've seen work well in another mobile or web app. Examples of the shape (don't reuse these verbatim — they're here to calibrate the size/genre of idea, generate new ones each run):

- "Re-add past order to cart" (iFood has this)
- "Wishlist item thumbnail upload" (user-supplied image, not just a product photo)
- "Shake device to clear cart"
- "Post owner can shadow-delete a comment" (YouTube has this — comment looks deleted to everyone but the commenter)

Rules for a good fresh feature idea:
- **Completely new**, not a variation or extension of an existing Shopit feature — if it's an improvement to something that already exists, it belongs in the systemic suggestions below, not here.
- **Borrowed from a named app or a clearly identifiable pattern** ("like X does") — this is what separates it from an abstract idea. Naming the source is what makes it concrete enough to discuss.
- **Verify it doesn't already exist in Shopit** before proposing it — quickly grep/Explore the mobile app for the feature name or an obvious equivalent. Don't waste the team's time re-proposing something already shipped.
- Should plausibly fit Shopit's product (shopping/commerce/social-commerce) — don't force-fit an idea that only makes sense in an unrelated domain.
- Keep it small enough to say aloud in 15-20 seconds and to prototype quickly — this is a spark for discussion, not a spec.

## Altitude: what counts as a systemic suggestion

Suggestions must be systemic — a pattern repeated across multiple features, a structural gap, or a researched should-we-or-shouldn't-we call. They must NOT be "did fix X from PR A also get applied to screen B" or any other single-PR leftover — that's a Slack message, not an architecture topic. Also do not flag things the team has already made an explicit, working call on (e.g. running multiple deliberate variants of a flow, or an accepted process like iterative self-review commits before merge) — those aren't up for debate and raising them reads as not having done the homework. If unsure whether something is settled, prefer a finding that's clearly still open.

## Memory — discarded ideas

This skill keeps its own memory file, local to this skill directory (not the Claude global auto-memory system): `.claude/skills/architecture-meeting-suggestions/discarded-ideas.md`. It exists so an idea the team has already discarded never gets re-proposed later, even reworded. Create it with an empty "Fresh feature ideas" / "Systemic suggestions" structure if it doesn't exist yet.

- **Read it in Step 3**, before brainstorming — never propose a fresh feature idea that's the same underlying concept as one already listed, even under a different name.
- **Write to it any time an idea is discarded** — mid-run ("skip that one, we already tried it"), while reviewing a run's output later (e.g. a comment on the draft PR, or a follow-up message naming specific ideas from a past run), or completely out of band. This isn't limited to a full skill invocation — treat "discard idea X" as an instruction to append to this file whenever it's said, regardless of what else is happening in the conversation.
- **Entry format**: headline, a one-line description (enough to recognize the idea even if reworded), the date discarded, and the source (a PR link if there's an artifact, otherwise "conversation").
- Systemic suggestions can be discarded the same way, filed under their own section in the same memory file — rarer in practice since they're grounded in current codebase state and tend to naturally stop applying as the code changes, but log it if the team explicitly rejects one on its merits.

## Step 1 — Verify required credentials (run in parallel)

```bash
printenv LINEAR_API_KEY
```

```bash
unset GITHUB_TOKEN && gh auth status 2>&1
```

If `LINEAR_API_KEY` is empty (printenv returns nothing), **stop immediately**:

> "LINEAR_API_KEY is not set. This skill requires Linear to give grounded suggestions — set it in your environment and try again."

If the `gh auth status` check fails or shows "not logged in", **stop immediately**:

> "GitHub CLI is not authenticated. Run `gh auth login` and try again."

Do not proceed if either check fails.

## Step 2 — Gather lightweight context (run in parallel)

```bash
# Recent commits across the whole repo, last 14 days
git log --since="14 days ago" --format="%h %s" --all | head -40

# Open PRs
gh pr list --state=open --limit=20 --json number,title,author,labels

# Recently merged PRs
gh pr list --state=merged --limit=15 --json number,title,mergedAt,author
```

Fetch in-progress and recently completed Linear tickets:
```bash
curl -s https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{"query":"query { issues(filter: { state: { type: { in: [\"started\", \"inProgress\", \"completed\"] } }, updatedAt: { gt: \"-P14D\" } }, first: 30, orderBy: updatedAt) { nodes { identifier title state { name } assignee { name } } } }"}'
```

This step is only for situational awareness (what's recently shipped, what's in flight) — it is NOT where suggestions come from. Do not derive a suggestion purely from a commit message or ticket title; use this step to know where to point the codebase exploration in Step 3.

## Step 3 — Brainstorm and verify 3 fresh feature ideas

Read `.claude/skills/architecture-meeting-suggestions/discarded-ideas.md` first (see "Memory — discarded ideas" above). Brainstorm a handful of candidate fresh feature ideas per the "Fresh feature: what counts" rules above — draw on features you know from shopping/social/delivery/streaming apps (iFood, Amazon, Instagram, TikTok, YouTube, Depop, Pinterest, etc.) that would plausibly fit a commerce app like Shopit. Skew toward variety: don't let all 3 land in the same theme (e.g. don't propose three different comment features). Drop any candidate that matches an idea already in the discarded-ideas memory, even under a different name — that's a rejected idea, not a fresh one, and keep brainstorming until you have 3 that are both confirmed-novel (below) and not previously discarded.

For each candidate, spawn a quick `Explore` agent (or grep directly if the check is trivial) against the mobile app to confirm Shopit doesn't already have it or a clear equivalent. Drop any candidate that turns out to already exist, and keep brainstorming until you have 3 confirmed-novel ideas.

## Step 4 — Explore the actual codebase for systemic suggestions (spawn Explore agents in parallel)

This is the step that actually produces the systemic suggestions. Spawn multiple `Explore` agents in parallel — do not rely on git/PR/Linear metadata alone. Cover at least these angles, adjusting targets based on what Step 2 surfaced as recently active:

**Tech debt / reuse (mobile app + convex backend)**
- Duplicated logic across features that should share an abstraction (e.g. multiple components/functions hand-rolling the same pattern instead of using an existing shared primitive)
- Structurally similar domains that diverged into different architectures for no clear reason (e.g. two features shaped the same way but one uses a global provider and the other doesn't)
- Oversized files/components that have outgrown a single responsibility
- Any duplicated-effort pattern where the same feature has to be built twice (parallel API surfaces, hand-synced trees)

**Product growth**
- Growth-loop mechanics (invite/referral, sharing, social graph) — are they instrumented end-to-end, client AND server, or does attribution get dropped somewhere?
- Re-engagement hooks (expiry reminders, restock alerts, lapsed-user nudges) — does the schema/data already support a hook that isn't wired up?
- Data captured (onboarding fields, denormalized counters) but never read downstream by any ranking/gating/notification logic

**UX / polish**
- Inconsistencies across screens introduced by recent changes
- Error and empty states on new features — built or skipped?

**QA gaps (systemic only)**
- A repeated *process* gap visible only zooming out across the whole cycle (e.g. a whole class of bug recurring across unrelated features) — not a single feature's leftover edge case

Each Explore agent should report concrete file paths and line numbers as evidence — no editorializing, just what it observed. Synthesize the actual suggestions yourself from that evidence; don't let an agent decide what's worth raising.

## Step 5 — Write 3 fresh feature ideas first, then 3-5 systemic suggestions

Each systemic suggestion must be:
- Grounded in specific file paths/line numbers from the Step 4 exploration (not just a commit message or ticket title)
- Framed as a question or observation for the team — not a unilateral decision
- Short enough to say aloud in 20-30 seconds
- Systemic (see Altitude above) — if it reads like a bug-fix reminder for one PR, cut it
- From Guilherme's angle per the focus areas above

Lead with the 3 fresh feature ideas from Step 3, in this format:

```
## Fresh feature ideas

**1. [Fresh feature] — Headline**
One sentence: what it is, which app it's borrowed from, why it'd fit Shopit.

**2. [Fresh feature] — Headline**
...

**3. [Fresh feature] — Headline**
...
```

Then, as a clearly separate block after the fresh feature ideas, list the 3-5 systemic suggestions under their own header:

```
## Systemic suggestions

**1. [Category] — Headline**
One or two sentences. Name the specific files/patterns found. Say what the observation is and why it's worth the team's attention.

**2. [Category] — Headline**
...
```

Categories: `Product growth` · `Tech debt` · `Reuse/consistency` · `Product velocity / reliability` · `UX friction` · `Polish` · `QA gap` · `Prototype idea`

## Good vs bad examples

**Good fresh feature**: "Shake-to-clear-cart — shake the phone while the cart sheet is open to clear it, like a few grocery apps use for a quick 'start over.' Cheap gesture-recognition prototype, no backend change." (named/identifiable pattern, confirmed not already in the app, small enough to prototype)
**Bad fresh feature**: "Add gamification to the app." (too vague, no named source, not concrete)
**Bad fresh feature**: "Let users filter search results by price range." (this is an obvious extension of an existing feature, not something completely new — belongs in systemic suggestions if it's worth raising at all)

**Good**: "The peer-invite loop fires from three growth surfaces but has no funnel event and no server-side referral attribution — the client captures the inviter's ID off the deep link and then never sends it anywhere. We can't answer 'how many signups came from an invite' today."

**Bad**: "We should improve the onboarding experience." (too vague, not grounded)
**Bad**: "Add more unit tests." (Wolfgang's territory, not user-facing)
**Bad**: "Did the address-sheet race-condition fix from PR #355 get applied to the checkout screen too?" (single-PR leftover, not systemic — this is a Slack message)
**Bad**: "We have a lot of self-review commits fixing bugs before merge." (that's an accepted, working process — not up for debate)
**Bad**: "We're running 3 parallel variants of the recipient-onboarding flow, is that intentional?" (if the team already knows and is fine with it, don't relitigate — only flag parallel-effort patterns if you can point to a concrete, still-open cost)

## Output

Print the suggestions directly in the response — the 3 fresh feature ideas first, then the 3-5 systemic suggestions, as two separate blocks per the formats above. No preamble, no trailing summary. Just the points, ready to speak.

Also write all of it (both blocks, fresh feature ideas first) to `/Users/guilhermereis/Desktop/clones/shopit-monorepo/arch-suggestions.md` (repo root, not `.claude/` — `.claude/` is gitignored repo-wide, and this file needs to be committable in Step 6), overwriting any previous run, using the Write tool (not printf). Then open the file with this exact command — always the same, no arguments change:

```bash
open -a TextEdit /Users/guilhermereis/Desktop/clones/shopit-monorepo/arch-suggestions.md
```

## Step 6 — Open (or update) a draft PR with the findings

Once the file is written and opened, archive the findings as a **draft** PR so they're shareable without touching `main`. Never mark it ready for review — leave it as a draft.

This is side-channel git work — a branch/commit the user didn't ask to be on — so it must run inside an isolated worktree (`EnterWorktree`/`ExitWorktree`), never as a direct `git checkout -B ...` in the shared primary working directory. A `git status` check moments earlier proves nothing about the moment the checkout actually runs — a concurrent session on the same machine/repo can switch branches or commit in that same directory in between. Physical isolation via a worktree is the only real guarantee.

**Default case — no existing PR to update**: `EnterWorktree` (creates a fresh worktree branched from `origin/main`), then inside it:

```bash
git checkout -B "arch-notes/$(date +%Y-%m-%d)"
# (the Write tool call for arch-suggestions.md happens against this worktree's path)
git add arch-suggestions.md
git commit -m "docs: architecture sync suggestions $(date +%Y-%m-%d)"
git push -u origin HEAD --force-with-lease

gh pr create --draft \
  --title "Architecture sync suggestions — $(date +%Y-%m-%d)" \
  --body-file arch-suggestions.md
```

**If the user points at an existing draft PR to update instead of creating a new one** (e.g. "update PR #624", or a PR URL passed as an argument): inside the worktree, check out that PR's existing branch instead of cutting a new one —

```bash
gh pr view <number> --repo <owner>/<repo> --json headRefName -q .headRefName
git fetch origin <headRefName>
git checkout -B <headRefName> origin/<headRefName>
# write the updated arch-suggestions.md, then:
git add arch-suggestions.md
git commit -m "docs: architecture sync suggestions $(date +%Y-%m-%d) — <short reason, e.g. 8 fresh feature ideas>"
git push origin HEAD:<headRefName>

gh pr edit <number> --repo <owner>/<repo> \
  --title "Architecture sync suggestions — $(date +%Y-%m-%d)" \
  --body-file arch-suggestions.md
```

Either way, once pushed, `ExitWorktree` with `action: "remove", discard_changes: true` — safe, since the commit already lives on the remote branch. Then delete the local root-level copy at `/Users/guilhermereis/Desktop/clones/shopit-monorepo/arch-suggestions.md` (the one written in Step 5, in the *original* working directory, not the worktree copy) — don't leave it sitting untracked on whatever branch the user returns to.

`git commit`/`gh pr create`/`gh pr edit` prefer `--body-file` over `--body "$(cat ...)"` — a command substitution around a git-adjacent command can read as "too complex to verify" inside a worktree sandbox. If a pre-commit hook needs `node` on PATH and sourcing `nvm` is blocked as unverifiable, prepend the version's bin dir directly instead: `export PATH="$HOME/.nvm/versions/node/vX.Y.Z/bin:$PATH"`. A docs-only commit can still get blocked by a repo-wide pre-commit hook (e.g. a full typecheck) failing on pre-existing, unrelated errors unconnected to `arch-suggestions.md` — `--no-verify` is fine there specifically, not as a general habit.

Report the draft PR URL in the response. This is a **docs-only** branch dedicated to notes — it's fine to force-push over a same-day rerun (when cutting a fresh dated branch) or to push a follow-up commit (when updating an existing PR's branch). Do not run this step if the *original* working directory has unrelated uncommitted changes beyond `arch-suggestions.md`; if `git status` there shows other modified/staged files, stop and tell the user instead of committing their in-progress work.

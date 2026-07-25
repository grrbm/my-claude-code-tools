---
name: architecture-meeting-suggestions
description: Generate concrete talking points for Guilherme to bring to the Monday architecture sync meeting. Use this skill whenever the user asks for meeting ideas, what to bring to architecture sync, suggestions for the Monday meeting, or what to discuss with the team this week. Explores the actual codebase (mobile app + convex backend) plus recent commits, open PRs, and Linear tickets to surface grounded, systemic observations — not invented busywork, not one-off bug fixes.
allowed-tools: Bash(git *), Bash(curl *), Bash(gh *), Bash(open *), Bash(printenv *)
---

Generate 3-5 concrete suggestions for the architecture sync meeting, grounded in what's actually in the codebase. The goal is to surface non-obvious, systemic observations the team should weigh in on — not tasks already being done, not abstract ideas, and NOT one-off bug-fix reminders (see "altitude" below).

## Guilherme's focus areas

You're building these suggestions for Guilherme, whose role is:
- **User-facing app flows** — how new users onboard, how existing users navigate, where flows break or feel incomplete
- **Prototypes** — quick experiments worth building to validate ideas before committing to full implementation
- **Product polish** — visual consistency, interaction quality, edge cases that make the product feel unfinished

Each suggestion should come from one of these angles, but don't self-censor backend/convex findings — if a backend pattern (e.g. duplicated logic, missing schema field, missing scheduled job) has a direct, nameable cost to shipping user-facing features or to product growth, it's fair game. Frame it from that impact ("every feature I ship has to be built twice"), not as generic backend architecture commentary. Avoid pure build/release/CI topics (Wolfgang's territory) or deep AI-infra internals (Jason's) with no user-facing angle.

## Altitude: what counts as a suggestion

Suggestions must be systemic — a pattern repeated across multiple features, a structural gap, or a researched should-we-or-shouldn't-we call. They must NOT be "did fix X from PR A also get applied to screen B" or any other single-PR leftover — that's a Slack message, not an architecture topic. Also do not flag things the team has already made an explicit, working call on (e.g. running multiple deliberate variants of a flow, or an accepted process like iterative self-review commits before merge) — those aren't up for debate and raising them reads as not having done the homework. If unsure whether something is settled, prefer a finding that's clearly still open.

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

## Step 3 — Explore the actual codebase (spawn Explore agents in parallel)

This is the step that actually produces suggestions. Spawn multiple `Explore` agents in parallel — do not rely on git/PR/Linear metadata alone. Cover at least these angles, adjusting targets based on what Step 2 surfaced as recently active:

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

## Step 4 — Write 3-5 suggestions

Each suggestion must be:
- Grounded in specific file paths/line numbers from the Step 3 exploration (not just a commit message or ticket title)
- Framed as a question or observation for the team — not a unilateral decision
- Short enough to say aloud in 20-30 seconds
- Systemic (see Altitude above) — if it reads like a bug-fix reminder for one PR, cut it
- From Guilherme's angle per the focus areas above

Use this format:

```
**1. [Category] — Headline**
One or two sentences. Name the specific files/patterns found. Say what the observation is and why it's worth the team's attention.

**2. [Category] — Headline**
...
```

Categories: `Product growth` · `Tech debt` · `Reuse/consistency` · `Product velocity / reliability` · `UX friction` · `Polish` · `QA gap` · `Prototype idea`

## Good vs bad examples

**Good**: "The peer-invite loop fires from three growth surfaces but has no funnel event and no server-side referral attribution — the client captures the inviter's ID off the deep link and then never sends it anywhere. We can't answer 'how many signups came from an invite' today."

**Bad**: "We should improve the onboarding experience." (too vague, not grounded)
**Bad**: "Add more unit tests." (Wolfgang's territory, not user-facing)
**Bad**: "Did the address-sheet race-condition fix from PR #355 get applied to the checkout screen too?" (single-PR leftover, not systemic — this is a Slack message)
**Bad**: "We have a lot of self-review commits fixing bugs before merge." (that's an accepted, working process — not up for debate)
**Bad**: "We're running 3 parallel variants of the recipient-onboarding flow, is that intentional?" (if the team already knows and is fine with it, don't relitigate — only flag parallel-effort patterns if you can point to a concrete, still-open cost)

## Output

Print the suggestions directly in the response. No preamble, no trailing summary. Just the points, ready to speak.

Also write them to `/Users/guilhermereis/Desktop/clones/shopit-monorepo/arch-suggestions.md` (repo root, not `.claude/` — `.claude/` is gitignored repo-wide, and this file needs to be committable in Step 5), overwriting any previous run, using the Write tool (not printf). Then open the file with this exact command — always the same, no arguments change:

```bash
open -a TextEdit /Users/guilhermereis/Desktop/clones/shopit-monorepo/arch-suggestions.md
```

## Step 5 — Open a draft PR with the findings

Once the file is written and opened, archive the findings as a **draft** PR so they're shareable without touching `main`. Never mark it ready for review — leave it as a draft.

```bash
# remember the branch we started on so we can return to it
original_branch=$(git branch --show-current)

git checkout -B "arch-notes/$(date +%Y-%m-%d)" main
git add arch-suggestions.md
git commit -m "docs: architecture sync suggestions $(date +%Y-%m-%d)"
git push -u origin HEAD --force-with-lease

gh pr create --draft \
  --title "Architecture sync suggestions — $(date +%Y-%m-%d)" \
  --body "$(cat /Users/guilhermereis/Desktop/clones/shopit-monorepo/arch-suggestions.md)"

git checkout "$original_branch"
rm /Users/guilhermereis/Desktop/clones/shopit-monorepo/arch-suggestions.md
```

Report the draft PR URL in the response. The findings live on the PR/branch now, so delete the local root-level copy once the PR is created — don't leave it sitting untracked on whatever branch the user returns to. This is a **docs-only** branch dedicated to notes — it's fine to force-push over a same-day rerun. Do not run this step if the working tree has unrelated uncommitted changes beyond `arch-suggestions.md`; if `git status` shows other modified/staged files, stop and tell the user instead of committing their in-progress work.

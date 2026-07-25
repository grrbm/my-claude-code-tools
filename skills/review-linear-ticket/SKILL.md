---
name: review-linear-ticket
description: Analyse one or more Linear tickets against the codebase, surface gaps and scope questions, then — only after explicit user approval — post the full analysis as a comment on each approved ticket. Use proactively when asked to review, check, or audit a Linear ticket (or several at once). Also triggers on phrases like "look at my ticket", "review these tickets", "what's missing from this issue", "check this Linear issue for gaps", "is this ticket ready?", or any request to evaluate or strengthen one or more Linear issues.
argument-hint: <linear-issue-url-or-identifier> [<additional-issues>...]
allowed-tools: Bash(curl *), Bash(grep *), Bash(find *), Bash(git *), Read, Glob, Grep
---

Analyse the Linear ticket(s): $ARGUMENTS

---

## Before you start

Parse `$ARGUMENTS` into a list of distinct issue identifiers (e.g. `SHO-368`, `SHO-370`, `SHO-372`). Tickets may arrive as URLs or bare identifiers, separated by spaces, commas, or newlines — extract the identifier from each. De-duplicate the list.

If the list is empty (no recognisable Linear URL or identifier), ask the user:

> "Which Linear ticket(s) should I review? Please share the URL(s) or identifier(s) (e.g. SHO-368), separated by commas or spaces."

Then wait. Do not proceed until you have at least one.

If there's more than one ticket, briefly confirm the batch before diving in, e.g. "Reviewing 3 tickets: SHO-368, SHO-370, SHO-372." so the user can catch a mis-parsed identifier early.

---

## Phase 1 — Analysis (runs automatically)

### Step 1 — Authenticate

Try `$LINEAR_API_KEY` first. If it is empty or unset, read it from the env file:

```bash
grep '^LINEAR_API_KEY=' /Users/guilhermereis/Desktop/clones/shopit-monorepo/.env.local | tail -1 | cut -d'=' -f2
```

Use whichever value you find in every subsequent `Authorization` header. Never print the key. Authenticate once — the same key covers every ticket in the batch.

### Steps 2–5 — For each ticket, in order

Run the following steps independently for every ticket in the list, one at a time. Each ticket gets its own fetch, its own codebase research, and its own report — don't let findings from one ticket bleed into another's analysis. Keep track of each ticket's UUID (from Step 2) for later, since Phase 2 needs it.

### Step 2 — Fetch the ticket

Parse the issue identifier from the URL or argument (e.g. `SHO-368`). Fetch full details including comments, priority, estimate, and labels — they all inform the analysis:

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: <key>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ issue(id: \"<IDENTIFIER>\") { id identifier title description priority estimate state { name } assignee { name } labels { nodes { name } } comments { nodes { body createdAt user { name } } } } }"
  }'
```

Read every comment — they often contain the most current requirements and scope clarifications that supersede the original description.

### Step 3 — Research the codebase

Based on the ticket's problem statement, acceptance criteria, and any "likely files" section:

- Locate each mentioned file or directory and read the relevant sections.
- Search for related symbols, routes, hooks, components, mutations, or validators using `Grep` or `grep -r`. Don't just trust the ticket's file list — verify it.
- Cross-check any factual claims: if the ticket says "file X already handles Y", check whether it actually does.
- Look for sibling patterns (similar features or flows) elsewhere in the codebase that give context on how this work should be structured.
- Check recent git history for the affected area to understand current state and recent changes:
  ```bash
  git log --oneline -10 -- <path>
  ```

Be thorough. Your goal is to know what is *actually* true in the codebase, not what the ticket assumes.

### Step 4 — Identify gaps

Evaluate the ticket against these dimensions:

- **Acceptance criteria** — are they testable and specific? Are edge cases and failure paths covered?
- **Scope boundary** — is the line between in-scope and out-of-scope clear? Are implicit dependencies stated?
- **Technical accuracy** — does the ticket assume things about the codebase that aren't true?
- **Test / QA path** — are manual test steps concrete enough? Do they cover error and edge states, not just the happy path?
- **Data / state model** — are schema, migration, or validator implications (e.g. Convex schema changes) mentioned?
- **Error & edge states** — are network failures, missing data, permission mismatches, and loading states addressed?
- **Non-goals** — are there omissions that could cause confusion or scope creep during implementation?

### Step 5 — Output the analysis report

Present findings for this ticket using this exact structure, then move on to the next ticket in the batch. Do not post anything to Linear yet.

---

```
## Ticket Analysis: <IDENTIFIER> — <title>

### What's well-defined ✅
<Brief bullets on parts of the ticket that are clear and actionable.>

### Gaps & ambiguities ⚠️
<Numbered list. For each gap: what's unclear, why it matters, and what the ticket should say instead.>

### Questions for your team ❓
<Numbered list of concrete questions to ask collaborators or stakeholders.
 Focus on things only a human can answer — product intent, business rules, priority tradeoffs.>

### Scope suggestions 🔭
**Consider adding:**
<Bullet list of things worth including that the ticket omits.>

**Consider removing / deferring:**
<Bullet list of things that are likely out of scope or better as a separate ticket.>

### Codebase findings 🔍
<Factual corrections or context from your research — e.g. "the ticket says X is already implemented, but file Y shows it is not", or "the likely-files list is missing Z which handles this concern". If everything checked out, say so.>
```

---

Repeat Steps 2–5 for every remaining ticket before asking about posting — the user should see the full batch of reports together, not be interrupted per-ticket.

Once every ticket's report has been shown, ask exactly:

> **Shall I post these analyses as comments? Reply with `all`, `none`, or the specific identifiers to post (e.g. "SHO-368, SHO-372").**

(If there was only one ticket in the batch, this still works fine as a yes/no question.)

**Stop here. Do not post anything to Linear until the user explicitly responds.**

---

## Phase 2 — Post comments (only after explicit user approval)

This phase runs only when the user has **explicitly approved** posting for at least one ticket (e.g. "go ahead", "yes", "all", "post it", "just SHO-368").

"Looks good" or "sounds right" without clear forward direction is **not** approval — ask once to confirm before proceeding. If the user names a subset, post only to those tickets and leave the rest untouched.

### Step 6 — Post each approved ticket's analysis as a Linear comment

Process the approved tickets one at a time. For each one, use its issue UUID from Step 2 (not the `SHO-NNN` identifier — the UUID is the long hex string in the `id` field) and post the entire analysis report (all five sections) as a comment:

```bash
LINEAR_KEY="<key>"
COMMENT=$(cat <<'EOF'
<full analysis markdown — all five sections exactly as shown to the user>
EOF
)
ESCAPED=$(echo "$COMMENT" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))")

curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"mutation CreateComment(\$issueId: String!, \$body: String!) { commentCreate(input: { issueId: \$issueId, body: \$body }) { success comment { id url } } }\",
    \"variables\": { \"issueId\": \"<UUID>\", \"body\": $ESCAPED }
  }"
```

Each `curl` call still has to happen one at a time (Linear's API doesn't batch comment creation), but don't narrate each one as it happens — the user asked to see the outcome once posting is fully done, not a drip of confirmations interleaved with other output. Silently record each ticket's outcome (posted + URL, or failed + error) as you go, then once every approved ticket has been attempted, print one consolidated report so the user can check off what actually landed:

```
## Posted to Linear

| Ticket | Status | Link |
|---|---|---|
| SHO-368 | ✅ Posted | <comment URL> |
| SHO-372 | ✅ Posted | <comment URL> |
| SHO-370 | ⏭️ Not approved — skipped | — |
| SHO-375 | ❌ Failed — <short error> | — |
```

Include every ticket from the original batch in this table, not just the approved ones — that's what makes it useful as a single place to check what happened to each ticket.

---

## Rules

- **Phase 1 never posts to Linear.** Analysis and reporting only, for every ticket in the batch.
- **One explicit gate before any mutation**: user responds → post comments only to the approved subset.
- **Report posting results once, at the end, as a single table covering the whole batch** — not as per-ticket confirmations scattered through the output.
- Always use the UUID for mutations, never the `SHO-NNN` identifier.
- Escape the comment body as a valid JSON string before embedding in GraphQL variables.
- If a ticket has no meaningful gaps, say so honestly — never invent issues to fill its report.
- If authentication fails, print the exact error and stop — this applies to the whole batch, since all tickets share one key.
- If fetching or analysing one ticket fails (bad identifier, API error), report that failure clearly and continue with the rest of the batch rather than aborting everything.

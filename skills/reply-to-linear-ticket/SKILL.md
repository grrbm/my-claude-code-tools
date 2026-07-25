---
name: reply-to-linear-ticket
description: Read a Linear issue's full description and entire comment thread, find open questions or pending decisions in the discussion, research the codebase to form a real evidence-backed answer, and draft a reply comment that resolves them — posting only after explicit approval. Use whenever asked to reply to a Linear ticket, answer open questions on an issue, respond to a discussion thread, weigh in on a decision someone is waiting on, or contribute to a Linear conversation. Triggers on phrases like "reply to this linear ticket", "answer the open questions on SHO-XXX", "what should I tell them on this issue", "help me respond to this thread", "can you weigh in on this ticket".
argument-hint: <linear-issue-url-or-identifier>
allowed-tools: Bash(curl *), Bash(grep *), Bash(find *), Bash(git *), Read, Glob, Grep
---

Reply to the Linear ticket: $ARGUMENTS

---

## Before you start

If `$ARGUMENTS` is empty or doesn't contain a recognisable Linear URL or issue identifier (like `SHO-372`), ask the user:

> "Which Linear ticket should I reply to? Please share the URL or identifier (e.g. SHO-372)."

Then wait. Do not proceed until you have one.

---

## Phase 1 — Find open questions & draft a reply (runs automatically)

### Step 1 — Authenticate

Try `$LINEAR_API_KEY` first. If it is empty or unset, read it from the env file:

```bash
grep '^LINEAR_API_KEY=' /Users/guilhermereis/Desktop/clones/shopit-monorepo/.env.local | tail -1 | cut -d'=' -f2
```

Use whichever value you find in every subsequent `Authorization` header. Never print the key.

### Step 2 — Fetch the issue and every comment

Parse the issue identifier from the URL or argument (e.g. `SHO-372`). Fetch the full thread in one request — you need the issue UUID (`id`) for posting later, not just the human-readable identifier:

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: <key>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ issue(id: \"<IDENTIFIER>\") { id identifier title description priority estimate state { name } assignee { name } labels { nodes { name } } comments { nodes { id body createdAt user { name } } } } }"
  }'
```

Read the description and every comment, in chronological order. The discussion is the source of truth — later comments often supersede the original description.

### Step 3 — Identify open questions and pending decisions

Walk the description and comment thread looking for things that are genuinely still unresolved:

- Direct questions ("should we do X or Y?", "@someone, thoughts on Z?")
- Stated uncertainty ("not sure if...", "TBD", "need to confirm...")
- A choice between approaches that nobody has committed to yet
- A blocker that's explicitly waiting on someone's input or a decision
- A claim or assumption flagged for verification (e.g. "⚠️ verify")

For each one, note who raised it, when, and the exact wording — you'll need to address it precisely, not just in the abstract.

Check whether any of these were already answered later in the thread (people sometimes answer their own questions, or someone replies further down) — don't re-raise something that's already settled.

If, after this pass, there are no genuinely open questions or pending decisions, say so honestly and stop here. Do not invent a question to answer just to have something to post.

### Step 4 — Research the codebase to form real answers

For each open question that touches the codebase (as most engineering questions will), go find out what's actually true rather than guessing or reasoning from the ticket text alone:

- Locate the relevant files, functions, schemas, or routes and read them.
- Search for related patterns elsewhere in the codebase (`Grep`, `grep -r`, `find`) to see how similar decisions were made before — consistency with existing patterns is usually the strongest argument for a recommendation.
- Check git history for the affected area to understand recent changes or prior intent:
  ```bash
  git log --oneline -10 -- <path>
  ```
- Verify any factual claims in the thread against the current code — people often discuss a file from memory and get the current state wrong.

Some questions will be pure product/business judgment that no amount of code-reading will resolve (pricing decisions, UX tradeoffs, priority calls). For those, give your best-reasoned recommendation but flag clearly that it's a judgment call, not something you verified.

### Step 5 — Draft the reply comment

Write a single comment that addresses every open question/decision found in Step 3. For each one:

- State the question being answered (so the reply reads coherently without needing the full thread open).
- Give your answer or recommendation.
- Back it with concrete evidence where you have it — file path, function name, or current behavior (`file.ts:42` style references read well in Linear).
- If it's a judgment call rather than a verified fact, say so plainly rather than presenting it with false confidence.

Keep the tone like a teammate replying inline — direct and specific, not a formal report. Use markdown formatting (bullets, code spans) consistent with how comments already read in the thread.

### Step 6 — Show the draft

Present to the user:

```
## Open questions found on <IDENTIFIER> — <title>

1. <question, who asked, when>
2. <question, who asked, when>
...

## Drafted reply

<the full comment markdown exactly as it would be posted>
```

Then ask exactly:

> **Shall I post this reply as a comment on <IDENTIFIER>?**

**Stop here. Do not post anything to Linear until the user explicitly says yes.** "Looks good" or "sounds right" without clear forward direction is not approval — ask once more to confirm before proceeding.

---

## Phase 2 — Post comment (only after explicit user approval)

This phase runs only when the user has **explicitly approved** posting (e.g. "go ahead", "yes", "post it", "do it").

### Step 7 — Post the reply as a Linear comment

Use the issue UUID from Step 2 (the long hex string in the `id` field) — never the `SHO-NNN` identifier:

```bash
LINEAR_KEY="<key>"
COMMENT=$(cat <<'EOF'
<full drafted reply markdown exactly as shown to the user>
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

Confirm success and print the comment URL returned by Linear.

---

## Rules

- **Phase 1 never posts to Linear.** Finding questions and drafting a reply only.
- **One explicit gate before any mutation**: user says yes → post comment.
- Always use the UUID for mutations, never the `SHO-NNN` identifier.
- Escape the comment body as a valid JSON string before embedding in GraphQL variables.
- Never answer a question with a guess dressed up as fact — verify against the codebase, and clearly label pure judgment calls as such.
- If there are no genuine open questions or pending decisions, say so honestly — never manufacture one to fill a reply.
- If authentication fails, print the exact error and stop.

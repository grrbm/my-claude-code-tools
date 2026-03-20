# Log Work to Memory

Trigger:
Automatically — after completing any meaningful unit of work during a conversation.

Behavior:
Save a `project` type memory entry describing what was just done, so it can be recalled later in "what did i do today" summaries.

When to save:
- After finishing or making significant progress on a feature or bug fix
- After addressing PR review feedback
- After creating or merging a PR
- After completing a Linear task or a significant chunk of one

What to save:
- A plain-English description of what was done (no jargon, no file paths)
- The Linear issue it relates to (if any)
- Today's date (use the `currentDate` from context)

Format (use `project` memory type):

```
What was done, in plain English.

**Why:** The Linear issue or reason behind the work.
**How to apply:** Use this for daily standup / end-of-day summary.
```

Rules:

- Save after the work is done, not before.
- Keep it brief — one or two sentences max.
- Do not save ephemeral or in-progress notes; only save completed work.
- Do not save the same work twice.

---

# What Did I Do Today

Trigger:
When I ask something like:

what did i do today
what have i worked on today
summarize my day
what did we do today

Behavior:
Read Claude memory to reconstruct what was worked on today, then give a short, plain-English summary — no technical jargon.

Workflow:

1. Get today's date from the environment.

2. Read all memory files in the project memory directory:
   `/Users/guilhermereis/.claude/projects/-Users-guilhermereis-Desktop-clones-shopit-monorepo/memory/`

3. Look for any `project` type memories logged today (check dates in the memory content).

4. Check for any uncommitted changes or work in progress as a supplement:
   `git status` and `git diff --stat`

5. Synthesize into bullet points describing what was worked on — as if explaining to a non-technical friend or writing a standup note.

Rules:

- Use bullet points — one bullet per meaningful area of work.
- No technical terms, no function names, no file paths, no jargon.
- Focus on the "what" and "why" from a product/feature perspective, not implementation details.
- Only report work that I (the user) did — not other contributors.
- If memory is empty or has nothing for today, say so honestly rather than falling back to git log.
- If nothing was committed yet but there are changes in progress, mention that too.
- Never mention the `new-apis-examples/` folder or any untracked folders that are clearly experiments/scratch work.

Example output:

- Added an automatic cleanup job that removes stale gift orders that got stuck during checkout
- Set up a PR for it and got it reviewed

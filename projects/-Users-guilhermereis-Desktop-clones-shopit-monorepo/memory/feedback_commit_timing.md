---
name: Don't commit without explicit instruction
description: Never create git commits unless the user explicitly says to commit
type: feedback
---

Do not commit changes unless the user explicitly asks. Always leave changes uncommitted until instructed.

**Why:** User wants control over when commits are created — committing proactively was unwanted.

**How to apply:** After implementing changes, stop before `git commit`. Only run commit commands when the user says "commit", "commit this", or similar explicit instruction.

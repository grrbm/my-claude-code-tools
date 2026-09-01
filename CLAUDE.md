# Global Claude Rules

These rules apply to all projects unless explicitly overridden.

@.claude/ai/git-conventions.md
@.claude/ai/memory.md
@.claude/ai/test-rule.md
@.claude/ai/design-system.md
@.claude/ai/no-use-effect.md
@.claude/ai/keyboard-overlap.md

## Package manager

This repo uses **bun** as the package manager. Use `bun run <script>` to run scripts.

## Typechecking

Run `bun run type-check` from the repo root — it runs `turbo type-check` across all packages.

To check a specific package only (faster): `cd packages/convex && bun run type-check` or `cd apps/mobile && bun run type-check`.

Pre-existing type errors exist in unrelated files (shared exports, discovery.ts, etc.); only treat errors in files you edited as regressions.

## node_modules

Never read files inside `node_modules/`. If you would have read a file there, say so explicitly ("I would have read X in node_modules — let me know if you want me to") and stop. The user will decide.

## locked components

If you think you need to change any locked components, mention it, but DONT change the components unless the explicit bypass phrase is said.

## iOS Simulator

Never check the simulator screen (screenshot, describe, or otherwise look at what's on screen) unless the user explicitly asks you to. This applies even when verifying a UI change — do not proactively launch a `run` or `screenshot-screen` skill/check to "confirm" something looks right; ask the user or wait for them to request it.

## Test accounts for two-user flows

Whenever you need to test anything that happens between two users — sending a gift, friend / follow requests, notifications on the receiving side, shared wishlists, etc. — two dev accounts already exist. Their credentials live in `packages/convex/.env.local`:

- `DEV_ACC_1_EMAIL` / `DEV_ACC_1_PASS`
- `DEV_ACC_2_EMAIL` / `DEV_ACC_2_PASS`

Sign in with them through the dev-only "Continue with email" button on the auth sheet (visible in `__DEV__` builds only). Don't paste these values into chat, commits, PRs, or any file outside `.env.local`.

## Auto-approving Write outside the project root (e.g. /private/tmp)

`Write(path)` rules in `permissions.allow` and `defaultMode: "acceptEdits"` only apply to files **within the project root**. Writing to `/private/tmp` or any path outside the repo will always prompt unless you do two things in `settings.local.json`:

1. `"defaultMode": "acceptEdits"` — auto-approves all Write/Edit calls within scope
2. `"additionalDirectories": ["/private/tmp", "/tmp"]` — extends the trusted scope to include those directories

Without `additionalDirectories`, even an exact-match `Write(/private/tmp/pr-review.md)` rule is ignored for out-of-root paths. Both keys must be set together.

Note: on macOS `/tmp` is a symlink to `/private/tmp` — add both to be safe.

## No AI attribution in commit messages

Never add `Co-Authored-By: Claude ...`, `Generated with Claude Code`, a session trailer, or any other assistant-identity attribution to a commit message — including in `implement-multiple-reviews`/`implement-self-review`-style skill commits. This repo has a required CI gate ("No assistant attribution") that scans every commit message in a PR and fails the check if it finds one, blocking merge. Authorship belongs to the human contributor.

If a commit with this trailer has already been pushed: amend it (`git commit --amend`, or an interactive rebase if it isn't the tip) to strip the trailer, then force-push — confirm with the user first, since force-push rewrites shared history.

## PermissionRequest hook output format

When writing a `PermissionRequest` hook to auto-allow a command, the correct output format is:

```json
{"hookSpecificOutput":{"hookEventName":"PermissionRequest","decision":{"behavior":"allow"}}}
```

**Common mistake:** using `"permissionDecision": "allow"` at the top level of `hookSpecificOutput` — that is the `PreToolUse` format and will be silently ignored by `PermissionRequest`, causing the dialog to still appear.

The two formats side by side:

```jsonc
// PermissionRequest hook — use "decision": { "behavior": "allow" }
{"hookSpecificOutput":{"hookEventName":"PermissionRequest","decision":{"behavior":"allow"}}}

// PreToolUse hook — use "permissionDecision": "allow"
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow"}}
```

Check the official docs for the latest schema — the format may change across Claude Code versions:
https://code.claude.com/docs/en/hooks

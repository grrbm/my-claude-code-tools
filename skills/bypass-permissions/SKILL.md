---
name: bypass-permissions
description: Check and toggle Claude Code's bypassPermissions mode — the permission-mode setting (`permissions.defaultMode`) that skips ALL tool-permission prompts, including destructive ones. Use this whenever the user runs `/bypass-permissions`, or asks things like "am I in bypass permissions mode", "check my permission mode", "turn off/on dangerous mode", "toggle full auto", "disable permission prompts", or otherwise wants to inspect or flip Claude Code's defaultMode / bypassPermissions setting. Always report the current state first and ask before changing anything — never toggle this on your own initiative outside of this explicit skill.
---

# bypass-permissions

Reports whether Claude Code's `bypassPermissions` mode is currently active, then — only if the
user confirms — flips it to the opposite state. This setting is a real security boundary (it skips
tool-permission prompts entirely, including for destructive actions like `rm -rf` or force-push),
so treat every step as something to show the user, not something to do quietly.

## Step 1 — Determine the current effective mode

`permissions.defaultMode` can be set in three places. Precedence (highest wins) is:

1. **`.claude/settings.local.json`** (project-local, personal/machine-specific overrides)
2. **`.claude/settings.json`** (project-shared, usually checked into git)
3. **`~/.claude/settings.json`** (user-level, applies to every project)

Read all three that exist (skip ones that don't) with the Read tool, and find `permissions.defaultMode`
in each. Valid values are `"default"`, `"acceptEdits"`, `"plan"`, and `"bypassPermissions"`. The
**effective mode** is whichever value is set in the highest-precedence file that has it set at all.
If none of the three files set it, the effective mode is Claude Code's built-in default: `"default"`
(full permission prompts for everything).

## Step 2 — Report it clearly

Tell the user, in plain terms:
- The effective mode right now, and which file it's coming from (or "not set anywhere — defaulting
  to full permission prompts" if none set it).
- If a *lower*-precedence file sets a different value than the effective one, mention it briefly so
  the user isn't confused later (e.g. "note: `.claude/settings.json` also sets this to `acceptEdits`,
  but that's overridden by `settings.local.json`").
- If the effective mode is `bypassPermissions`, say plainly that no tool call is currently being
  confirmed with the user, including destructive ones.

## Step 3 — Ask before changing anything

Use `AskUserQuestion` to confirm switching to the opposite state. Phrase it based on the current state:

- **Not currently bypassPermissions**: ask whether to turn it ON, and say explicitly what that means
  ("this disables all tool-permission prompts, including for destructive actions, until you turn it
  back off").
- **Currently bypassPermissions**: ask whether to turn it OFF (back to normal prompting).

Give a clear yes/no choice (plus the automatic "Other" the tool provides). If the user declines,
stop here — report that nothing was changed.

## Step 4 — Apply the change (only after confirmation)

Always write to **`.claude/settings.local.json`** in the current project — that's the file this
skill manages, since it's already the highest-precedence file and matches how this kind of local
tool-permission config is conventionally handled per this project's own `CLAUDE.md`. Never edit
`.claude/settings.json` or the user-level `~/.claude/settings.json` as part of this skill — if the
effective mode is actually coming from one of those (because `settings.local.json` doesn't set
`defaultMode` at all), writing to `settings.local.json` will still correctly take precedence; just
say so in your confirmation message so it's not a surprise.

Use the Edit tool for a **targeted, minimal diff** — find the existing `"defaultMode": "..."` line (or
the `"permissions": {` block if the key doesn't exist yet) and change only that, rather than rewriting
the whole file. This file often has a long list of unrelated permission rules; don't touch them.

### Always: keep the hard-deny safety net in place

Explicit `permissions.deny` entries still block a matching command even when `defaultMode` is
`"bypassPermissions"` — deny is checked first regardless of mode. So every time this skill writes to
`settings.local.json` (turning on **or** off), also make sure `permissions.deny` contains at least
these entries, merging them in without touching or removing any other deny rules already there and
without adding duplicates:

```json
"deny": [
  "Bash(rm -rf *)",
  "Bash(git push --force*)",
  "Bash(git push -f*)",
  "Bash(git reset --hard*)",
  "Bash(git clean -f*)",
  "Bash(git branch -D*)"
]
```

This is a permanent floor, not something tied to the current toggle state — it should end up present
whenever this skill has touched the file, so that even a future `bypassPermissions` session (including
ones started before this skill runs again) can't casually wipe the working tree or force-push. If you
add any of these entries, mention it briefly in the Step 5 confirmation.

**Turning ON:**
1. Note whatever `defaultMode` is currently set to in `settings.local.json` right now (or `"default"`
   if the key isn't present there) — this is the value to restore later.
2. Set `permissions.defaultMode` to `"bypassPermissions"`.
3. Add a sibling key `permissions._bypassPermissionsPriorMode` set to the value from step 1. This is
   a plain, harmless custom field (Claude Code ignores unrecognized keys) that lets a future run of
   this skill restore the exact prior mode instead of guessing.
4. If `.claude/settings.local.json` doesn't exist yet in this project, create it with a minimal valid
   structure: `{"permissions": {"defaultMode": "bypassPermissions", "_bypassPermissionsPriorMode": "default"}}`.

**Turning OFF:**
1. Look for `permissions._bypassPermissionsPriorMode` in `settings.local.json`.
   - If present: restore `defaultMode` to that value, then remove the `_bypassPermissionsPriorMode` key.
   - If absent (e.g. bypassPermissions was turned on some other way, not through this skill): fall
     back to `"acceptEdits"`, and say clearly in your confirmation that this is a fallback guess, not
     a restored prior value, in case the user wants something else.

## Step 5 — Confirm what changed

State the before → after value plainly (e.g. `defaultMode: "acceptEdits" → "bypassPermissions"`), and
which file was edited. If this project's `CLAUDE.md` says to stage `.claude/settings.local.json`
alongside commits (this one does), remind the user of that so the change doesn't get left out of their
next commit — but don't stage or commit anything yourself.

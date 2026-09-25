---
name: video-demo-feature
description: Drive the iOS Simulator through a feature the way a user would, record it as a video with a timestamp log, then send it to LaunchReel (MCP) to get captions and a voiceover. Use when asked to "record a demo video of X", "video-demo-feature", "demo this PR on the simulator with voiceover", or to show a feature working end to end as a narrated video. Works from a PR URL, a Linear ticket, or a plain-English list of steps. Produces an editable LaunchReel composition, not an exported MP4.
argument-hint: <pr-url | feature description> [steps to perform]
---

Record a narrated demo video of: $ARGUMENTS

The whole job: get the app onto the right branch and running, script the steps in one Python process (no
turn-by-turn tapping), record the simulator, work out when each thing happens *from the video itself*, then
call the LaunchReel MCP with timed segments so it adds captions and a voiceover.

Scripts live next to this file in `scripts/` (call it `$SKILL`):
- `lib.py` – simulator/agent-device helpers, `mark()`, `recording()`. Import it from the flow script.
- `flow_example.py` – the real PR #675 flow (sign-up, name, email, shipping address, use my location). Copy it.
- `review.py` – `compress`, `info`, `scenes`, `frames`, `finish` (writes `timestamps.txt` and `subtitles.srt`).

## Step 0 — Understand what to show

Read the PR (`gh pr view`), its "How to manually test this" section, and any steps the user gave. Write down the
ordered list of on-screen states that prove the feature: the start state, each action, and what the viewer must
see (e.g. "names already filled in", "sheet stays above the keyboard"). Note anything that cannot be shown and say
so in the final report instead of faking it (see *Things that cannot be demoed*).

If a design or a Linear ticket is referenced, check its comments too.

## Step 1 — Bring the environment up (in this order)

1. On the PR branch: `gh pr checkout <n>` (unrelated uncommitted changes: leave them, never switch on a dirty tree).
2. **Convex**: `ps aux | grep "convex dev"`. If a watcher is already running (the user's terminal usually has one),
   leave it. Run exactly one, never a second one or `convex dev --once` beside it.
3. **Metro**: `lsof -nP -iTCP:8081 -sTCP:LISTEN`. If something already serves this repo, **reuse it**; starting
   another prints "Use port 8082 instead?" and exits in a non-interactive shell.
4. **Simulator**: only the **iPhone 16e** (`xcrun simctl list devices booted`); boot it if needed. Never use whichever
   device happens to be booted.
5. **App build**: launch it and look. A red screen saying `[runtime not ready]: ReferenceError: Property
   'MessageQueue' doesn't exist` means the installed native binary is older than the JS (for example built before an
   Expo SDK bump). Rebuild natively and reuse Metro:
   `cd apps/mobile && bunx expo run:ios --device <udid> --no-bundler` (takes several minutes; run it in the
   background). That installs bundle id **`mobile.shopit.store`**; the older `mobile.shopit.store.dev` may still be
   installed and stale. Use whichever the build printed as "Opening on iPhone 16e (…)".
   - Put NVM node on PATH (`~/.nvm/versions/node/v22.22.3/bin`, plus `~/.bun/bin`); this shell has no `node` by default
     and both `pod install` and the git pre-commit hook fail without it.
   - Xcode 26.3 cannot build `expo-modules-jsi@57.1.x` (Swift 6 "sending 'resultPtr' risks causing data races",
     7 errors). Xcode 27 builds it fine. Do not patch node_modules; upgrade Xcode.
6. **agent-device**: `agent-device open <bundle> --platform ios --device "iPhone 16e" --foreground`.

## Step 2 — Reset state off camera

- **Location** (the app is US-only, so fake a US point): `xcrun simctl location <udid> set 37.3349,-122.0090`
  (Apple Park; also 37.4220,-122.0841 for the Googleplex). A real Brazil location gives "couldn't find a U.S.
  address". A VPN does not change device location.
- **Permission prompts**: `xcrun simctl privacy <udid> reset location <bundle>` so the system alert shows again.
  Once "Allow" was chosen it never reappears by itself.
- **Signed out start**: `lib.sign_out()` (Home → Open profile → Open settings → Sign out → confirm "Sign Out").
- **Fresh account**: sign-in is by phone number and a real SMS is impossible. Clerk dev instances accept fictional
  numbers `+1 (xxx) 555-0100` … `0199` with the fixed code **424242**, so enter e.g. `2015550103`.
  **A number that already signed up signs into its old account**, which already has name, email and address, so
  those sheets never appear. Use a new number per take and keep a note of the ones used
  (used so far on the dev backend: 0100 and 0102 fully set up with name, email and address; 0101 created but
  stopped at the name sheet, so it has no name). Each successful take creates a real user on the shared dev
  Convex deployment; mention that in the report.
- The dev-only "Continue with email" button (DEV_ACC_1/2 accounts in `packages/convex/.env.local`) was not on the
  add-to-cart sign-in sheet. Do not paste those credentials anywhere.

## Step 3 — Write the flow script, dry-run it, then record

Copy `scripts/flow_example.py` next to your work dir and rewrite the steps. Rules that made the difference:

- **One process, whole flow.** The first attempt driven turn by turn was 6 min 54 s and 141 MB with long dead
  stretches; the scripted take was 1 min 36 s. Investigate and fix problems *before* the recorded take.
- **Dry-run first**: `DEMO_NO_RECORD=1 python3 flow.py` shakes out labels without recording. (It still drives the
  app, so it consumes a fresh account/phone number and changes state; reset before the real take.)
- **Re-snapshot before every tap.** Refs (`@e12`) are renumbered whenever the screen changes, notably when the
  keyboard appears. `lib.tap` and `lib.fill` already do this.
- **`fill` right after a screen change often fails** ("no text input found"). `lib.fill` focuses the field first
  and retries.
- **Unlabeled fields gain a label once filled.** After filling field 0 with "Jane" the last-name field is the only
  unlabeled one, so it is index 0 again.
- **Kind `other` elements are pressable** (`Save & Continue`, `Add to Cart`). A first tap right after the keyboard
  opens can miss, so loop until the expected next state appears.
- **`wait_for` the next state**, never just sleep. `Cart, 1 item` is disabled until sign-in finishes.
- **The first backdrop tap only dismisses the keyboard**; a sheet with the keyboard up did not close on further
  taps. To abandon a sheet, relaunch the app (`xcrun simctl terminate` then `agent-device open`) and sign out.
- **System alerts** (location, etc.) are reachable through agent-device; `Allow While Using App` is a button.
- `recording()` always stops the recorder, even if a step raises. A failed take leaves a partial file: **delete it**
  (`raw.mp4 marks.tsv start.epoch end.epoch`) and reset state before the next take.
- If a step reveals a real bug, stop recording and fix it (typecheck, `biome check`, tests) before re-recording,
  same rule as `do-all-manual-testing` Step 5. Never film over a known bug.
- **Never complete a payment.** Stop when the Stripe sheet ("Pay US$ …", TEST badge) appears.

Run it: `DEMO_DIR=<out dir> python3 flow.py`. Everything is written to `$DEMO_DIR`.

## Step 4 — Work out the video timeline (do not trust the marks)

`marks.tsv` is only an action log. It is written *before* each action (a snapshot takes 1–5 s) and the wall clock
it uses drifted up to ~5 s from the video by the middle of the run (idle frames seem to be dropped), even though
start and end matched. Captions built from marks were visibly early. So:

```bash
export DEMO_DIR=<out dir>
python3 $SKILL/scripts/review.py compress        # raw.mp4 -> demo.mp4 (~1.6 MB instead of ~90 MB)
python3 $SKILL/scripts/review.py scenes          # video times where the screen changes
python3 $SKILL/scripts/review.py frames 3.4 28.7 64.4 ...   # labelled montage -> frames.png; Read it
```

Match each visible change to an event, then write `segments.json` as `[[start, end, "text"], …]` on the **video**
timeline, one segment per step, no gaps needed, no overlaps. Also check the frames actually show what you claim
(keyboard up with the sheet above it, prefilled names, the filled address, the final sheet).

Caption text: plain sentences, spoken aloud by a TTS voice, so avoid symbols and write numbers as words.
Budget about **2.7 words per second** of segment length; a line longer than its slot overruns the next one.
`review.py finish segments.json` checks this, the ordering and the video length, then writes `timestamps.txt`
and `subtitles.srt`.

## Step 5 — Send to LaunchReel

The LaunchReel MCP (`mcp__launchreel__*`; source and README in `~/Downloads/mcp-server`) is a deferred tool: load
its schemas with ToolSearch first (`select:mcp__launchreel__create_video_composition,mcp__launchreel__list_voices`).

`create_video_composition({ video_path: <demo.mp4>, title, segments: [{start, end, text}, …] })`
- Omit `clips` to keep the whole video; segment times are on the edited timeline, which equals the video timeline
  when there are no clips.
- Default voice is `en_US-ryan-medium`; `list_voices` shows others.
- It uploads the video to a third party and **charges 5 credits + 2 per segment** to the user's LaunchReel account.
  The user asked for this by invoking the skill, but state the cost in the report. Upload the compressed
  `demo.mp4`, and make sure nothing sensitive is on screen (dev accounts only, fictional numbers).
- The result is an editable composition (`editorUrl`), **not an exported MP4**. There is no export tool; the user
  exports from the editor.
- `edit_video_composition` replaces the whole composition and re-charges credits; edits the user made in the editor
  are lost. Tell the user to review timing in the editor first and only re-run for big changes.

## Step 6 — Report

Finish with: the editor URL and credits charged; what was shown and confirmed on screen; what was **not** verified;
test accounts/phone numbers created on the shared dev backend; the absolute paths of every file written
(`demo.mp4`, `raw.mp4`, `timestamps.txt`, `subtitles.srt`, `segments.json`, `marks.tsv`); and anything left
uncommitted. Do not edit the PR body or post a comment with the video unless the user asks; once they export, the
`report-with-videos` / `post-screenshots-to-pr` skills cover getting media into a PR.

## Things that cannot be demoed here

- **ATT (App Tracking Transparency)**: `requestTrackingPermission*` return immediately when `__DEV__` is true, so
  no dev build ever shows the dialog. Needs a Release build or TestFlight (also needs the Tracking setting on).
- **QWERTY keyboard on a fresh field**: the simulator here is headless (this Xcode 27 install has no
  `Simulator.app`, so `open -a Simulator` and the Toggle Software Keyboard menu are unavailable) and behaves as if a
  hardware keyboard is attached. The number pad shows at once, but the QWERTY keyboard only appears after you type
  into a field. Type a character before filming a keyboard-overlap check.
- **Real device location / push / anything needing SMS**: not reproducible on the simulator.

## Rules (from CLAUDE.md that apply)

- iPhone 16e simulator only. Looking at the simulator screen is fine here because the user asked for a demo.
- No AI attribution in any commit message; never add a `SHO-` number if the user says not to.
- Never read files inside `node_modules/`; say what you would have read and stop.
- Do not create or commit anything unless asked. All output goes to a scratch/out dir, not the repo.
- Locked components (`MultiStepBottomSheet`, `BottomSheetKeyboardFixed`, …) are never edited without the exact
  bypass phrase, even if the demo exposes a bug in one; report it.

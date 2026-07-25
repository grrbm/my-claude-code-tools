---
name: screenshot-screen
description: Navigate to a specific screen or UI element in the booted iOS simulator and take a screenshot. Use when asked to screenshot something specific in the app, like "the name prompt in checkout" or "the CartSheet gift flow". Also handles batch screenshot runs (multiple screens in one go).
allowed-tools: Bash(xcrun *), Bash(python3 *), Bash(defaults *), Bash(idb *), Bash(idb_companion *), Bash(kill *), Bash(sleep *), Bash(rm *), Bash(ls *), Read
---

Navigate to the requested screen(s) or UI element(s) in the running iOS simulator and capture screenshots.

## Step 0 — Hardware keyboard check (ALWAYS run this first, before anything else)

The software keyboard only appears in the simulator when the hardware keyboard is **disconnected**. If it is connected, text inputs will not show the on-screen keyboard in screenshots.

Run these as **two separate Bash calls** to check the booted simulator's UDID and keyboard setting:

```bash
# Call 1 — get UDID via python3 subprocess and write to temp file (starts with python3 ✓)
python3 -c "
import json, subprocess, pathlib
result = subprocess.run(['xcrun', 'simctl', 'list', 'devices', 'booted', '-j'], capture_output=True, text=True)
d = json.loads(result.stdout)
udid = next(v['udid'] for vs in d['devices'].values() for v in vs if v['state'] == 'Booted')
pathlib.Path('/tmp/sim_udid.txt').write_text(udid)
print('UDID:', udid)
"
```

```bash
# Call 2 — read hardware keyboard preference (starts with python3 ✓)
python3 -c "
import subprocess, pathlib
udid = pathlib.Path('/tmp/sim_udid.txt').read_text().strip()
r = subprocess.run(['defaults', 'read', 'com.apple.iphonesimulator', 'DevicePreferences'], capture_output=True, text=True)
lines = r.stdout.splitlines()
in_block = False
for line in lines:
    if udid in line:
        in_block = True
    if in_block and 'ConnectHardwareKeyboard' in line:
        print(line.strip())
        break
else:
    print('ConnectHardwareKeyboard not set (defaults to 1 = connected)')
"
```

**Interpret the result:**
- `ConnectHardwareKeyboard = 0` → hardware keyboard is **disconnected** ✅ software keyboard will appear → proceed automatically
- `ConnectHardwareKeyboard = 1` or key missing → hardware keyboard is **connected** ⛔ software keyboard will NOT appear

**If connected (⛔):** Stop immediately. Tell the user:

> ⚠️ The simulator's hardware keyboard is currently **connected**, which means the software keyboard won't appear in screenshots.
>
> To fix this:
> 1. Open your booted iPhone Simulator
> 2. Go to **I/O → Keyboard**
> 3. Turn off **"Connect Hardware Keyboard"**
> 4. If the software keyboard still doesn't appear after that, use the same menu to tap **"Show Keyboard"**
>
> Once done, let me know and I'll proceed with the screenshots.

Do **not** proceed with navigation or screenshots until the user confirms the hardware keyboard is disconnected.

## Output directories

- **Final screenshots**: `/Users/guilhermereis/Desktop/clones/shopit-monorepo/.claude/screenshots-output/`
- **Temp navigation screenshots**: `/tmp/nav_<slug>.png` — reuse freely, overwrite between steps

## Batch run setup (when multiple screenshots are requested)

1. Ensure output directory exists and clear it — run as **two separate Bash calls**:
   ```bash
   python3 -c "import pathlib; pathlib.Path('/Users/guilhermereis/Desktop/clones/shopit-monorepo/.claude/screenshots-output').mkdir(parents=True, exist_ok=True)"
   ```
   ```bash
   rm -f /Users/guilhermereis/Desktop/clones/shopit-monorepo/.claude/screenshots-output/*.png
   ```
2. Process each target one by one.
3. Save each final screenshot as: `/Users/guilhermereis/Desktop/clones/shopit-monorepo/.claude/screenshots-output/<slug>.png`
   - slug = kebab-case name of the target, e.g. `account-sheet-email`, `cart-gift-message`, `comments-sheet`
4. After all screenshots are done, list the output directory and confirm each file.

## App Navigation Map

### Floating Tab Bar (glass pill at the bottom of screen)
The pill only has **3 icons**: Home, Search, Orders. There is NO Account or Notifications icon in the tab bar.
- **Home** — leftmost icon (house outline)
- **Search** — middle icon (magnifying glass)
- **Orders** — rightmost icon (receipt outline)
- **Cart** — a separate pill that appears to the **right** of the main pill only when there are items in the cart; tapping opens CartSheet

### Home Screen Header (top of the Home feed — NOT the tab bar)
- **UserAvatar** — circular profile picture at the **top-left** of the home screen header; tapping navigates to the user's own Profile page
- **Bell icon** — notification icon at the **top-right** of the home screen header; tapping navigates to `/notifications`

### Screens & Entry Points

**Home Feed — `/home`**
- Default screen after login; vertical ForYouFeed of product cards
- Tap product card → PDP
- Tap comment bubble icon on a feed item → CommentsSheet (type in comment box to show keyboard)

**Product Detail Page (PDP) — `/[orgId]/p/[productId]`**
- Entry: tap any product card on Home feed
- "Send Gift" button (near bottom) → SendGiftSheet
- "Add to Cart" → cart count badge appears on FloatingTabBar

**CartSheet**
- Entry: tap cart icon in FloatingTabBar
- Inside sheet:
  - Gift icon (top-right of sheet) → gift flow → friend picker (search input) → gift message input
  - "Continue to Checkout" / "Checkout" button → checkout sub-sheets open sequentially:
    - **NameSheet** — if name missing from profile
    - **EmailSheet** — if email missing from profile
    - **ShippingAddressSheet** — if shipping address missing

**SendGiftSheet**
- Entry: PDP → "Send Gift" button
- Multi-step: friend picker with search input → gift message input → payment

**Orders Tab — `/(orders)/orders`**
- Entry: tap Orders icon in FloatingTabBar
- "Order History" button (top-right) → AllOrders screen
- Tap order card → OrderSheet
- Tap gift card → GiftSentSheet

**AccountSheet**
- Entry (4 steps): tap **UserAvatar** (top-left of Home header) → Profile page → tap **settings gear icon** (top-right of Profile page) → Settings screen → tap **"Account"** row → AccountSheet opens
- Inside AccountSheet: tap Email, Phone, or Name row to open the respective input sheet
- Shows editable fields for name, email, phone

**Settings Screen — `/settings`**
- Entry: Profile page → tap settings gear icon (top-right, only visible on own profile)
- Contains rows: Account (→ AccountSheet), Notifications (→ NotificationsSheet), Data & Privacy, Blocked Users
- **Not accessible from the FloatingTabBar directly**

**NameSheet**
- Entry: CartSheet → "Checkout" → triggered automatically if name is missing
- Also accessible: Home → UserAvatar → Profile → settings gear → Settings → Account → Name row

**EmailSheet**
- Entry: CartSheet → "Checkout" → triggered automatically if email is missing
- Also accessible: Home → UserAvatar → Profile → settings gear → Settings → Account → Email row

**ShippingAddressSheet**
- Entry: CartSheet → "Checkout" → triggered automatically if shipping address is missing
- Scrollable form with many fields

**CommentsSheet**
- Entry: tap comment icon (speech bubble) on any home feed item OR on a user profile page
- Tap the comment input to show the keyboard

**SaveAddressSheet**
- Entry: Gift claim flow at `/gift/[giftId]` — accessible from a gift notification or gift link → shipping address step

**AuthSheet**
- Entry: tap any protected feature while signed out (e.g. tap Orders tab when logged out)
- Contains: phone/email input, OTP input

**DevEmailAuthSheet**
- Entry: AuthSheet → dev-mode email option (only visible in dev/Expo Go builds)

**WishlistFormSheet**
- Entry: tap bookmark/wishlist icon on any product card → "Create Wishlist"
- Opens modal at `/(modal)/wishlist/editor`
- Currently has no text inputs — just verify it opens without crashing

**NotificationsSheet**
- Entry: tap **bell icon** at the top-right of the Home screen header (NOT the FloatingTabBar) → navigates to `/notifications`
- Also accessible from Settings screen → "Notifications" row

**OrderSheet**
- Entry: Orders tab → tap any order card

**GiftSentSheet**
- Entry: Orders tab → tap a gift-type order card

## Tap helper — start this once per session, reuse for all taps

Run each line as a **separate Bash call** so every command starts with its binary name and auto-approves:

```bash
# Call 1 — get UDID via python3 subprocess and write to temp file (starts with python3 ✓)
python3 -c "
import json, subprocess, pathlib
result = subprocess.run(['xcrun', 'simctl', 'list', 'devices', 'booted', '-j'], capture_output=True, text=True)
d = json.loads(result.stdout)
udid = next(v['udid'] for vs in d['devices'].values() for v in vs if v['state'] == 'Booted')
pathlib.Path('/tmp/sim_udid.txt').write_text(udid)
print('UDID:', udid)
"
```

```bash
# Call 2 — read UDID and start idb_companion with literal UDID (starts with python3 ✓)
python3 -c "
import pathlib, subprocess, os
udid = pathlib.Path('/tmp/sim_udid.txt').read_text().strip()
proc = subprocess.Popen(['idb_companion', '--udid', udid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
pathlib.Path('/tmp/idb_pid.txt').write_text(str(proc.pid))
print('idb_companion started, PID', proc.pid, 'UDID', udid)
"
```

```bash
# Call 3 — wait then connect (starts with sleep ✓)
sleep 2 && idb connect localhost 10882 2>/dev/null
```

**Tap command — ALWAYS use a literal UDID, never shell substitution:**

Before the first tap each session, read the UDID into your context with:
```bash
python3 -c "import pathlib; print(pathlib.Path('/tmp/sim_udid.txt').read_text().strip())"
```

Then embed that value **literally** in every tap — e.g. if the UDID is `55A0A61B-21E4-4D21-BB3B-077FAF7176FB`:
```bash
idb ui tap <X> <Y> --udid 55A0A61B-21E4-4D21-BB3B-077FAF7176FB 2>/dev/null
```

This form starts with `idb` and contains no shell substitution, so it auto-approves every time.

**⛔ NEVER write:** `idb ui tap <X> <Y> --udid "$(cat /tmp/sim_udid.txt)"` — the `$(...)` substitution inside a quoted string is unparseable by the permission checker and will prompt for confirmation on every tap.

At the end of the session:
```bash
python3 -c "import pathlib, os, signal; os.kill(int(pathlib.Path('/tmp/idb_pid.txt').read_text().strip()), signal.SIGTERM)"
```

**Do NOT** use `export PATH=...`, `UDID=$(...)`, or `IDB_PID=$!` as standalone shell assignments — these start with variable names and will not match the auto-approve patterns. Always use the temp file pattern above.

## Coordinate system

`idb ui tap` uses **logical iOS points** — same coordinate system as the simctl screenshot.

Screenshots from `xcrun simctl io booted screenshot` are saved at 3× native resolution.
- A simctl screenshot for this device is **1170×2532 px** = **390×844 logical points**
- 1 logical point = 3 original pixels

**Always use the grid overlay technique to find precise tap coordinates** — do NOT estimate from the raw screenshot, as visual estimation is unreliable and leads to mis-taps.

### Grid overlay technique (required before every tap)

After taking a nav screenshot, bake a logical-point grid into the image using one of the two presets below. Use Grid A (default) unless targets are very small or densely packed, in which case use Grid B. Run the python block inside a `python3 << 'EOF' … EOF` heredoc, substituting `<slug>` with your actual slug.

Two grid presets are available. **Default is Grid A.**

**Grid A — high precision (default)**
- Red labeled lines every 50pt, orange lines every 10pt
- **All lines must be `width=2`** — never use `width=1` for any line; thin lines are invisible at 3× resolution

```python
for lx in range(0, 391, 10):
    px = lx * 3
    color = (255, 0, 0) if lx % 50 == 0 else (255, 140, 0)
    draw.line([(px, 0), (px, h)], fill=color, width=2)
    if lx % 50 == 0:
        draw.text((px + 3, 10), str(lx), fill=(255, 0, 0))
for ly in range(0, 845, 10):
    py = ly * 3
    color = (255, 0, 0) if ly % 50 == 0 else (255, 140, 0)
    draw.line([(0, py), (w, py)], fill=color, width=2)
    if ly % 50 == 0:
        draw.text((5, py + 3), str(ly), fill=(255, 0, 0))
```

**Grid B — super high precision (use when targets are very small or densely packed)**
- Red labeled lines every 50pt, orange labeled lines every 10pt, faint yellow lines every 5pt
- **All lines must be `width=2`**

```python
for lx in range(0, 391, 5):
    px = lx * 3
    if lx % 50 == 0:
        color, width = (255, 0, 0), 2
    elif lx % 10 == 0:
        color, width = (255, 140, 0), 2
    else:
        color, width = (200, 200, 0), 2
    draw.line([(px, 0), (px, h)], fill=color, width=width)
    if lx % 50 == 0:
        draw.text((px + 3, 10), str(lx), fill=(255, 0, 0))
    elif lx % 10 == 0:
        draw.text((px + 2, 25), str(lx), fill=(255, 140, 0))
for ly in range(0, 845, 5):
    py = ly * 3
    if ly % 50 == 0:
        color, width = (255, 0, 0), 2
    elif ly % 10 == 0:
        color, width = (255, 140, 0), 2
    else:
        color, width = (200, 200, 0), 2
    draw.line([(0, py), (w, py)], fill=color, width=width)
    if ly % 50 == 0:
        draw.text((5, py + 3), str(ly), fill=(255, 0, 0))
    elif ly % 10 == 0:
        draw.text((18, py + 2), str(ly), fill=(255, 140, 0))
```

### ⚠️ Zoom before you tap — MANDATORY

**Full-screen grid labels are too small to read accurately.** At 390×844pt rendered into a small image, the y-label text is only a few pixels tall and misreading it by even 50–80pt causes mis-taps (e.g. hitting Notifications instead of Account). This has caused real errors in the past.

**Before every tap, crop the screenshot to the region containing your target and re-apply the grid to that crop**, keeping y-labels in original full-screen coordinates. This makes labels 4–6× larger and readable:

```python
# Crop to region of interest (adjust y_start/y_end to bracket your target)
y_start, y_end = 80, 350  # logical points
crop = img.crop((0, y_start * 3, w, y_end * 3))
draw = ImageDraw.Draw(crop)
cw, ch = crop.size
for lx in range(0, 391, 10):
    px = lx * 3
    color = (255, 0, 0) if lx % 50 == 0 else (255, 140, 0)
    draw.line([(px, 0), (px, ch)], fill=color, width=2)
    if lx % 50 == 0:
        draw.text((px + 3, 5), str(lx), fill=(255, 0, 0))
for ly_offset in range(0, y_end - y_start + 1, 10):
    py = ly_offset * 3
    ly_label = y_start + ly_offset
    color = (255, 0, 0) if ly_label % 50 == 0 else (255, 140, 0)
    draw.line([(0, py), (cw, py)], fill=color, width=2)
    if ly_label % 10 == 0:
        draw.text((5, py + 2), str(ly_label), fill=(255, 0, 0) if ly_label % 50 == 0 else (255, 140, 0))
crop.save("/tmp/nav_<slug>_zoom.png")
```

The y values you read from the zoomed image are already in full-screen coordinates — pass them directly to `idb ui tap`.

Read the zoomed grid image — read off the logical (x, y) directly from the labeled grid lines, then pass those values to `idb ui tap`.

### ⛔ NEVER read pixel positions from the image — always read labeled gridline values

The image is rendered at 3× resolution. A target that appears at pixel x=100 in the image is at logical x=33pt — NOT x=100. **Raw pixel positions must never be used as logical point coordinates.**

The only valid way to determine coordinates:
1. Find the nearest labeled vertical gridline to the LEFT of the target → that label is its approximate logical x.
2. Find the nearest labeled horizontal gridline ABOVE the target → that label is its approximate logical y.
3. Interpolate between adjacent labeled lines only if the target is clearly between them (e.g. midway between the 50 and 100 lines → x=75).

If you cannot confidently read a label, regenerate with Grid B (denser labels) or tighten the crop window. **Do not guess.**

## Navigation Workflow (per target)

1. **Take a nav screenshot**: `xcrun simctl io booted screenshot /tmp/nav_<slug>.png`
2. **Apply grid overlay** (see Grid overlay technique above) → save as `/tmp/nav_<slug>_grid.png`
3. **🛑 BLOCKING: Zoom + Read** — crop the screenshot to the region containing your target (see "Zoom before you tap" above), apply the grid to the crop, save as `/tmp/nav_<slug>_zoom.png`, then call `Read` on the zoom image. Read off the logical (x, y) from the zoomed labels. **Never read coordinates from the full-screen grid — the labels are too small and cause mis-taps. Never estimate from memory or a raw screenshot.**
4. **Tap**: `idb ui tap <X> <Y> --udid <LITERAL_UDID> 2>/dev/null` — using the literal UDID string (no shell substitution) and coordinates derived in step 3.
5. **Wait**: `sleep 0.8` for navigation; `sleep 1.2` after a bottom sheet opens.
6. **Re-screenshot to confirm**: take a fresh screenshot, apply grid, **Read the grid image**, verify the expected screen/sheet appeared before continuing.
7. **Save final screenshot**: `xcrun simctl io booted screenshot /Users/guilhermereis/Desktop/clones/shopit-monorepo/.claude/screenshots-output/<slug>.png`
8. Read the saved file and briefly describe what's visible.

## Between targets (batch runs)

After finishing one target:
- The app may be in a deep state (sheet open, nested screen). Navigate back to a clean state before starting the next target:
  - Dismiss open sheets by tapping outside them or swiping down
  - Go back to Home tab by tapping the Home icon in FloatingTabBar
- Then start the next target's navigation from a known clean state.

## Rules
- **Always run the hardware keyboard check (Step 0) before doing anything else.** If the keyboard is connected, stop and inform the user — do not proceed until they confirm it's disconnected.
- Always take a fresh screenshot first — never assume current app state.
- **Always use the grid overlay technique** to determine tap coordinates — never estimate from the raw screenshot.
- **🛑 You MUST call `Read` on the grid image before every tap.** The mandatory sequence is: screenshot → generate grid → `Read` grid image → extract coordinates from grid labels → tap. Skipping the `Read` and guessing or estimating coordinates is forbidden, even if the target seems obvious.
- **⛔ Never use raw pixel positions as logical coordinates.** Image pixels are 3× logical points. Always read the value from the nearest labeled gridline — that label IS the logical point value. Pixel position ÷ 3 ≠ an acceptable substitute for reading the label.
- Wait after every tap before screenshotting — animations and network requests take time.
- If a step doesn't produce the expected result, screenshot again, re-apply the grid, Read the new grid, and re-evaluate before retrying.
- Do not ask the user for confirmation — navigate and capture automatically.
- For keyboard verification shots: inputs with `autoFocus` show the keyboard automatically when a step opens — no need to tap the input again.
- If a target is only available in dev builds (DevEmailAuthSheet) and is not visible, note it and skip.
- Present a summary at the end listing each saved file and a one-line description of what it shows.
- **All commands starting with `xcrun`, `python3`, `idb`, `idb_companion`, `sleep`, `kill`, `rm`, `ls`, `mkdir`, or `defaults` are pre-approved — never pause to ask for confirmation before running them.**
- **⛔ Never chain commands with `&&` across different binaries** (e.g. `mkdir -p ... && xcrun ...`). The permission checker parses compound commands as a unit and may fail to match either rule. Always run each command as a separate Bash call.

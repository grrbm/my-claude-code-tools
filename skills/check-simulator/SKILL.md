---
name: check-simulator
description: Take a screenshot of the booted iOS simulator and describe what is on screen. Use when asked to check the simulator screen, look at the simulator, or what the simulator shows.
allowed-tools: Bash(xcrun *), Read
---

> **Headful simulator only.** Never drive, screenshot or record a headless simulator. On Xcode 27 the simulator
> window is hosted by **DeviceHub** (`/Applications/Xcode.app/Contents/Applications/DeviceHub.app`, bundle id
> `com.apple.dt.Devices`); there is no `Simulator.app` any more. Before touching the device, make sure it is running:
> `pgrep -x DeviceHub || open -b com.apple.dt.Devices` (older Xcode: `open -a Simulator`), and that the iPhone 16e is
> booted. `bun run ios` (`expo run:ios`) also opens it. If the window host cannot be opened, **stop and tell the
> user**; do not continue headless. (Headless also hides the QWERTY keyboard until text is typed, which makes
> keyboard checks and recordings misleading.)

Take a fresh screenshot of the booted iOS simulator and describe what you see.

Workflow:

1. Run: `xcrun simctl io booted screenshot /tmp/screen.png`
2. Read the file at `/tmp/screen.png` using the Read tool.
3. Describe what you see and respond accordingly.

Rules:
- Always capture a fresh screenshot — never reuse a previous one.
- Do not ask for confirmation before taking the screenshot.
- After reading the image, respond based on its contents as if looking at it in real time.
- **This skill is for observation only.** Never derive tap coordinates from this screenshot and never attempt navigation (idb ui tap) after running it. If the user's request requires navigating to a specific screen or tapping UI elements, use the `screenshot-screen` skill instead — it has the mandatory grid overlay technique that produces accurate coordinates.

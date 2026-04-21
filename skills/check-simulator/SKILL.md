---
name: check-simulator
description: Take a screenshot of the booted iOS simulator and describe what is on screen. Use when asked to check the simulator screen, look at the simulator, or what the simulator shows.
allowed-tools: Bash(xcrun *), Read
---

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

# Check Simulator Screen

Trigger:
When I say something like:

check my screen
check my simulator screen
what does my simulator show
look at my simulator

Behavior:
Take a screenshot of the booted iOS simulator and read it visually.

Workflow:

1. Run: `xcrun simctl io booted screenshot /tmp/screen.png`
2. Read the file at `/tmp/screen.png` using the Read tool.
3. Describe what you see and respond accordingly.

Rules:

- Always capture a fresh screenshot — never reuse a previous one.
- Do not ask for confirmation before taking the screenshot, just do it.
- After reading the image, respond based on its contents as if you were looking at it in real time.

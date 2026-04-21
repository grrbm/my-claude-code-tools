---
name: check-iphone
description: Read the most recent screenshot from the user's desktop and describe what is on screen. Use when asked to check the iPhone screen, look at the iPhone, or what the physical device shows.
allowed-tools: Bash(ls *), Bash(find *), Read
---

Read the most recent screenshot from the user's Desktop and describe what you see.

Workflow:

1. Run: `ls -t ~/Desktop/Screenshot*.png ~/Desktop/Screenshot*.jpg 2>/dev/null | head -1` to find the most recent screenshot file.
2. Read that file using the Read tool.
3. Describe what you see and respond accordingly.

Rules:
- Always use the single most recent file — never guess or reuse a previous path.
- Do not ask for confirmation before reading.
- After reading the image, respond based on its contents as if looking at it in real time.

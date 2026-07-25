---
name: context7
description: Look up documentation for a package or library using Context7 MCP. Use this whenever a specific npm package, library, or framework is mentioned and you need accurate, up-to-date API docs before writing or modifying code that uses it.
argument-hint: <package-name>
allowed-tools: mcp__context7__resolve-library-id, mcp__context7__get-library-docs
---

Use the Context7 MCP to fetch up-to-date documentation for: $ARGUMENTS

1. Call `mcp__context7__resolve-library-id` with the package name to get the correct library ID.
2. Call `mcp__context7__get-library-docs` with that library ID to fetch the relevant docs.
3. Use the returned documentation to inform your answer or implementation.

If no argument is provided, infer the package from the current conversation context.

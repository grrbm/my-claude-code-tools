---
name: linear
description: Query or modify Linear using the GraphQL API. Use whenever asked to check, fetch, or modify anything on Linear.
argument-hint: <query or action>
allowed-tools: Bash(curl *)
---

Use the Linear API to handle: $ARGUMENTS

API Endpoint: https://api.linear.app/graphql

Authentication Header:
  Authorization: $LINEAR_API_KEY

Example request pattern:

```bash
curl https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{ "query": "query { viewer { id name email } }" }'
```

Rules:
- Always read the API key from the `LINEAR_API_KEY` environment variable.
- Never hardcode or print the API key.
- Only return relevant results.

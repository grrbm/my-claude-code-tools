# Linear Integration

Trigger:
When I ask you to check, fetch, or modify anything on Linear.

Behavior:
1. Use the Linear API.
2. Use the API key from the environment variable `LINEAR_API_KEY`.
3. Never hardcode or print the API key.
4. Prefer using curl or CLI tools to query the Linear GraphQL API.

API Endpoint:
https://api.linear.app/graphql

Authentication Header:

Authorization: $LINEAR_API_KEY

Example request pattern:

curl https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{ "query": "query { viewer { id name email } }" }'

Rules:
- Always read the API key from the environment variable.
- Never expose the API key in output.
- Only return relevant results.

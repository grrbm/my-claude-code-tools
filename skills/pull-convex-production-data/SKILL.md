---
name: pull-convex-production-data
description: Pull a read-only production data summary for a specific user from a Convex deployment. Use this whenever the user asks to inspect, pull, trace, audit, or summarize a production user's Convex records by email, name, Clerk ID, or Convex user ID, especially in the Shop It monorepo. Prefer the user's already-authenticated Convex dashboard session when CLI authentication is unavailable, trace linked records through indexed user fields, and return a concise PII-aware report without mutating production.
---

# Pull Convex Production Data

Use this workflow to inspect one user's production records across Convex tables. Treat the deployment as read-only: the goal is to identify the exact user, trace their linked data, and report what exists without changing production.

## Inputs

Resolve these from the user's request or the repository before starting:

- Production deployment name, such as `kindly-manatee-929`
- At least one user identifier: email, full name, Clerk ID, or Convex user ID
- Repository root containing the Convex schema, normally `packages/convex/schema.ts`

If the deployment or user identifier is genuinely missing, ask one concise question. Do not ask for information already present in the conversation.

## Safety contract

- Perform reads only. Do not add, edit, delete, import, or run mutations/actions.
- Do not use a production mutation as a shortcut for querying data.
- Never expose auth tokens, push tokens, signed cart URLs, full home addresses, full phone numbers, or raw browsing/search history in chat unless the user explicitly asks for that exact field.
- It is fine to use sensitive identifiers inside the authenticated Convex dashboard to perform the requested lookup. Keep the resulting report proportional to the user's request.
- Do not claim a count, status, or total until it is visibly verified in the dashboard or returned by an authenticated read-only query.

## Workflow

### 1. Try the authenticated CLI path briefly

From the monorepo root, first check whether the Convex CLI can run an inline read-only query against the named deployment. Use `bunx`, never `npx`.

Example exact-email lookup:

```bash
bunx convex run --deployment <deployment> --inline-query \
  'return await ctx.db.query("users").withIndex("by_email", q => q.eq("email", "<email>")).collect()'
```

If the command reports an invalid or expired access token, stop retrying the CLI. Do not run `convex dev`, log out, or disturb the user's existing authentication. Continue through the already-authenticated dashboard.

### 2. Use the existing Convex dashboard session

Read and follow the `agent-browser` skill before browser automation.

- Reuse an existing logged-in browser tab for `dashboard.convex.dev` when one is available.
- Confirm the tab is on the requested team, project, and production deployment before reading data.
- Do not open a separate unauthenticated session when the user already has an authenticated tab.
- Leave the final exact user row open in the dashboard when finished.

### 3. Resolve the exact user row

Open the `users` table and use the most selective available index:

- Email: `by_email`
- Clerk ID: the matching Clerk index from the deployed schema
- Convex ID: `_id` or the appropriate ID filter
- Name: use a name filter only to find candidates, then verify with another stable identifier

Convex dashboard filter values must be valid Convex values. For IDs and strings, enter the value as a quoted string in the filter editor:

```text
"jx77enqgv1fjrmhsdaxpznhws584342c"
```

An unquoted ID may appear as a filter chip while still showing an error and returning unfiltered rows. Verify success by checking all three signals:

1. No “not a valid Convex value” error is present.
2. The URL's encoded filter changes or the filter persists after focus leaves the editor.
3. The document count and visible row match the intended user.

Confirm the exact row using at least two available identifiers, for example email plus name or email plus Clerk ID. Record the Convex `_id`; it is the join key for the remaining tables.

### 4. Discover the deployed relationships

Use the local schema as a map, not as proof that an index is deployed:

```bash
rg -n 'defineTable|\.index\(' packages/convex/schema.ts
```

Inspect only relevant schema sections. Common Shop It relationships include:

| Table | User field/index | Purpose |
|---|---|---|
| `orders` | `userId` / `by_user` | Orders paid for or gifts sent |
| `orders` | `recipientId` / `by_recipient` | Gifts received |
| `giftIntents` | `senderUserId` / `by_sender` | Gift attempts and conversions |
| `giftIntents` | `recipientUserId` / `by_recipient` | Incoming gift intents |
| `wishlists` | `userId` / `by_user` | Wishlist headers |
| `wishlistItems` | `wishlistId` / `by_wishlist` | Items for each resolved wishlist |
| `friendships` | `userIdA` / `by_user_a` and `userIdB` / `by_user_b` | Accepted and pending relationships |
| `notifications` | `userId` / `by_user` | Read/unread notifications |
| `pushDevices` | `userId` / `by_user_id` | Active device count; never report the token |
| `feedback` | `userId` / `by_user` | Submitted feedback |
| `orgMembers` | `userId` / `by_user` | Organization memberships |

The checked-out schema can be ahead of production. If selecting an expected index falls back to `by_creation_time`, do not treat a zero-row result as authoritative. Report that the relationship could not be verified through that production index, or use another deployed read-only path.

### 5. Trace linked records with indexes

Filter each relevant table by the resolved Convex user ID. Use every participant-side index where a relationship is symmetric:

- Query both `friendships.by_user_a` and `friendships.by_user_b`.
- Query both `orders.by_user` and `orders.by_recipient`.
- Query both sender and recipient gift-intent indexes when the requested scope is a full account pull.
- Resolve each wishlist first, then query `wishlistItems.by_wishlist` for every wishlist ID.

For each table, capture only verified aggregates and operationally useful details:

- Row count
- Status breakdown
- Read/unread or active/inactive breakdown
- Monetary totals from final/captured fields, not preliminary quote fields
- Relevant dates and record IDs when useful for debugging

Avoid double-counting. A gift intent and its resulting order describe stages of the same flow, so report them separately as intents and orders rather than summing them together.

### 6. Interpret money and lifecycle fields carefully

- Treat integer currency fields as cents and format them as dollars only after summing the correct final fields.
- For sent gifts, prefer captured/final order amounts such as `giftCapturedCents` or `giftClaimFinalCents` according to the observed lifecycle.
- Do not include expired, cancelled, or uncaptured records in a captured-spend total.
- Keep `CONFIRMED`, `FULFILLED`, `DELIVERED`, `expired`, `cancelled`, and unset statuses distinct unless the summary explicitly groups them and lists the breakdown.
- When a displayed order status is unset, say so; do not infer “pending” unless another field proves it.

### 7. Leave a useful dashboard state

Return to the exact filtered `users` row and verify that exactly one matching document is loaded. Preserve the user's existing tab and leave it open for follow-up inspection.

## Report format

Lead with confirmation of the matched production user and deployment. Then use a compact list:

```markdown
Pulled <name>'s production data from `<deployment>` and left the filtered user record open.

- User ID: `<convex-id>`
- Clerk ID: `<clerk-id>`
- Account: created <date>; onboarding <state>; internal <yes/no>; deletion markers <state>
- Friends: <accepted> accepted, <pending> pending
- Wishlists: <count>, containing <active-item-count> active items
- Gifts sent: <intent-count> intents resulting in <order-count> orders
  - Status breakdown: ...
  - Captured/final total: `$...`
- Gifts received: ...
- Notifications: <total>, <unread> unread
- Push devices: <active-count> active
- Feedback: <count or none>
```

Include stable internal identifiers that help debugging. Redact or summarize direct PII by default, for example “Las Vegas shipping address on file” instead of the street address. Say that sensitive fields remain visible in the authenticated dashboard.

## Completion checklist

Before responding, verify:

- The deployment name matches the user's request.
- The user match is exact and supported by at least two identifiers where possible.
- Every reported count came from an applied, valid filter rather than an invalid filter chip.
- Both sides of symmetric relationships were checked.
- Currency totals exclude uncaptured/cancelled/expired records.
- No production writes occurred.
- The exact user row is left open for follow-up.

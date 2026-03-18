# Test Push Notifications

Trigger:
When I ask something like:

test a push notification
send a test push notification
test push notification
trigger a push notification

Behavior:

Step 1 — Warn about device requirement:

Reply with:

> ⚠️ Push notifications are not delivered to the iOS Simulator. Make sure your **iPhone is connected** and the app is running on a physical device before proceeding.

Then ask: "Ready to continue? Which notification would you like to test?"

Step 2 — Show options:

Present the available notification types:

1. **Order Fulfillment** — simulates a fulfillment status update for an order (e.g. shipped, delivered)

Step 3 — Gather required info based on the chosen type:

**Option 1: Order Fulfillment**

Show the user the defaults and ask them to choose:

> **1** — Use defaults (`grrbm2+colorless-clam.mobile@gmail.com`, order `1069`, status `SHIPPED`)
> **2** — Customize values

If they reply `1`, proceed immediately with the defaults.
If they reply `2`, ask for each value individually:
- `customerEmail` [default: `grrbm2+colorless-clam.mobile@gmail.com`]
- `orderId` [default: `1069`]
- `fulfillmentStatus` [default: `SHIPPED`] — one of: `FULFILLED`, `IN_TRANSIT`, `OUT_FOR_DELIVERY`, `DELIVERED`, `SHIPPED`, `PARTIALLY_FULFILLED`, `ON_HOLD`, `PENDING_FULFILLMENT`, `SCHEDULED`

To get the `organizationId` (Convex DB `_id`):
- Ask the user for the Clerk org ID (e.g. `org_xxx`) if not already known
- OR query the organizations table to find it — never ask the user to dig it up themselves if you can resolve it

Step 4 — Call the function:

For Order Fulfillment, run:

```
bunx convex run mobile/shopify/notifications:sendFulfillmentStatusNotification '{
  "organizationId": "<convex_org_id>",
  "orderId": "<orderId>",
  "orderName": "Order <orderId>",
  "customerEmail": "<customerEmail>",
  "fulfillmentStatus": "<fulfillmentStatus>"
}'
```

Run this from the monorepo root.

Step 5 — Report result:

- If `success: true` and `notificationRecorded: true` → confirm the notification was sent and tell the user to check their iPhone. Also add: "If you don't receive it, the dedup log may have a stale entry — delete the matching record from the `notifications` table in the Convex dashboard and try again."
- If `success: true` and `notificationRecorded: false` → explain why it wasn't sent (user not found, status not meaningful, etc.).
- If `success: false` → report the error.

Rules:

- Always show the iPhone warning first — do not skip it.
- Never call the function without having all required fields confirmed.
- `orderName` can always be inferred as `"Order <orderId>"` — do not ask the user for it.
- The `organizationId` field must be the Convex DB `_id`, not the Clerk org ID. Resolve it automatically if possible.

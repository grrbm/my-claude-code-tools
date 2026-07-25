---
name: test-push-notification
description: Send a test push notification to a physical device. Use when asked to test a push notification, send a test push notification, or trigger a push notification.
allowed-tools: Bash(bunx *), Bash(curl *)
---

Send a test push notification.

Step 1 — Warn about device requirement:

Reply with:

> ⚠️ Push notifications are not delivered to the iOS Simulator. Make sure your **iPhone is connected** and the app is running on a physical device before proceeding.

Then ask: "Ready to continue? Which notification would you like to test?"

Step 2 — Show options:

Present the available notification types:

1. **Order Fulfillment** — simulates a fulfillment status update for an order (e.g. shipped, delivered)

Step 3 — Gather required info:

**Option 1: Order Fulfillment**

Show the user the defaults and ask them to choose:

> **1** — Use defaults (`grrbm2+colorless-clam.mobile@gmail.com`, order `1069`, status `SHIPPED`)
> **2** — Customize values

If they reply `1`, proceed immediately with the defaults.
If they reply `2`, ask for each value individually:
- `customerEmail` [default: `grrbm2+colorless-clam.mobile@gmail.com`]
- `orderId` [default: `1069`]
- `fulfillmentStatus` [default: `SHIPPED`] — one of: `FULFILLED`, `IN_TRANSIT`, `OUT_FOR_DELIVERY`, `DELIVERED`, `SHIPPED`, `PARTIALLY_FULFILLED`, `ON_HOLD`, `PENDING_FULFILLMENT`, `SCHEDULED`

For `organizationId` (Convex DB `_id`): ask the user for the Clerk org ID (e.g. `org_xxx`) OR query the organizations table — never ask the user to dig it up themselves if it can be resolved automatically.

Step 4 — Call the function from the monorepo root:

```bash
bunx convex run mobile/shopify/notifications:sendFulfillmentStatusNotification '{
  "organizationId": "<convex_org_id>",
  "orderId": "<orderId>",
  "orderName": "Order <orderId>",
  "customerEmail": "<customerEmail>",
  "fulfillmentStatus": "<fulfillmentStatus>"
}'
```

Step 5 — Report result:

- `success: true` + `notificationRecorded: true` → confirm sent, tell user to check their iPhone. Add: "If you don't receive it, the dedup log may have a stale entry — delete the matching record from the `notifications` table in the Convex dashboard and try again."
- `success: true` + `notificationRecorded: false` → explain why it wasn't sent.
- `success: false` → report the error.

Rules:
- Always show the iPhone warning first.
- Never call the function without all required fields confirmed.
- `orderName` is always `"Order <orderId>"` — do not ask the user for it.
- `organizationId` must be the Convex DB `_id`, not the Clerk org ID.

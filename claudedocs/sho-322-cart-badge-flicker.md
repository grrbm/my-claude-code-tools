# SHO-322 — Cart Badge Flicker: Badge Should Count Distinct Items

## Symptom

The "Cart N" badge in the `CartSheet` header (and the `CartFAB` badge outside the sheet) flickered when the user tapped `+` or `−` on an existing line item. The count would briefly jump — e.g. "Cart 1" → "Cart 2" → "Cart 1" — before settling on the correct value.

## Root Cause

`optimisticItemCount` (CartSheet) and `itemCount` (useCart / CartFAB) were both computed by **summing total quantity across all line items**, not counting distinct line items:

```ts
// useCart.ts — BEFORE
const itemCount = cartData?.cart.totalQuantity ?? 0

// CartSheet.tsx — BEFORE
const optimisticItemCount =
  cartData?.cart.lines.edges.reduce((total, edge) => {
    const line = edge.node
    if (line.__typename !== 'CartLine') return total
    const pendingQty = pendingQuantities.get(line.id)
    return total + (pendingQty !== undefined ? pendingQty : line.quantity)
  }, 0) ?? itemCount
```

With one snowboard at qty=1, the badge showed "1". Tapping `+` set an optimistic `pendingQty=2`, causing `optimisticItemCount=2` → badge "2". After the mutation resolved and `pendingQuantities` was cleared there was also a secondary race (see below) that caused a brief "1" before the server-confirmed "2" landed.

## The Badge Has the Wrong Semantics

The badge is meant to communicate **"you have N different products in your cart"**, not the total number of units. Changing the quantity of an already-present item should never move the badge. This is both the correct UX and the fix that eliminates the flicker entirely.

## Fix

Count distinct `CartLine` nodes instead of summing quantities:

```ts
// useCart.ts — AFTER
const itemCount =
  cartData?.cart.lines.edges.filter(
    (edge) => edge.node.__typename === 'CartLine'
  ).length ?? 0

// CartSheet.tsx — AFTER
const optimisticItemCount =
  cartData?.cart.lines.edges.filter(
    (edge) => edge.node.__typename === 'CartLine'
  ).length ?? 0
```

Because `pendingQuantities` is no longer involved in computing the badge, the count is completely stable during stepper interactions. It only changes when a new line item is added or an existing one is removed.

## Secondary Race (also fixed in this PR)

Even after the semantics fix, a timing issue existed in the success path of `handleQuantityChange` in `CartLineItem`: `pendingQuantities` was cleared synchronously immediately after `await refetch()` resolved. TanStack Query schedules its React re-render asynchronously, so there was a brief render where `pendingQuantities={}` and `cartData.line.quantity` was still stale — showing the old count.

Fix: defer the clear by one macro task so TanStack Query's state update lands in the same React batch:

```ts
// BEFORE
} finally {
  if (debounceRef.current === null) {
    setLocalQty(null)
    onPendingChange(line.id, null)
  }
}

// AFTER (success path)
setTimeout(() => {
  if (debounceRef.current === null) {
    setLocalQty(null)
    onPendingChange(line.id, null)
  }
}, 0)
```

## Files Changed

- `apps/mobile/hooks/useCart.ts` — `itemCount` counts distinct `CartLine` nodes
- `apps/mobile/components/shop/CartSheet.tsx` — `optimisticItemCount` counts distinct `CartLine` nodes; success-path clear deferred by `setTimeout(0)`

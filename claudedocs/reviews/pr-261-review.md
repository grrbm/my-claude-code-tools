# PR #261 Review — `perf: launch-readiness performance pass (P0/P1 bundle)`

**Reviewer:** grrbm  
**Date:** 2026-05-13  
**Verdict:** ✅ Approve with comments — no blocking issues; one behavioral change worth acknowledging before merge.

---

## Summary

13 commits, 366/+103 across 19 files. This is a well-scoped bundle: image-loading perf, backend runtime migration, throttle observability, parallel PDP fetch, schema scaffolding for the reactive lifecycle follow-up (PR #262). The internal review ledger in the PR description is unusually thorough and I trust the prior passes caught the sharp edges.

---

## Non-blocking findings

### 1. `getForYouFeed` — upfront `Promise.all` changes failure semantics for multi-merchant feeds

**File:** `packages/convex/mobilev2/discoveryActions.ts`

```ts
const orgsWithSessions: Array<OrgWithSession> = await Promise.all(
  organizations.map(async (organization) => ({
    organization,
    session: await ctx.runAction(
      internal.shared.shopify.storefrontCore.getStorefrontSession,
      { organizationId: organization._id }
    ),
  }))
)
```

Before this refactor, `getStorefrontSession` was called inside `fetchInterestProducts` and `fetchSupplementalProducts` — one call per term per org, each wrapped in its own `tryCatch`. A misconfigured org (no Shopify session, revoked token) caused that org's products to be silently absent from the feed; other orgs still contributed.

After this refactor, a single session failure causes the entire `getForYouFeed` action to throw, returning nothing. For a multi-merchant setup this is a net regression in resilience, even if the perf win (N sessions instead of N×terms) is real.

**Suggested fix** (non-blocking, can land in PR #262 or a follow-up):

```ts
const orgsWithSessions: Array<OrgWithSession> = (
  await Promise.allSettled(
    organizations.map(async (organization) => ({
      organization,
      session: await ctx.runAction(
        internal.shared.shopify.storefrontCore.getStorefrontSession,
        { organizationId: organization._id }
      ),
    }))
  )
)
  .filter((r): r is PromiseFulfilledResult<OrgWithSession> => r.status === 'fulfilled')
  .map((r) => r.value)
```

If the current deployment is single-merchant only, this is low-urgency. But Joey's campaign bringing unbounded merchant signups is the stated context — worth hardening before that load arrives.

---

### 2. `combinedSearchTerm` — multi-word interest quoting deferred

**File:** `packages/convex/mobilev2/discoveryActions.ts`

```ts
const combinedSearchTerm = interestTerms.join(' OR ')
```

For multi-word interests (e.g. `"café racer"`), this produces `café racer OR sneakers`, which Shopify parses as `café OR racer OR sneakers`. The PR correctly calls this out as a deferred MEDIUM finding addressed in PR #262. Just confirming I see it and the merge order (261 → 262 within hours, not days) is load-bearing here.

---

### 3. `storefrontCore.ts` — breadcrumb exchange is module-level; shared across all client instances

**File:** `packages/convex/shared/shopify/storefrontCore.ts`

```ts
const operationStartedAt = new WeakMap<object, number>()
const shopifyBreadcrumbExchange = mapExchange({ ... })
```

Both the WeakMap and the exchange are module-level constants shared across every `createShopifyStorefrontClient()` call. The WeakMap keying on the urql `Operation` object (a unique reference per query) means there are no cross-client collisions — GC handles cleanup. This is safe as written. Noting it only so a future reader doesn't refactor it "for cleanliness" into a per-client closure without understanding why it works.

---

## What looks good

**PDP parallel fetch (`[productId].tsx`)** — Correct fix. `productId` from URL params is always available before the product resolves, so gating similar/complementary on `product?.id` was a purely unnecessary waterfall. The `enabled: Boolean(productId && orgId)` guard is right.

**`throttle.ts` extraction** — Clean, well-documented. The `graphQLErrors.some(e => extensions.code === 'THROTTLED')` check matches Shopify's documented throttle shape. The `SHOPIFY_THROTTLE_MESSAGE` string is user-appropriate.

**Schema additions** — `scheduledExpiryId: v.optional(v.id('_scheduled_functions'))` and `expiryVersion: v.optional(v.number())` are correctly optional. No consumers in this PR means no risk surface here; the consumer lands in PR #262.

**`images.ts` shared module** — Good consolidation. Three named constants (`PRODUCT_CARD_IMAGE_WIDTH`, `PRODUCT_THUMB_IMAGE_WIDTH`, `PRODUCT_HERO_IMAGE_WIDTH`) with cap values are cleaner than the previous inline `Math.min(Math.ceil(...), N)` at each call site. The `shopifyImageUrl` passthrough for non-Shopify URLs (user avatars, etc.) is the right guard.

**expo-image migration** — All 5 surfaces (FeedItem, ForYouFeed, RecentlyViewedSheet, ProductCard ×2, ProductImageCarousel) are consistent: `cachePolicy="disk"`, `contentFit="cover"`, `recyclingKey`. `ProductImageCarousel` correctly keeps `cachePolicy="memory-disk"` (as noted in #262's comment) given its revisit-heavy PDP back-nav pattern. Not changed in this PR — good.

**`findOrphanedExpiredGifts`** — Good design choice: on-demand diagnostic query instead of a polling cron. The `by_gift_status_and_expires` index scan with `.lt('expiresAt', threshold)` is efficient. The `hasScheduledExpiry: order.scheduledExpiryId !== undefined` field is the right diagnostic signal — a non-empty result with `hasScheduledExpiry: true` means the scheduled fire dropped, not that the scheduler wasn't set up.

**V8 migration of `discoveryActions.ts`** — The `withSentryNode` → `withSentry` swap is the right corresponding change. No Node.js-only imports left. The session-deduplication and OR-query consolidation are the highest-value individual changes in this PR.

**CLAUDE.md — scheduled-function rename contract** — This section is a good addition and follows the same structural rationale as the mobile-API-versioning rule it's modelled on. The `_scheduled_functions` query snippet for pre-deletion verification is a useful operational reference.

---

## Operational checklist before campaign go-live (from PR description, confirming I've read it)

- [ ] Verify `BACKEND_SENTRY_DSN` is set on the Convex deployment and a sample `console.error` from `discoveryActions.ts` appears in Sentry within ~1 minute
- [ ] Upgrade Convex plan from Starter → Pro before campaign goes live (1000 concurrent sessions / 64 action slots is the real ceiling, not code)
- [ ] Merge order: PR #261 → PR #262 within hours, not days (MEDIUM cart-deletion-on-throttle finding is fixed in #262)

---

> Overall: the work is solid. The single behavioral concern (Promise.all failure mode) is worth tracking but doesn't block merge given the current single-merchant deployment. Flag it for PR #262 or an immediate follow-up.

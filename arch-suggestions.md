# Architecture sync — suggestions (2026-07-13)

**1. [Reuse/consistency] — New shared sheet primitive, same duplication it was built to fix**
We just shipped `ContentBottomSheet` (apps/mobile/components/sheets/ContentBottomSheet.tsx) specifically to stop backdrop/ref/dismiss plumbing from being hand-rolled per sheet — but only 3 of roughly 13 bottom sheets use it (RecentlyViewedSheet, RecipientWishlistSheet, SaveToWishlistSheet). The other 10 — CommentsSheet, GiftSentSheet, OrderSheet, NotificationsSheet, DataPrivacySheet, ContactSupportSheet, FriendOptionsSheet, NotificationPrimerSheet, WishlistSharePreflightSheet, BaseFilterSheet — still each redefine the same forwardRef + BottomSheetModal + BottomSheetBackdrop scaffolding the primitive exists to replace. Worth a team call: backfill the migration, or is it meant to be opt-in going forward?

**2. [UX friction] — Three recently-reworked flows, four different error-state paradigms, no shared component**
PDP's top-level fetch error is a full-screen icon+title+dual-CTA block built inline (apps/mobile/app/[orgId]/p/[productId].tsx:879-912). Search has its own hand-rolled error block — worded and laid out differently in three places in the same file (components/search/SearchResultsGrid.tsx:76-99, 106-129, 181-197). Onboarding uses native `Alert.alert` dialogs with no retry affordance (app/onboarding.tsx:259-264, 317-323) — a third, OS-native paradigm — while its own AccountSetupGate.tsx:70-127 implements a fourth, closer to PDP's style but still a separate component. On top of that, PDP's "similar products" / "complementary products" shelves swallow fetch errors and empty results entirely — no error state, no skeleton, no "nothing found" copy, just `null` (product/[productId].tsx:129-163) — unlike search's polished, purpose-built empty states (SearchEmptyState.tsx, SearchZeroResults.tsx). Worth standardizing on one error/empty-state component before the next flow gets rebuilt with its own variant.

**3. [Product growth] — A sent gift gets zero reminder before it's refunded**
Gift expiry is scheduled once, at the terminal deadline only (mobile/orderRecords.ts:1346-1356, `expiresAt = now + GIFT_EXPIRY_MS` → single `ctx.scheduler.runAt`). There's no earlier warning: the notification-type enum (schema.ts:90-100) has `gift_expired` but no `gift_expiring_soon`. So a sender whose gift sits in `pending_claim` for the full window gets no "your gift to X hasn't been claimed, N days left" nudge — the first signal they get is that the charge is already being refunded. A pre-expiry reminder would reuse the exact same scheduler pattern already in place for the terminal expiry, just fired earlier.

**4. [UI/Animation] — Is this gift wrap screen complete as is ? Should we animate it to unwrap ?**

<img width="345" height="704" alt="Screenshot 2026-07-13 at 15 50 39" src="https://github.com/user-attachments/assets/71e0fc54-ad5a-46f7-b734-83d0e544783e" />

**5. [UI/Animation] — When we changed the old "GiftIt" splash screen to the new one, we lost the logic that eagerly loaded the feed items; so the app launches with unloaded ForYouFeed items, which looks bad and kinda sluggish.**

<img width="345" height="704" alt="image" src="https://github.com/user-attachments/assets/e5426891-35d0-4fbd-a48e-b7dce685c3af" />

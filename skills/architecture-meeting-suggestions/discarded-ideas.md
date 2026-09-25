# Discarded ideas — architecture-meeting-suggestions

This is this skill's own memory, local to this skill directory (not the
Claude global auto-memory system). It exists so a discarded idea never
gets re-proposed in a later run, even reworded.

Checked at Step 3 (fresh feature brainstorming) before generating
candidates — never re-propose an idea listed here, even under a
different name, if it's the same underlying concept. Systemic
suggestions can be discarded the same way; they're rarer since they're
grounded in current codebase state, but list them below if it happens.

Appended to any time the user discards, rejects, or says not to suggest
an idea again — whether that happens mid-run, while reviewing a run's
output (e.g. a draft PR), or completely out of band in a later
conversation. Each entry: the idea's headline, a one-line description
(enough to recognize it even if reworded later), the date discarded, and
the source (PR link, or "conversation" if there's no artifact).

## Fresh feature ideas

### Gifting Wrapped
Spotify Wrapped-style annual recap card of gifts sent/received and top friend.
Discarded 2026-09-15 — source: [PR #624](https://github.com/ShopIt-LLC/shopit-monorepo/pull/624).

### Chip In on a Gift
Amazon Registry / GoFundMe-style group contribution letting several friends split one gift's cost.
Discarded 2026-09-15 — source: [PR #624](https://github.com/ShopIt-LLC/shopit-monorepo/pull/624).

### Seen By on Wishlist & Sizes/Style
Instagram Stories-style "seen by" viewer list for wishlist items or the sizes & style brief.
Discarded 2026-09-15 — source: [PR #624](https://github.com/ShopIt-LLC/shopit-monorepo/pull/624).

### "Ask before asking" push-notification primer
Full-screen explainer (Duolingo-style) shown before the native iOS notification permission dialog, plus a personalised bottom-sheet variant after sending a gift. Discarded as excessive / not needed after manually reviewing its pen design.
Discarded 2026-09-21 — source: [PR #649](https://github.com/ShopIt-LLC/shopit-monorepo/pull/649).

### STANDING RULE: nothing about non-US / international support
Never suggest features about other countries, regions, currencies, languages, localization or international shipping/waitlists. Brazil and Ecuador phone sign-in exist for the devs only; the application is US-focused. This applies to fresh feature ideas AND systemic suggestions.
Added 2026-09-18 — source: conversation.

### WhatsApp code option for phone sign-in
"Send code via WhatsApp" next to SMS on the sign-in code step, aimed at Brazil/Ecuador numbers (non-US, see standing rule).
Discarded 2026-09-18 — source: [PR #649](https://github.com/ShopIt-LLC/shopit-monorepo/pull/649).

### "We don't ship there yet" waitlist for non-US users
Tell non-US phone numbers that shipping is U.S.-only and offer a "notify me" waitlist capture (non-US, see standing rule).
Discarded 2026-09-18 — source: [PR #649](https://github.com/ShopIt-LLC/shopit-monorepo/pull/649).

## Systemic suggestions

(none yet)

The standing rule above (no non-US / international support suggestions) applies here too.

---
name: refactor-big-file
description: Split an oversized source file (e.g. a 2000+ line React Native/TypeScript component file like apps/mobile/components/shop/CartSheet.tsx) into smaller, modular files/components without changing behavior. Use when asked to "break up", "split", "modularize", or "extract components from" a large file, or when a file has grown unwieldy and needs to be divided into per-component/per-function files. This is a pure structural refactor — logic must stay byte-for-byte equivalent.
---

Split a large file into smaller modules while guaranteeing the code behaves
identically before and after. The core discipline: **move code verbatim,
wire up imports second**. Never rewrite from memory in the same step as
extracting — that's how subtle behavior changes sneak in.

## Step 0 — Check for lock markers first

Before touching the target file, check whether it (or the component inside
it) is a **locked component** per this repo's CLAUDE.md rule. Search for
"DO NOT MODIFY" / lock-section markers in AGENTS.md and check recent git log
for "lock" commits touching the file. If it's locked, mention this to the
user and stop — do not extract from it unless the user gives the explicit
bypass phrase. If a locked-component finding was already raised and declined
in a prior session, don't re-raise it without the bypass phrase.

## Step 1 — Read everything before touching anything

- Read the full target file top to bottom (not just a chunk — the whole
  file). Note its imports, module-level constants, exported types, and the
  overall component/function boundaries.
- If there is a source ticket (Linear issue) or spec for this refactor, fetch
  it and read the full description *and every comment*. Extraction plans
  often live in ticket comments: which pieces go where, shared constants,
  "must preserve" invariants, explicit "not in scope" items, test remap
  instructions. Treat these as binding — they override generic judgment
  calls below.
- Grep the repo for any tests that pin against the target file's *source
  text* (see Step 6) so you know up front what you'll need to update.

## Step 2 — Build the extraction inventory

Before editing, write out (in your own working notes, not a repo file) a
table of:

| Piece (component/function/type) | Target file | Line range in original | Notes |

Group pieces sensibly:
- One file per component is the default in this repo (see
  `apps/mobile/components/shop/product/` — `ProductDescription.tsx`,
  `VariantSelector.tsx`, `RatingStars.tsx`, `ImageOverlayIconButton.tsx`,
  `ProductMetafields.tsx`, `ProductImageCarousel.tsx` are each one
  component per file).
- Small, tightly-coupled helpers that only make sense next to one component
  (e.g. a tiny local formatter used by exactly one extracted component) can
  share that component's file. Don't invent a shared file for something used
  in one place.
- Don't over-fragment: a helper function used only inline for readability
  doesn't need its own file just because the parent file is big. Extract
  along real component/responsibility boundaries, not arbitrarily by line
  count.
- Follow the ticket's plan for naming/placement if one exists; only fall
  back to your own judgment where the ticket is silent.

Do not start editing until this inventory is complete — it's what keeps the
move from turning into an ad hoc rewrite.

## Step 3 — For each piece: verbatim copy, then wire the new file

For every row in the inventory, in order:

1. **Copy the exact original code** (same logic, same formatting, same
   variable names) into the new file. Use Read on the precise line range and
   reproduce it exactly — do not retype from memory or "clean it up" while
   moving. If you want to reformat or simplify, that is a separate follow-up
   step after the move is verified, never combined with it.
2. Add whatever imports the new file needs for the copied code to compile
   (React/RN imports, `@shopit/*` package imports, `@/lib`, `@/hooks`,
   `@/components/ui`, etc.). Follow this repo's import grouping/order as
   seen in the original file: side-effect-free React/RN core imports first,
   then external packages, then `@shopit/*` workspace packages, then local
   `@/...` imports, then `type`-only imports last (often re-grouped with a
   blank line, see `CartSheet.tsx` and `product/ProductImageCarousel.tsx`
   for the pattern).
3. Export the piece. Match this repo's convention: components are named
   function exports (`export function ComponentName(...)`), not default
   exports. Props types are local `interface ComponentNameProps { ... }`
   (not usually exported) unless a ref type or shared type is genuinely
   needed elsewhere, in which case export it explicitly (see
   `ProductImageCarousel.tsx`'s exported `ProductImageCarouselRef`, and
   `CartSheet.tsx`'s exported `PromoCodeRowRef`).
4. Styling stays as-is: this repo uses NativeWind `className` strings on
   RN components (`View`, `Text`, `TouchableOpacity`, ...), not
   `StyleSheet.create`. Don't convert styling approaches while moving code.
5. Type-check just this new file in isolation once it's copied (or note
   compile errors to resolve) before moving to the next piece — catching
   missing-import errors early is cheaper than debugging a batch of them
   later.

## Step 4 — Replace the moved code in the original file

Only after a piece's new file is copied and compiling:

1. Go back to the original file and **delete** the code that was moved
   (the exact range from your inventory).
2. Replace it with an import of the new file and a usage site
   (`<ComponentName {...props} />` or a direct function call, matching how
   it was invoked before).
3. Do not touch surrounding code while doing this — the diff at this point
   should be "removed lines X-Y, added one import line + one usage line",
   nothing else nearby should shift.

Never interleave step 3 (build new file) and step 4 (strip original) across
different pieces in a way that leaves the original file in a broken
intermediate state for long — extract-and-wire one piece at a time,
verifying it still compiles, before starting the next.

## Step 5 — Shared module-level constants

If a constant, type, or small helper is used by *both* the original file and
one or more extracted files (or by multiple extracted files), it must have a
**single source of truth** — do not copy it into each file that uses it.
Options, in order of preference:
1. If it already lives in a shared location (`@shopit/shared`, `@/lib/...`),
   just import it from there in every file that needs it — nothing to move.
2. If it's local to the original file and now genuinely shared across the
   split pieces, hoist it into whichever file is the most natural owner
   (often the file that still contains the parent/orchestrating component)
   and export it, then import it from the others.
3. Never end up with the same constant/type defined twice — that's a
   silent behavior-change risk if one copy drifts from the other later.

## Step 6 — Update source-pinning tests

Some tests in this repo assert against a file's literal source text rather
than rendering it (because NativeWind `className` can't render in Jest —
see `apps/mobile/lib/__tests__/contentBottomSheetContract.test.ts` and
`giftAccessibilityContract.test.ts` for the pattern: they `fs.readFileSync`
a specific file path and `expect(source).toContain('...')` on exact
snippets, including `testID`/`testIDPrefix` string literals).

Before finishing:
1. Grep for any test that reads the original file's path
   (`readSource('apps/mobile/components/.../OriginalFile.tsx')` or similar)
   or asserts on a string/testID that lived in a range you moved.
2. If the asserted snippet moved to a new file, update the test to read the
   new file path instead (don't just delete the assertion — repoint it).
3. If a testID or exact string was part of what got extracted, confirm the
   test still targets the file where that string now actually lives.

## Step 7 — Type-check and test

- Run type-check for the affected package (faster than the whole repo):
  `cd apps/mobile && bun run type-check` (or the specific package touched).
- Run the relevant test suite: `bun run test` (root `turbo test`) or scope
  to the affected package/test file.
- Fix only regressions in files you touched. Pre-existing unrelated type
  errors elsewhere in the repo are not your concern (per this repo's
  CLAUDE.md).

## Step 8 — Final diff review

Before reporting done, review the full diff (`git diff`) end to end and
confirm:
- Every hunk in the **new** files is a verbatim copy of the original code
  (only import additions and the `export` keyword should differ from the
  original text).
- Every hunk in the **original** file is a deletion of moved code plus an
  added import + usage line — no incidental logic edits, renamed variables,
  reformatted JSX, or "while I'm here" fixes.
- No constant/type/helper got duplicated (Step 5).
- No new file was created for something that didn't need its own file
  (Step 2's fragmentation check).
- Any pinning tests you updated (Step 6) point at the correct new file.

If the diff shows anything beyond a structural move, stop and fix it before
calling the refactor done — a passing type-check does not prove behavior is
unchanged, only the diff review does.

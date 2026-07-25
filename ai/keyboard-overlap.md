# Keyboard Overlap in Bottom Sheets

**When a virtual keyboard covers content inside a `@gorhom/bottom-sheet` modal, fix it by adjusting `snapPoints` — not with `KeyboardAvoidingView` or layout padding.**

---

## Why snapPoints, not KeyboardAvoidingView

Claude cannot see where components render on a physical device or simulator. `KeyboardAvoidingView` offset guesses are error-prone and hard to verify blindly. Snap points are declarative and predictable: a sheet at `75%` will always sit above a standard iOS keyboard (~40% of screen height). The fix is visible and testable without needing to see the screen.

---

## The pattern (AuthSheet reference)

`apps/mobile/components/auth/AuthSheet.tsx` is the canonical example:

```tsx
<BottomSheetModal
  ref={sheetRef}
  index={1}
  snapPoints={['25%', '45%']}         // start at 45% — clears keyboard
  enableDynamicSizing={false}
  keyboardBehavior="interactive"       // sheet rises with keyboard
  keyboardBlurBehavior="restore"       // snaps back when keyboard closes
  android_keyboardInputMode="adjustResize"
>
```

- `keyboardBehavior="interactive"` — the sheet moves up as the keyboard appears, keeping inputs visible.
- `keyboardBlurBehavior="restore"` — sheet returns to its snap point when keyboard closes.
- `android_keyboardInputMode="adjustResize"` — equivalent behavior on Android.

---

## How to fix keyboard overlap

1. **Start at 50%** as the active snap point (index pointing to it). This is a safe default that clears the keyboard on all iPhone sizes.
2. Check the result on device. If content is still clipped, increase to `65%` or `75%`.
3. Always pair with `keyboardBehavior="interactive"` and `keyboardBlurBehavior="restore"`.
4. Set `enableDynamicSizing={false}` — required when using explicit `snapPoints`.

```tsx
// Before: content hidden behind keyboard
snapPoints={['30%']}

// After: sheet tall enough to clear keyboard
snapPoints={['30%', '55%']}
index={1}
keyboardBehavior="interactive"
keyboardBlurBehavior="restore"
android_keyboardInputMode="adjustResize"
```

---

## What NOT to do

```tsx
// ❌ — unreliable, requires seeing the screen to tune offset
<KeyboardAvoidingView behavior="padding" keyboardVerticalOffset={80}>

// ❌ — dynamic sizing conflicts with snapPoints
enableDynamicSizing={true}
snapPoints={['50%']}
```

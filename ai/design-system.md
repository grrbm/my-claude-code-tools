# Design System Components (handle with care)

`Button` and `Input` in `apps/mobile/components/ui/` were recently standardized by the senior dev. Treat them as owned by someone else — change them only when strictly necessary, and **always report every change made** so the team stays in sync.

**`Button.tsx`**
- Variants: `primary` | `secondary` | `tonal` | `plain` | `ghost` | `glass`
- Sizes: `xs` | `sm` | `md` (default) | `lg` | `icon`
- Heights: `h-12` (48px) for `md`/`lg`, `h-10` (40px) for `sm`/`xs`
- All sizes use `rounded-full` — do not add mixed radius
- Uses CVA (`class-variance-authority`) for variants — add new variants there, not via ad-hoc `className`

**`Input.tsx`**
- Variants: `animated` (default, floating label) | `classic` | `underlined`
- Standard height: 48px | Standard radius: `rounded-2xl`
- Props: `label`, `error`, `isPassword`, `leftElement`, `rightIcon`, `isMultiline`, `inRow`, `variant`
- `leftElement` renders inside the input row (e.g. country code prefix) — use this instead of wrapping with custom Views
- **Never use NativeWind text-size classes on `TextInput`** (`text-base`, `text-xl`, etc.) — they inject `lineHeight` and break iOS vertical centering. Use inline `style={{ fontSize: 16 }}` or the shared `<Input>` component instead of raw `TextInput`

**When you modify either file, include in your response:**
1. Which file and which prop/variant/style was changed
2. Why the existing API couldn't cover the need
3. A one-line summary the user can forward to the senior dev (e.g. "Added `loading` prop to Button — shows ActivityIndicator in place of children while `isSubmitting` is true")

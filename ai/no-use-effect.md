# No useEffect

**Never use `useEffect`.** Every use case has a better alternative in this stack.

---

## Replacements by category

### 1. Data loading / fetching
Use `useQuery` (Convex reactive subscription) or `useAction` + TanStack Query.
`useQuery` opens a live WebSocket subscription — Convex pushes updates automatically when underlying data changes. No fetch trigger needed.

```ts
// ❌
const [order, setOrder] = useState(null)
useEffect(() => { fetchOrder(id).then(setOrder) }, [id])

// ✅
const order = useQuery(api.mobilev2.orders.getOrder, { id })
```

Conditional / dependent queries use `'skip'`:
```ts
const user = useQuery(api.users.getMe)
const orders = useQuery(api.mobilev2.orders.list, user ? { userId: user._id } : 'skip')
```

One-shot fetches use `useAction` + TanStack Query:
```ts
const getTrending = useAction(api.mobilev2.discoveryActions.getTrending)
const { data } = useQuery({ queryKey: ['trending'], queryFn: () => getTrending({ limit: 6 }) })
```

---

### 2. Derived / synced state
Compute inline from query results. React Compiler handles memoization.

```ts
// ❌
const [isExpired, setIsExpired] = useState(false)
useEffect(() => { setIsExpired(gift?.status === 'expired') }, [gift])

// ✅
const gift = useQuery(api.mobilev2.gifts.getGift, { giftId })
const isExpired = gift?.status === 'expired'
```

---

### 3. User-triggered side effects
Put the side effect directly in the event handler.

```ts
// ❌
const [submitted, setSubmitted] = useState(false)
useEffect(() => { if (submitted) doSomething() }, [submitted])

// ✅
function handleSubmit() { doSomething() }
```

---

### 4. Screen focus / blur effects
Use `useFocusEffect` from `expo-router`.

```ts
// ❌
useEffect(() => { markAllRead() }, [])

// ✅
useFocusEffect(useCallback(() => { markAllRead() }, []))
```

---

### 5. Interval / countdown timer
Use `useSyncExternalStore` with an external interval, or a dedicated interval utility.

```ts
// ❌
useEffect(() => {
  const t = setInterval(() => setCooldown(c => c - 1), 1000)
  return () => clearInterval(t)
}, [cooldown])
```

Instead, manage the interval in an external store (outside React) and subscribe with `useSyncExternalStore`, keeping React as a pure display layer.

---

### 6. One-time app initialization (permissions, tracking, deep links)
Move setup outside the React tree — call it in the app bootstrap before rendering, not inside a component.

```ts
// ❌  (inside a component)
useEffect(() => {
  initializeTracking()
  requestNotificationPermission()
}, [])

// ✅  (in app entry point, before <App /> renders)
await initializeTracking()
await requestNotificationPermission()
renderApp()
```

---

### 7. Navigation reactions
Convex reactive queries driving render state eliminate the need to "react" to changes imperatively. If a value changes and a navigation should happen, derive it from query state or trigger it directly from the mutation callback.

```ts
// ❌
useEffect(() => { if (redirectHref) router.replace(redirectHref) }, [redirectHref])

// ✅ — call router.replace() directly inside the mutation's onSuccess / callback
```

---

### 8. Reanimated animation triggers
Set the initial `useSharedValue` to the target and use `withDelay`/`withSpring` at declaration time, or trigger the animation directly in an event handler.

```ts
// ❌
useEffect(() => { opacity.value = withTiming(isReady ? 1 : 0) }, [isReady])

// ✅ — trigger in the event/callback that changes isReady, or derive with useAnimatedStyle
```

---

## Summary table

| Pattern | Instead of useEffect, use |
|---|---|
| Load data | `useQuery` / `useAction` + TanStack |
| Derived state | Inline computation |
| User-triggered side effect | Event handler |
| Screen focus effect | `useFocusEffect` (expo-router) |
| Interval / timer | `useSyncExternalStore` + external interval |
| App init (permissions, tracking) | Bootstrap outside React tree |
| Navigation reaction | Call directly in mutation callback |
| Animation trigger | `withDelay` initial value or event handler |

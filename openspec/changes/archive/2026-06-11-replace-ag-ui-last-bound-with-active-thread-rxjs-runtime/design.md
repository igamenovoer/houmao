## Context

The AG-UI workbench has grown from a simple protocol harness into a multi-pane runtime. It now coordinates AG-UI connect and run streams, watched-target reconnect loops, client event cache writes, passive discovery, Debug Agent relay state, tmux session listing and WebSocket attachment, gateway destination fallback, and user-driven pane state.

Most of this behavior currently lives in React components and hooks through `useEffect`, refs, local state, `setTimeout`, `AbortController`, and ad hoc callbacks. That pattern is manageable for one stream at a time, but it becomes fragile when the GUI must coordinate one gateway state across several panes. The new active-thread behavior is the clearest example: many panes may watch or display the same gateway, but only one shared active-thread poller should exist for that gateway.

The previous tmux-tab change introduced `last-bound-thread`, where the GUI implicitly updated the gateway default destination when a discovered pane connected, retargeted, or became foreground. The revised design replaces that with an explicit gateway `active-thread` selected by a user action or by a pane connect action. The gateway still keeps `last-sent-thread`, but only as bookkeeping after concrete non-sink publishes. It no longer uses last-sent state as a fallback destination.

## Goals / Non-Goals

**Goals:**

- Add RxJS as the primary browser runtime event facility for the AG-UI workbench.
- Centralize long-lived workflows in a workbench runtime layer rather than scattering them through pane components.
- Replace `last-bound-thread` with gateway `active-thread`.
- Make active-thread selection explicit through a pane control, with a gray inactive state and green active state.
- Automatically set active-thread when a discovered Houmao agent pane connects to its gateway.
- Poll active-thread status at a 1 second default interval and share one poller per gateway.
- Preserve inactive pane behavior: inactive panes still receive and render events addressed to their exact thread.
- Keep `last-sent-thread` as gateway-owned bookkeeping only.
- Change omitted-route publish fallback to explicit destination, then active-thread, then default sink.
- Preserve client persistence boundaries, especially no raw tmux terminal bytes in browser persistence and no accidental replay buffers for sensitive stream content.

**Non-Goals:**

- Do not rewrite every component into RxJS in one step.
- Do not replace React rendering, Dockview ownership, xterm DOM ownership, or local editor input state with RxJS.
- Do not make active-thread durable across gateway restarts.
- Do not use `last-sent-thread` for routing fallback.
- Do not add gateway replay storage for missed GUI events.
- Do not make RxJS part of host-side Vite plugins in this change.
- Do not require third-party AG-UI endpoints to understand Houmao active-thread routes.

## Decisions

### Add a Workbench Runtime Layer

Introduce an RxJS runtime under `apps/ag-ui-workbench/src/runtime/` or equivalent:

```text
runtime/
  actions.ts
  state.ts
  workbenchRuntime.ts
  selectors.ts
  react.ts
  effects/
    activeThreadEffects.ts
    agUiEffects.ts
    discoveryEffects.ts
    storageEffects.ts
    tmuxEffects.ts
    watchedTargetEffects.ts
```

The runtime owns a single action stream, a reduced state stream, and effect subscriptions:

```text
actions$ ─────► reducers via scan ─────► state$
   │                                      │
   └──────► effects ─────► actions$ ◄────┘
```

React components dispatch actions and subscribe to selectors through a small adapter, preferably implemented with `useSyncExternalStore` to avoid tearing under React concurrent rendering.

Alternative considered: add RxJS only inside specific hooks. That keeps the current fragmentation. A runtime layer gives the workbench one consistent place for cancellation, polling, reconnects, persistence, and cross-pane coordination.

### Keep React as the Rendering and Imperative-Island Boundary

React remains responsible for visible component rendering, Dockview component mounting, short-lived form input state, and imperative DOM integrations such as xterm attachment. RxJS emits view models and lifecycle commands; it does not directly render.

Examples:

- Prompt textarea text can remain local React state until submitted.
- xterm `Terminal` instances remain local to `TmuxTabPanel`, but socket lifecycle and tmux status events are represented in the runtime.
- Dockview panel creation and close operations may remain in `App`, but persistent pane records and cross-pane state flow through runtime actions.

Alternative considered: move all state into RxJS immediately. That would increase blast radius and make the first RxJS change harder to review. The runtime should first own workflows that cross pane boundaries or require cancellation.

### Replace Last-Bound Thread With Active Thread

Gateway destination state becomes:

```ts
interface AgUiDestinationState {
  activeThread: {
    status: "empty" | "active";
    threadId: string | null;
    updatedAtUtc?: string;
    source?: "gui_button" | "gui_connect" | "manual";
  };
  lastSentThread: {
    status: "empty" | "sent";
    threadId: string | null;
    updatedAtUtc?: string;
    source?: "explicit" | "event" | "connection" | "active_thread";
  };
}
```

Expose active-thread through Houmao gateway extension routes:

```text
GET    /v1/ag-ui/destination
GET    /v1/ag-ui/active-thread
PUT    /v1/ag-ui/active-thread
DELETE /v1/ag-ui/active-thread?threadId=<expected-thread>
```

The `DELETE` route should accept an optional expected thread id. If present, the gateway clears active-thread only when the current active thread matches. This prevents a closing stale pane from clearing a newer active pane.

Alternative considered: keep `/bindings/last-thread` and rename only UI text. That preserves misleading semantics. The route and model should use active-thread vocabulary because this is an intentional default destination, not a historical binding.

### Publish Fallback Uses Active Thread, Not Last Sent

Gateway publish routing order becomes:

1. Explicit request route, explicit connection id, explicit run route, or a single consistent event-level thread id.
2. Gateway active-thread.
3. Gateway default sink.

`last-sent-thread` is refreshed after concrete non-sink sends from explicit or active-thread routes. It is diagnostic state only and never participates in route resolution.

The current default sink behavior remains: accept the valid event batch, emit safe diagnostics, perform no GUI fanout, and return `default_sink_due_to_no_destination`.

Alternative considered: keep last-sent as a fallback before active-thread. That can route a later omitted publish to whichever thread last received a graphic, which is exactly the surprising behavior this change removes.

### Active Thread Is Shared Gateway State, Not Pane-Local State

The workbench runtime computes a normalized gateway key from a discovered pane's AG-UI base URL. For every gateway key with at least one interested pane, the runtime owns one active-thread poller:

```text
Pane A ─┐
Pane B ─┼── subscribe ──► activeThreadPoller(gatewayKey) ── GET /active-thread every 1s
Pane C ─┘
```

Pane active indicators derive from comparing the pane's current thread id with the gateway active-thread state:

```text
green   activeThread.threadId === pane.target.threadId
gray    activeThread.threadId !== pane.target.threadId
error   active-thread read failed or gateway extension unavailable
```

Alternative considered: each pane polls active-thread independently. That creates duplicate network traffic and opens race-prone local state. One poller per gateway is simpler and more accurate.

### Pane Connect Auto-Activates the Thread

When a user activates Connect on an eligible discovered Houmao agent pane, the runtime dispatches an active-thread set action with source `gui_connect`. This is intentionally different from passive background watcher reconnects. Watchers may open SSE streams, update caches, and render events, but they do not call `PUT /active-thread`.

The active-thread button uses source `gui_button`. A manual CLI caller or test can use source `manual`.

Alternative considered: only the explicit button sets active-thread. That makes the common "open pane and connect" workflow require an extra click and increases the chance that tmux-controlled graphing goes to the default sink.

### Inactive Panes Continue Receiving Explicitly Addressed Events

Active-thread controls only omitted-route publishing. AG-UI streams subscribed to a concrete thread remain normal live streams. If an agent publishes with `--thread-id beta-thread`, the beta pane can receive and render it even when alpha is the active thread.

This distinction must be visible in tests because otherwise users may interpret the green active marker as an exclusive subscription state.

### RxJS Should Avoid Raw Replay Buffers by Default

Use `share()` for live streams and explicit state reducers for view state. Avoid `ReplaySubject` or unbounded `shareReplay` for raw AG-UI events, WebSocket payloads, terminal bytes, request bodies, credentials, or prompt text. When a replay or cache is required, use the existing client-owned event cache policy and keep it scoped to watched AG-UI events.

Alternative considered: use replayed subjects everywhere to simplify React mounting. That risks retaining sensitive content and makes persistence boundaries harder to prove.

### Migrate in Layers

The first implementation layer should add the runtime and move active-thread behavior into it. The second should move watched-target lifecycle because that hook currently owns reconnect backoff, connect streams, event cache writes, and resolved-target updates. The third should move AG-UI run/connect and tmux attach workflows.

This order gives immediate value without requiring a full GUI rewrite.

## Risks / Trade-offs

- RxJS misuse can create hidden subscriptions and leaks → Keep runtime construction explicit, use `takeUntil` and teardown tests, and expose selectors instead of raw subjects.
- React and RxJS can duplicate state if boundaries are vague → Define a runtime-owned state list and keep local component state only for short-lived form/DOM concerns.
- Active-thread polling can overload gateways when many panes exist → Use one shared poller per gateway key and stop polling when no pane is interested.
- Stale active-thread after browser close can route omitted publishes to a thread with no live listener → Preserve live-only delivery counts and keep zero-delivery reporting clear.
- Conditional clear can be missed by older gateways → Treat 404 or extension-unavailable reads as a visible inactive/error state, not as a fatal pane failure.
- Renaming routes is breaking for recently added code and tests → This project is still unstable; prefer the clear active-thread vocabulary over compatibility shims unless a test fixture needs a short transition helper.
- RxJS can retain sensitive stream content → Avoid replay buffers for raw stream bytes and add persistence/leak tests around localStorage, IndexedDB, and runtime snapshots.

## Migration Plan

1. Add `rxjs` to the workbench package.
2. Add the runtime shell, action types, state types, selectors, and React adapter.
3. Rename gateway destination state and routes from last-bound-thread to active-thread.
4. Change gateway publish fallback to explicit destination, active-thread, then default sink.
5. Keep last-sent updates after concrete publishes and remove last-sent fallback behavior.
6. Move workbench active-thread set, clear, and poll behavior into the runtime.
7. Add pane active-thread button and connect-time activation through runtime actions.
8. Move watched-target lifecycle into runtime effects.
9. Move AG-UI run/connect stream orchestration into runtime effects while preserving pure reducers.
10. Move tmux status, sessions, and attach socket lifecycle into runtime effects where it reduces component-local async code.
11. Update README, skill guidance, and publish helper wording.
12. Remove obsolete `last-bound-thread` route/client names and tests.

Rollback is straightforward before archive: restore last-bound route names and previous fallback ordering, remove RxJS runtime usage, and keep component-local hooks. After archive, rollback should be a new change because route names and skill guidance are user-visible.

## Open Questions

- Should `GET /v1/ag-ui/destination` keep the older `/bindings` alias during one development cycle, or should this unstable branch break immediately?
- Should active-thread poll failures show a yellow unknown state or a red error state in the pane header?
- Should a user be able to clear the active thread from the active pane button, or should the button only set active and a separate menu clear it?
- Should debug-agent panes ever participate in active-thread, or should active-thread remain limited to discovered Houmao agent panes?

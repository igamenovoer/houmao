## Context

The active-thread RxJS work added the first runtime boundary for the AG-UI workbench, but most long-lived browser workflows still live in React hooks and pane components. Watched-target reconnect loops, AG-UI connect streams, AG-UI run streams, tmux status refresh, tmux WebSocket attachment, and cache writes each keep their own timers, abort controllers, connection ids, and cleanup paths. That makes cross-pane behavior hard to reason about and leaves teardown spread across components.

This change assumes the active-thread RxJS runtime from `replace-ag-ui-last-bound-with-active-thread-rxjs-runtime` is present. If that change remains unarchived, this refactor should be implemented after it or in the same branch order so the runtime shell, active-thread actions, and active-thread polling services already exist.

## Goals/Non-Goals

Goals:

- Make the RxJS workbench runtime the owner of long-lived browser lifecycles: watched targets, AG-UI connect/run streams, tmux refreshes, tmux attachments, gateway active-thread polling, cancellation, and teardown.
- Define typed runtime actions, state, selectors, and services for pane lifecycle, target changes, watched-target reconciliation, AG-UI stream state, tmux state, runtime errors, and persistence/cache effects.
- Keep React responsible for UI-local state and DOM-owned objects: Dockview layout, form inputs, prompt text, measured canvas size, `Terminal`, `FitAddon`, and element refs.
- Preserve existing AG-UI request semantics, Houmao gateway routes, active-thread semantics, client event-cache semantics, typed graphics rendering, and durable storage formats.
- Keep sensitive or high-volume content out of replayed runtime state: raw terminal bytes, credentials, prompt text after dispatch, AG-UI request bodies, forwarded props, and unbounded raw event streams.

Non-goals:

- Do not change the AG-UI protocol or Houmao gateway route surface.
- Do not add gateway-side replay or server-side event caching.
- Do not move xterm.js `Terminal` or `FitAddon` objects into serializable runtime state.
- Do not redesign typed component rendering or Houmao component schemas.
- Do not preserve internal component-local lifecycle APIs that are replaced by runtime actions and selectors.

## Decisions

1. Runtime state will expose view models, not resource handles. `WorkbenchRuntimeState` will contain pane runtime summaries, watched-target summaries, AG-UI stream status, reduced AG-UI display state, tmux status/session lists, tmux attachment status, gateway active-thread status, and runtime errors. It will not contain `AbortController`, `WebSocket`, timer handles, raw terminal bytes, credentials, request bodies, or unbounded replay buffers.

2. Runtime effects will own non-serializable lifecycle resources. Effect-private maps will hold abort controllers, reconnect timers, connection ids, WebSockets, pending fetches, sequence counters, and tmux output sink registrations. Runtime teardown will dispose those maps through one `Subscription` boundary so tests and page unloads close all live resources.

3. Durable workbench configuration remains outside the runtime reducer. `App` and the existing storage layer remain the authority for localStorage-backed layout and target metadata. The runtime receives storage snapshots as typed actions and reconciles effects from those snapshots. For watched AG-UI events, the runtime uses the existing client event-cache service directly because cache writes are part of the watched stream lifecycle.

4. Watched targets will be reconciled from snapshots. When the watched-target set changes, runtime effects will start, stop, or retarget background connect loops. Each watcher will load cached events into reduced state, resolve discovered agents through the passive server when needed, open connect streams, append received watched events to the client cache, and retry with bounded backoff. Background watcher reconnects must not set active-thread.

5. Agent pane connect and run workflows will become runtime actions. A pane connect action will mark eligible discovered-agent panes active with source `gui_connect`, then ensure the target is watched or connected through runtime effects. A pane run action will carry the submitted prompt and compact canvas context as an action payload, start an AG-UI run effect, reduce received events into pane-visible state, and forget the prompt after the request is issued and the effect completes or is canceled.

6. Tmux refresh and attach workflows will become runtime effects with an explicit terminal sink bridge. Runtime effects will fetch tmux status, sessions, and discovered Houmao agents, own attach WebSockets, track attach status, and handle input/resize actions. `TmuxTabPanel` will keep the xterm DOM objects and register an ephemeral output sink keyed by pane or attachment id; runtime WebSocket output writes to that sink and is not replayed or persisted.

7. Pure AG-UI event reduction remains separate from effects. Stream effects parse and route protocol events, then call the existing pure reducer path for transcript, graphics, state, tool-call, activity, custom, error, and bounded raw timeline state. This keeps renderer behavior testable without live network streams.

8. React components will move to selectors and dispatches. `AgentSessionPanel`, `TmuxTabPanel`, and workbench context code should render derived runtime state through selector hooks and dispatch typed actions for user intent. Component-local timers, reconnect refs, stream abort refs, socket refs, and duplicated status state should be removed after the owning effect is migrated.

## Risks/Trade-offs

- A broad runtime can become a dumping ground. The boundary is restricted to lifecycle state and cross-pane view models; UI form state and DOM objects stay in React.
- Tmux output is high-volume and not naturally reducible. The sink bridge avoids replay buffers, but it requires careful registration cleanup when panes close or retarget.
- Having App own durable config while runtime owns live effects creates a two-layer contract. Snapshot actions and explicit persistence/cache services keep that contract concrete and testable.
- This refactor touches code also affected by the active-thread change. Implementation should start only after the active-thread runtime shell is available in the working tree.

## Migration Plan

1. Expand runtime contracts with typed actions, state slices, selectors, and service interfaces for panes, watched targets, AG-UI streams, tmux refresh/attach, cache writes, and teardown.
2. Move watched-target reconciliation and reconnect loops from `useWatchedTargets` into runtime effects while preserving cache loading, cache writes, clear-cache behavior, and passive resolution semantics.
3. Move agent-pane connect and run stream orchestration from `AgentSessionPanel` into runtime effects while preserving compact connect/run request bodies and active-thread behavior.
4. Move tmux status, session, and discovered-agent refresh workflows from `TmuxTabPanel` into runtime effects.
5. Move tmux attach WebSocket ownership into runtime effects and add the ephemeral terminal output sink bridge for xterm rendering.
6. Remove obsolete component-local lifecycle refs, timers, status state, and cleanup code after each runtime effect replaces it.
7. Add runtime tests with fake services and Playwright coverage for watcher reconnect, active-thread non-stealing, lifecycle teardown, tmux attach cleanup, and visible graphics after runtime migration.

## Open Questions

- The exact runtime module split can be chosen during implementation, but it should keep effect modules focused by workflow: watched targets, AG-UI streams, tmux, gateway active-thread, and storage/cache effects.
- A developer-facing runtime trace or debug panel could help future work, but this change should not add it unless needed to test the lifecycle migration.

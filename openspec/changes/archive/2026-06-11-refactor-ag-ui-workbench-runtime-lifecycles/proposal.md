## Why

The AG-UI workbench now has several long-lived browser workflows spread across React hooks and pane components: watched-target reconnect streams, agent run streams, tmux refreshes, tmux WebSocket attachment, event cache writes, and active-thread polling. The first RxJS layer proved useful for active-thread coordination; the remaining lifecycle code should move behind the same runtime boundary so cancellation, teardown, and cross-pane state are consistent.

## What Changes

- Move watched-target lifecycle ownership from `useWatchedTargets` into RxJS runtime effects while preserving reconnect backoff, passive resolution, event cache loading, and event cache writes.
- Move agent-pane AG-UI connect and run stream orchestration into runtime effects while preserving compact connect/run request bodies, canvas-size context, explicit thread targeting, and existing pure event reducers.
- Move tmux status/session refresh and tmux attach WebSocket lifecycle into runtime effects while keeping xterm `Terminal`, `FitAddon`, and DOM refs in React.
- Expand runtime actions and state to cover pane lifecycle, target changes, watched targets, AG-UI streams, tmux refresh/attach, runtime errors, and persistence triggers.
- Remove obsolete component-local timers, abort refs, reconnect counters, connection refs, and stream status once the runtime owns those workflows.
- Preserve the current persistence and security boundary: no raw terminal bytes, credentials, prompt text, request bodies, or unbounded replay buffers in reduced runtime state.
- Add runtime and Playwright coverage proving watcher reconnects do not activate gateway active-thread and proving lifecycle teardown closes timers, streams, and WebSockets.

## Capabilities

### New Capabilities

- `ag-ui-workbench-runtime-lifecycles`: Defines the workbench runtime ownership model for long-lived browser lifecycles, cancellation, teardown, and reduced state.

### Modified Capabilities

- `ag-ui-workbench-app`: Refines pane behavior so agent panes and tmux panes delegate long-lived AG-UI/tmux lifecycles to the runtime while React keeps UI-local and DOM-owned state.
- `ag-ui-workbench-client-event-cache`: Clarifies that watched-target cache writes are runtime-owned, bounded, and limited to watched AG-UI events.

## Impact

- Affected frontend code: `apps/ag-ui-workbench/src/runtime/**`, `App.tsx`, `workbenchContext.tsx`, `AgentSessionPanel.tsx`, `TmuxTabPanel.tsx`, and `ag-ui/useWatchedTargets.ts`.
- Affected tests: workbench Playwright suite and runtime unit-style tests under `apps/ag-ui-workbench/tests/`.
- No gateway route changes, no AG-UI protocol changes, and no durable storage format changes are intended.

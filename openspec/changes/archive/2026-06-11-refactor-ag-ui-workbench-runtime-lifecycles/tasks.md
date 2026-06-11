## 1. Runtime Contracts

- [x] 1.1 Confirm the active-thread RxJS runtime shell from `replace-ag-ui-last-bound-with-active-thread-rxjs-runtime` is present before starting implementation.
- [x] 1.2 Expand `apps/ag-ui-workbench/src/runtime/actions.ts` with typed actions for pane lifecycle, target changes, watched-target snapshots, watched-target cache clearing, AG-UI connect/run/cancel, tmux refresh/attach/input/resize/detach, runtime errors, and runtime disposal.
- [x] 1.3 Expand `apps/ag-ui-workbench/src/runtime/state.ts` with serializable view-model slices for panes, watched targets, AG-UI stream state, reduced AG-UI display state, tmux status/sessions/attachments, gateway active-thread state, and runtime errors.
- [x] 1.4 Expand `apps/ag-ui-workbench/src/runtime/selectors.ts` and `runtime/react.tsx` with selectors needed by agent panes, tmux panes, workbench context, and tests.
- [x] 1.5 Expand `WorkbenchRuntimeServices` with testable services for AG-UI client calls, passive discovery, event cache access, tmux client calls, timers, WebSocket creation, and storage snapshot inputs.
- [x] 1.6 Add effect-private resource registries for abort controllers, reconnect timers, connection ids, WebSockets, watcher sequence counters, and tmux terminal output sinks.
- [x] 1.7 Update runtime disposal so one teardown path cancels all subscriptions, timers, HTTP streams, WebSocket streams, sink registrations, and pending cache effects.

## 2. Watched Target Runtime Effects

- [x] 2.1 Replace `useWatchedTargets` lifecycle ownership with a runtime watched-target snapshot action derived from persisted workbench storage.
- [x] 2.2 Implement watched-target reconciliation in `runtime/effects/watchedTargetEffects.ts` so added, removed, and retargeted watched targets start or stop exactly one background connect loop per target.
- [x] 2.3 Move cached-event loading into the watched-target runtime effect and reduce loaded events into watched-target display state before live events arrive.
- [x] 2.4 Move passive-server resolution, capability fetch, AG-UI connect startup, detach cleanup, and bounded reconnect backoff into watched-target runtime effects.
- [x] 2.5 Move watched live-event cache writes into runtime effects while excluding request bodies, forwarded props, credentials, passive-server response bodies, mailbox content, memory content, and raw terminal content.
- [x] 2.6 Implement runtime actions for clearing one watched target cache and clearing all watched target caches while keeping watcher registration and reconnect state intact.
- [x] 2.7 Remove or shrink `apps/ag-ui-workbench/src/ag-ui/useWatchedTargets.ts` so it no longer owns timers, abort controllers, reconnect counters, connection ids, or watcher display state.

## 3. Agent Pane AG-UI Runtime Effects

- [x] 3.1 Wire `AgentSessionPanel` target changes, connect/watch, disconnect, clear-canvas, and pane disposal to runtime actions and selectors.
- [x] 3.2 Implement pane-owned AG-UI connect effect behavior for explicit connect actions that is separate from background watcher reconnects.
- [x] 3.3 Implement pane-owned AG-UI run effects that build compact `RunAgentInput` bodies, include canvas size only when measured, reduce stream events, and cancel on pane close or explicit cancellation.
- [x] 3.4 Preserve active-thread behavior so user-initiated eligible connect sets active-thread with source `gui_connect`, while background watcher startup and reconnect never set active-thread.
- [x] 3.5 Ensure runtime run effects do not retain prompt text, request bodies, forwarded props, credentials, or unbounded raw stream replay in reduced runtime state.
- [x] 3.6 Remove obsolete `AgentSessionPanel` reconnect timers, abort refs, connection id refs, duplicated stream status state, and dead connect-loop code after runtime effects own those workflows.
- [x] 3.7 Keep prompt editor state, target form editing, measured canvas size, and rendered DOM local to React components.

## 4. Tmux Runtime Effects

- [x] 4.1 Move tmux status fetch, tmux session refresh, and discovered Houmao agent refresh from `TmuxTabPanel` into `runtime/effects/tmuxEffects.ts`.
- [x] 4.2 Add tmux runtime state and selectors for loading state, errors, session list, discovered agent list, active attachment, read-only mode, and attach status.
- [x] 4.3 Add an ephemeral terminal output sink registry so `TmuxTabPanel` can register xterm output callbacks without storing `Terminal`, `FitAddon`, DOM refs, or terminal bytes in runtime state.
- [x] 4.4 Move tmux attach WebSocket ownership into runtime effects, including attach request, output routing, close/error/exit handling, and reconnect-free cleanup.
- [x] 4.5 Route tmux input and resize through runtime actions, and suppress input dispatch when the pane is attached read-only.
- [x] 4.6 Dispose tmux WebSockets and sink registrations when the pane detaches, closes, retargets, or when the runtime is disposed.
- [x] 4.7 Remove obsolete `TmuxTabPanel` socket refs, fetch abort refs, duplicated refresh state, and attach lifecycle cleanup after runtime effects own those workflows.

## 5. Workbench Integration

- [x] 5.1 Update runtime provider construction in `App.tsx` and `workbenchContext.tsx` to pass the expanded service set and dispose the runtime during page/test teardown.
- [x] 5.2 Keep localStorage-backed layout and target metadata ownership in the existing storage layer while dispatching storage snapshots into the runtime.
- [x] 5.3 Ensure runtime cache and persistence effects do not write stream content, prompt text, request bodies, forwarded props, terminal output, credentials, cookies, bearer tokens, or authorization headers to localStorage.
- [x] 5.4 Surface runtime errors in existing pane UI without crashing the workbench or hiding later stream events.
- [x] 5.5 Preserve existing clear-canvas behavior for watched and unwatched panes after moving lifecycle state into the runtime.

## 6. Tests

- [x] 6.1 Extend `apps/ag-ui-workbench/tests/runtime.spec.ts` with fake services for timers, AG-UI streams, passive discovery, event cache, tmux calls, and WebSockets.
- [x] 6.2 Add runtime tests proving watched-target reconnects do not dispatch active-thread set requests.
- [x] 6.3 Add runtime tests proving watched events are cached, unwatched run events are not cached by default, and cache clear resets reduced watched-target display state without stopping watchers.
- [x] 6.4 Add runtime tests proving pane run streams reduce events, cancel on pane disposal, and do not retain submitted prompt text in reduced state.
- [x] 6.5 Add runtime tests proving runtime disposal closes timers, HTTP stream abort controllers, WebSocket streams, and tmux output sink registrations.
- [x] 6.6 Add runtime tests proving tmux attach output writes to the registered sink, read-only attachments suppress input, and pane close prevents later socket output from reaching the removed pane.
- [x] 6.7 Extend `apps/ag-ui-workbench/tests/workbench.spec.ts` with Playwright coverage proving runtime-migrated AG-UI streams still display Houmao graphics.
- [x] 6.8 Extend Playwright coverage for visible watched-target cache behavior after close/reopen and after clear-canvas.

## 7. Validation

- [x] 7.1 Run `openspec validate refactor-ag-ui-workbench-runtime-lifecycles --strict --no-interactive` and resolve all OpenSpec validation issues.
- [x] 7.2 Run `bun install` in `apps/ag-ui-workbench` if dependencies or lockfile state require it.
- [x] 7.3 Run `bun run typecheck` in `apps/ag-ui-workbench` and resolve all TypeScript errors.
- [x] 7.4 Run `bun run e2e` in `apps/ag-ui-workbench` and resolve all deterministic Playwright failures.
- [x] 7.5 Run `pixi run test` from the repository root if Python-side shared behavior or packaging metadata changes during implementation.

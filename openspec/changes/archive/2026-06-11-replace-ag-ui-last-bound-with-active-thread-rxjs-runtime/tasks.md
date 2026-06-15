## 1. Runtime Foundation

- [x] 1.1 Add `rxjs` to `apps/ag-ui-workbench/package.json` and update the Bun lockfile.
- [x] 1.2 Add the workbench runtime module structure for actions, state, selectors, runtime construction, React adapter hooks, and effects.
- [x] 1.3 Define typed runtime actions for pane lifecycle, target changes, AG-UI streams, active-thread requests, watcher lifecycle, tmux lifecycle, and persistence triggers.
- [x] 1.4 Define runtime state types for panes, watched targets, gateway active-thread records, gateway polling status, tmux attachment status, and runtime errors.
- [x] 1.5 Implement the runtime reducer pipeline using RxJS `scan` or equivalent pure state reduction.
- [x] 1.6 Implement React selector hooks with stable subscription semantics and no direct component access to raw subjects.
- [x] 1.7 Add runtime teardown support that cancels all effect subscriptions, timers, HTTP streams, and WebSocket streams.

## 2. Gateway Active-Thread State

- [x] 2.1 Rename gateway destination state from last-bound-thread to active-thread in models, state classes, and route helpers.
- [x] 2.2 Add active-thread response and request models with source values for `gui_button`, `gui_connect`, and `manual`.
- [x] 2.3 Add `GET /v1/ag-ui/destination`, `GET /v1/ag-ui/active-thread`, `PUT /v1/ag-ui/active-thread`, and conditional `DELETE /v1/ag-ui/active-thread`.
- [x] 2.4 Ensure active-thread starts empty and rejects blank thread ids without replacing the previous value.
- [x] 2.5 Implement expected-thread conditional clear so stale panes cannot clear a newer active-thread value.
- [x] 2.6 Preserve last-sent-thread state as gateway-owned bookkeeping and ensure active-thread clear does not clear last-sent-thread.
- [x] 2.7 Remove or replace workbench-facing `/bindings/last-thread` client usage.

## 3. Gateway Publish Fallback

- [x] 3.1 Change publish destination resolution to explicit request or event destination, then active-thread, then default sink.
- [x] 3.2 Remove last-sent-thread from fallback route selection.
- [x] 3.3 Refresh last-sent-thread after concrete explicit, event-level, connection, or active-thread publishes.
- [x] 3.4 Ensure default-sink publishes do not expose a sink thread and do not refresh last-sent-thread.
- [x] 3.5 Update diagnostic fields and publish response destination kind values to use `active_thread` where applicable.
- [x] 3.6 Preserve live-only delivery semantics and zero-delivery reporting for active-thread fallback.

## 4. Workbench Active-Thread Runtime Effects

- [x] 4.1 Add runtime active-thread client helpers for destination read, active-thread read, active-thread set, and conditional active-thread clear.
- [x] 4.2 Implement one shared active-thread polling effect per normalized gateway key.
- [x] 4.3 Start active-thread polling when at least one eligible pane targets a gateway and stop it when no pane remains interested.
- [x] 4.4 Use a 1 second default polling interval and expose deterministic polling status in runtime state.
- [x] 4.5 Implement active-thread set effects for `gui_button` and `gui_connect` sources.
- [x] 4.6 Implement conditional active-thread clear effects for pane close and retarget-away.
- [x] 4.7 Ensure poll failures update pane presentation without disconnecting existing AG-UI streams.

## 5. Workbench Pane Integration

- [x] 5.1 Add an active-thread control to eligible Houmao agent panes with gray inactive, green active, and deterministic unavailable/error states.
- [x] 5.2 Wire active-thread button clicks to runtime dispatch instead of direct fetch calls.
- [x] 5.3 Make Connect on an eligible discovered Houmao agent pane dispatch active-thread set with source `gui_connect`.
- [x] 5.4 Ensure background watchers, passive reconnects, hidden panes, and event-cache listeners do not dispatch active-thread set.
- [x] 5.5 Ensure inactive panes keep receiving and rendering events explicitly addressed to their own thread.
- [x] 5.6 Ensure stale pane close or retarget does not clear another pane's newer active-thread state.
- [x] 5.7 Keep operator marker behavior independent from active-thread behavior.

## 6. Runtime Migration of Existing Workflows

- [x] 6.1 Move watched-target lifecycle from `useWatchedTargets` into RxJS effects while preserving reconnect backoff and event cache writes.
- [x] 6.2 Move AG-UI connect stream orchestration into runtime effects while preserving metadata-minimal connect request bodies.
- [x] 6.3 Move AG-UI run stream orchestration into runtime effects while preserving compact canvas context and pure event reducers.
- [x] 6.4 Move tmux status and session refresh lifecycle into runtime effects.
- [x] 6.5 Move tmux attach WebSocket status and message lifecycle into runtime effects while keeping xterm DOM ownership in the panel.
- [x] 6.6 Keep short-lived prompt editor, debug editor, and xterm instance refs in React where they do not cross pane boundaries.
- [x] 6.7 Remove obsolete component-local timers, abort refs, and stream lifecycle state once replaced by runtime effects.

## 7. Persistence and Security Boundaries

- [x] 7.1 Keep persisted workbench layout and non-sensitive target metadata in localStorage.
- [x] 7.2 Ensure runtime snapshots or selectors do not persist raw AG-UI request bodies, forwarded props, prompt text, credentials, bearer tokens, cookies, or raw terminal bytes.
- [x] 7.3 Preserve watched-target event cache behavior and avoid storing unwatched stream events in IndexedDB.
- [x] 7.4 Avoid `ReplaySubject` or unbounded replay buffers for raw AG-UI events, tmux terminal output, WebSocket payloads, and request bodies.

## 8. CLI, Skill, and Documentation Updates

- [x] 8.1 Update `houmao-mgr` AG-UI publish output and tests to report active-thread fallback and default-sink warnings.
- [x] 8.2 Update `houmao-agent-ag-ui` skill guidance for active-thread fallback, last-sent bookkeeping, and default-sink/no-delivery handling.
- [x] 8.3 Update workbench README to explain active-thread controls, inactive pane rendering, and RxJS runtime ownership.
- [x] 8.4 Update any existing last-bound-thread wording in docs, tests, and comments to active-thread or last-sent bookkeeping as appropriate.

## 9. Tests and Verification

- [x] 9.1 Add gateway unit tests for active-thread read, set, blank rejection, conditional clear, and last-sent preservation.
- [x] 9.2 Add gateway publish tests for explicit destination precedence, active-thread fallback, last-sent non-fallback, default sink, and last-sent refresh after active-thread publish.
- [x] 9.3 Add CLI tests for route-optional publish output under active-thread fallback, zero delivery, and default-sink warnings.
- [x] 9.4 Add runtime unit tests for action reduction, effect teardown, active-thread polling sharing, and no duplicate gateway pollers.
- [x] 9.5 Add runtime tests proving background watcher reconnects do not dispatch active-thread set.
- [x] 9.6 Add Playwright coverage for button-driven active-thread selection and gray-to-green pane state updates.
- [x] 9.7 Add Playwright coverage for Connect auto-activating an eligible pane.
- [x] 9.8 Add Playwright coverage proving inactive panes still render explicitly addressed AG-UI events.
- [x] 9.9 Add Playwright coverage proving external active-thread changes are reflected after polling.
- [x] 9.10 Add persistence/leak coverage proving runtime migration does not store raw terminal bytes or forbidden AG-UI request content.
- [x] 9.11 Run `bun run typecheck` and the workbench Playwright suite from `apps/ag-ui-workbench`.
- [x] 9.12 Run relevant gateway and CLI Python tests with `pixi run`.
- [x] 9.13 Run `pixi run lint` and `pixi run typecheck`.
- [x] 9.14 Run `openspec validate replace-ag-ui-last-bound-with-active-thread-rxjs-runtime --strict --no-interactive`.

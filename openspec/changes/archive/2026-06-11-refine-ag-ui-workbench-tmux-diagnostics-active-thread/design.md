## Context

The workbench already has a runtime-owned tmux inventory, tmux attach WebSocket effects, reduced AG-UI event state, and shared active-thread polling by normalized gateway key. The current UI still spends a fixed left column on tmux sessions, renders global diagnostics beside every normal agent transcript, and treats every discovered gateway as eligible for active-thread polling.

Exploration against the live passive server found a concrete active-thread mismatch: a live gateway can expose `/v1/ag-ui/capabilities` while returning `404` for `/v1/ag-ui/active-thread` and `/v1/ag-ui/destination`. The current selector still marks that discovered target active-thread eligible, so the pane displays an inactive marker and an error status even though the gateway is otherwise usable.

## Goals / Non-Goals

**Goals:**

- Give tmux panes a full-width terminal by moving session selection into a top combobox.
- Refresh tmux session inventory only when the user opens the combobox, manually refreshes, or an attachment exit/error makes the inventory stale.
- Keep the existing Fuse-powered tmux search and Houmao-only filter behavior inside the combobox.
- Hide normal agent diagnostics until the user asks for diagnostics for a specific message.
- Show a per-message side inspector containing message-specific raw events, activity/custom records, tool calls, and state evidence.
- Detect unsupported active-thread gateways, stop polling them, and render a deterministic unsupported/unavailable state instead of inactive/error flicker.

**Non-Goals:**

- Do not change the passive server API, tmux bridge API, or gateway active-thread API.
- Do not add a new UI framework or combobox dependency.
- Do not persist diagnostic panel open state or per-message inspector state to local storage.
- Do not remove Debug Agent raw diagnostic evidence; this change targets normal agent panes.
- Do not alter the semantics of watched-target caching, AG-UI run/connect request bodies, or tmux attach lifecycle boundaries.

## Decisions

### Use a Local Combobox State for Tmux Session Selection

The tmux pane should keep `query`, dropdown open state, and highlighted/selected row state in React component state. The shared runtime inventory remains the source for status, sessions, agents, loading, and errors.

Alternatives considered:

- Keep the left list and add a collapse button. This preserves implementation shape but still makes session discovery a permanent layout concern.
- Use a native `<select>`. This is simple, but it does not support the existing Fuse search and rich Houmao metadata rows.

### Make Tmux Inventory Demand-Refreshed

Opening the combobox should dispatch `tmux/refreshRequested` using the configured passive server URL. Manual refresh should do the same. Attachment `exit`, `close`, or `error` should continue to request a refresh because those events often mean the selected tmux session changed liveness.

The runtime should no longer maintain a timer solely because a tmux pane is open. Obsolete refresh requests should still be aborted or ignored so rapid open/filter/refresh interactions do not publish stale inventory.

Alternatives considered:

- Keep the 5 second background poller. This improves stale-session detection, but it conflicts with the requested demand-refresh model and does unnecessary work while the user is focused on the terminal.
- Move all tmux refresh code back into the component. This would increase component lifecycle ownership and undo the runtime separation already in place.

### Scope Diagnostics to a Selected Message

`AgUiDisplaySurface` should support a mode for normal agent panes where transcript messages render an info icon. Selecting a message opens an inspector panel for that message. The inspector should derive related records from the reduced event state:

- transcript message by `message.id`
- raw events whose event has `messageId` equal to the message id
- tool calls whose `parentMessageId` equals the message id
- raw events whose event `toolCallId` matches one of those tool calls
- activity/custom entries whose `id` or content references the message where deterministically available
- the current state snapshot as contextual state evidence

Debug Agent panes can keep the existing global diagnostics display by passing a mode or prop to the shared display component.

Alternatives considered:

- Add a global show/hide diagnostics toggle. This reduces clutter, but it does not answer the user's per-message debugging workflow.
- Move diagnostics into a modal. A side panel is better for comparing the selected message with the transcript without covering the content.

### Model Active-Thread Unsupported Separately from Error

The active-thread runtime state should distinguish:

- active-thread supported and ready
- ordinary transient poll errors
- unsupported extension, such as `404` or `405` from `/active-thread`

Unsupported gateways should stop their active-thread poller until the pane target changes, the user retries, or a new gateway key is registered. The UI should not present an unsupported gateway as an inactive thread. Connect and manual active-thread set actions should also avoid mutation calls when the selector reports unsupported or ineligible state.

Alternatives considered:

- Hide all active-thread controls until capabilities prove support. Current capabilities do not advertise active-thread support, so this would require a backend contract change.
- Continue to show the existing error marker. This is technically accurate for the fetch call, but misleading for users because the gateway itself can still connect and run.

### Prevent Active-Thread Poll Overlap

The active-thread poll effect should not abort an in-flight poll merely because the next 1 second tick arrives. Use an RxJS strategy equivalent to `exhaustMap` per gateway, or explicit in-flight tracking, so slow but healthy gateways do not oscillate between polling, abort, and error states.

Alternatives considered:

- Increase the poll interval. This reduces flicker but does not fix overlap when a request is slower than the interval.
- Keep `switchMap`. That is appropriate for replacing stale user-triggered requests, but not for periodic status polling where the latest request is not meaningful until the previous one finishes.

## Risks / Trade-offs

- Demand-refreshed tmux inventory can show stale sessions while the dropdown is closed. Mitigation: refresh immediately when the dropdown opens and after attachment exit/error.
- Per-message diagnostics may miss events that do not carry a stable `messageId` or `parentMessageId`. Mitigation: always include current state snapshot and raw message/tool-call records when deterministic links exist.
- The active-thread unsupported heuristic might classify a temporary reverse-proxy 404 as unsupported. Mitigation: reset unsupported state when the target/gateway key changes and keep ordinary network failures as retryable errors.
- Changing diagnostics test IDs can break existing Playwright assertions that read `raw-*` directly. Mitigation: update tests to open the message info panel before asserting raw diagnostics for normal agent panes, while keeping Debug Agent raw evidence direct.

## Migration Plan

No user data migration is required. Existing tmux tab and pane storage records remain valid. The change is deployable as a frontend/runtime update with test coverage. Rollback is a normal code revert because no persistent data format changes are introduced.

## Open Questions

- None. The current capabilities payload does not advertise active-thread support, so unsupported detection will be based on active-thread endpoint responses for this change.

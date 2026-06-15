# ag-ui-workbench-runtime-lifecycles Specification

## Purpose
Define the workbench runtime ownership model for long-lived browser lifecycles, cancellation, teardown, and reduced state.
## Requirements
### Requirement: Runtime owns long-lived workbench lifecycles
The AG-UI workbench browser runtime SHALL own long-lived browser lifecycle workflows that can outlive a single React render.

Runtime-owned browser workflows SHALL include pane view-state updates, watched-target presentation state, browser subscriptions to local server streams, browser WebSocket lifecycle, browser-side stream cancellation, watched-target cache writes, runtime teardown, tmux terminal sink registration, and active-thread view-model updates.

The local Fastify server SHALL own host-side workflows, including Houmao AG-UI gateway HTTP/SSE clients, target-policy checks, Debug Agent fixture behavior, tmux host bridge processes, and presentation-session lifecycle.

React components SHALL dispatch typed runtime actions for browser workflows and SHALL render runtime-derived view models through selectors.

#### Scenario: Pane run lifecycle is coordinated through runtime and server
- **WHEN** a user submits a prompt from an agent pane
- **THEN** the pane dispatches a runtime run action
- **AND THEN** the browser runtime sends a private workbench command to the local server
- **AND THEN** the local server owns the Houmao AG-UI run stream to the target gateway
- **AND THEN** the browser runtime tracks, reduces, and cancels the pane-visible subscription state

#### Scenario: Runtime teardown stops browser workflows
- **WHEN** the browser workbench runtime is disposed
- **THEN** active browser subscriptions, reconnect timers, browser WebSocket streams, and pending browser cache effects are stopped
- **AND THEN** the local server receives connection close or cancellation signals for matching server-owned resources

#### Scenario: Server teardown stops host workflows
- **WHEN** the local Fastify workbench server shuts down
- **THEN** server-owned AG-UI streams, tmux bridge resources, Debug Agent fixtures, and presentation sessions are closed or released deterministically
- **AND THEN** the server does not stop or interrupt Houmao agents solely because the GUI server shut down

### Requirement: Runtime state separates view models from resource handles
The runtime SHALL keep reducer state limited to serializable or view-oriented state needed by the workbench UI.

The runtime SHALL NOT store `AbortController` instances, timer handles, `WebSocket` instances, xterm `Terminal` objects, `FitAddon` objects, DOM refs, raw terminal bytes, credentials, authorization headers, AG-UI request bodies, forwarded props, or unbounded replay buffers in reduced runtime state.

Runtime effects MAY hold non-serializable resource handles in effect-private maps when those handles are cleaned up through deterministic teardown.

#### Scenario: Tmux output is not replayed from runtime state
- **WHEN** a tmux attach WebSocket receives terminal output bytes
- **THEN** the runtime writes the bytes to the registered terminal sink without storing the bytes in reduced runtime state
- **AND THEN** a later subscriber cannot replay previous terminal output from runtime state

#### Scenario: Prompt text is not retained after run ownership
- **WHEN** a pane run action carries submitted prompt text to the runtime
- **THEN** the runtime may use that text to build the AG-UI request
- **AND THEN** reduced runtime state does not retain the prompt text after the run effect completes or is canceled

### Requirement: Runtime exposes typed actions, selectors, and services
The browser runtime SHALL define typed actions for pane lifecycle, target changes, watched-target storage snapshots, watched-target cache clear requests, AG-UI connect requests, AG-UI run requests, AG-UI stream cancellation, tmux refresh requests, tmux attach requests, tmux input, tmux resize, tmux detach, active-thread requests, and runtime disposal.

The runtime SHALL expose selectors for panes, watched targets, AG-UI stream status, reduced AG-UI event state, tmux status, tmux sessions, tmux attachment state, active-thread state, and runtime errors.

The runtime SHALL accept service interfaces for local server HTTP, local server WebSocket, storage, cache, timer, and browser stream work so tests can run with deterministic fakes.

Services that previously contacted Houmao gateways or host tmux resources directly SHALL be routed through local Fastify server APIs after equivalent server APIs exist.

#### Scenario: Target change dispatches one typed action
- **WHEN** a pane changes from one AG-UI target to another
- **THEN** the component dispatches a typed target-change action
- **AND THEN** runtime effects cancel obsolete browser subscriptions and start required browser subscriptions for the new target

#### Scenario: Component reads derived runtime status
- **WHEN** a pane needs AG-UI stream status or tmux attach status
- **THEN** it reads that status through a runtime selector
- **AND THEN** it does not subscribe directly to internal runtime subjects

#### Scenario: Runtime service talks to local server
- **WHEN** the browser runtime needs capabilities, connect, run, detach, tmux inventory, or tmux attachment behavior after the Fastify API exists
- **THEN** it calls a typed local-server service
- **AND THEN** it does not construct direct host-integration or arbitrary gateway requests inside React components

### Requirement: Watched-target effects preserve client cache semantics
The runtime SHALL reconcile watched targets from durable storage snapshots and SHALL maintain at most one background connect stream per watched target in a browser workbench instance.

For watched targets, runtime effects SHALL load cached events, reduce cached and live events through the same reducer path, append received live AG-UI events to the client event cache, retry passive resolution and stream connection with bounded backoff, and stop the watcher when the target is unwatched.

Background watcher startup and reconnect SHALL NOT set or clear gateway active-thread.

#### Scenario: Background reconnect does not steal active thread
- **WHEN** one pane is active for a gateway
- **AND WHEN** a watched target for another thread on the same gateway reconnects in the background
- **THEN** the runtime does not dispatch an active-thread set request for the watched target
- **AND THEN** the gateway active-thread remains the foreground pane's thread

#### Scenario: Watched event is cached by runtime effect
- **WHEN** a watched connect stream receives a standard AG-UI event
- **THEN** the runtime reduces the event into watched-target display state
- **AND THEN** the runtime appends the received event to the client event cache with target and thread metadata

### Requirement: AG-UI stream effects use pure reducers
The runtime SHALL route AG-UI connect and run stream events through pure AG-UI reducer functions for display state updates.

Runtime effects SHALL keep protocol parsing, network lifecycle, cancellation, and rendering concerns separate.

#### Scenario: Run stream event updates visible state through reducer
- **WHEN** an AG-UI run stream emits transcript, state, activity, custom, tool-call, graphics, or error events
- **THEN** the runtime passes those events through the pure AG-UI reducer path
- **AND THEN** panes render the resulting reduced state without requiring stream-specific rendering code

### Requirement: Tmux effects use ephemeral terminal output sinks
The runtime SHALL own browser-side tmux status presentation, tmux session selection state, tmux attach WebSocket client lifecycle, tmux input commands, tmux resize commands, tmux detach requests, and terminal output sink registration.

The local Fastify server SHALL own host-side tmux inventory lookup, tmux process attachment, read-only enforcement at the host bridge boundary, and tmux bridge teardown.

React tmux panes SHALL keep xterm `Terminal`, `FitAddon`, and DOM refs outside runtime state and SHALL register an ephemeral output sink for the active attachment.

The runtime SHALL drop or report terminal output when no matching sink is registered, but SHALL NOT persist or replay raw terminal bytes.

#### Scenario: Tmux attach writes to registered sink
- **WHEN** a tmux pane attaches to a session and registers a terminal sink
- **AND WHEN** the browser runtime receives terminal output for that attachment from the local server
- **THEN** the runtime writes the output to the registered sink
- **AND THEN** the runtime updates attachment status without storing raw terminal output

#### Scenario: Pane close cleans up tmux attachment
- **WHEN** a tmux pane with an active attachment closes
- **THEN** the runtime closes the browser-side attachment WebSocket or sends a detach command to the local server
- **AND THEN** the runtime unregisters the terminal output sink
- **AND THEN** later WebSocket events cannot write to the removed pane

#### Scenario: Host tmux bridge enforces read-only mode
- **WHEN** a tmux pane attaches in read-only mode
- **THEN** the local Fastify server's tmux bridge rejects or ignores input messages for that attachment
- **AND THEN** the browser runtime also suppresses terminal input for that attachment

### Requirement: Runtime owns shared tmux inventory freshness
The workbench runtime SHALL maintain tmux status, session list, and tmux-related discovered-agent data as a shared runtime-owned inventory for tmux panes.

Runtime effects SHALL refresh tmux inventory when one or more tmux panes explicitly need current inventory, including when the user opens a tmux session combobox, when the user requests refresh, and when a tmux attachment exits, closes, or errors.

Runtime effects SHALL NOT keep a recurring tmux inventory poller active solely because a tmux pane is open.

The runtime SHALL avoid overlapping tmux inventory requests by canceling, coalescing, or ignoring obsolete requests.

#### Scenario: One inventory state serves multiple tmux panes
- **WHEN** two tmux panes exist in one workbench runtime
- **AND WHEN** either pane opens or refreshes the tmux session combobox
- **THEN** runtime effects refresh one shared tmux inventory
- **AND THEN** both panes render tmux status, sessions, discovered agents, loading state, and errors from runtime-derived inventory state

#### Scenario: No poller runs for closed dropdowns
- **WHEN** a tmux pane is open but no tmux session combobox is open and no tmux attachment exit is pending
- **THEN** runtime effects do not keep a recurring tmux inventory timer solely for that pane

#### Scenario: Open and manual refresh update inventory
- **WHEN** at least one tmux pane exists
- **AND WHEN** the user opens the tmux session combobox or activates manual tmux refresh
- **THEN** the runtime requests current tmux inventory from the tmux service

#### Scenario: Attach exit refreshes inventory on demand
- **WHEN** a tmux attachment exits, closes, or errors
- **THEN** runtime effects request current tmux inventory
- **AND THEN** selectors expose the refreshed sessions when the next tmux session picker is shown

### Requirement: Tmux attach exit refreshes inventory without controlling sessions
When a tmux attach WebSocket reports terminal process exit, closes, or errors, runtime effects SHALL close that attachment, update the pane attachment status, unregister or ignore obsolete output sinks, and request a tmux inventory refresh.

The runtime SHALL NOT send tmux kill-session, Houmao stop, restart, shutdown, interrupt, launch, registry cleanup, or prompt-control requests as part of attach-exit handling.

Raw terminal output SHALL continue to flow only through the registered ephemeral terminal sink and SHALL NOT be persisted in reduced runtime state.

#### Scenario: Attach exit removes dead session through inventory refresh
- **WHEN** a tmux attach WebSocket for session `HOUMAO-alpha` reports an exit
- **THEN** the runtime marks the pane attachment disconnected
- **AND THEN** the runtime requests tmux inventory refresh
- **AND THEN** if the refreshed inventory no longer contains `HOUMAO-alpha`, selectors no longer expose that session in tmux session lists

#### Scenario: Attach close does not kill session
- **WHEN** the browser tmux attachment socket closes for session `HOUMAO-beta`
- **THEN** runtime effects clean up the browser attachment resources
- **AND THEN** runtime effects do not issue a tmux or Houmao lifecycle command to kill or stop `HOUMAO-beta`

### Requirement: Runtime models unsupported active-thread gateways
The workbench runtime SHALL distinguish unsupported active-thread gateways from transient active-thread request failures.

When an active-thread read returns a deterministic unsupported-route response such as `404` or `405`, the runtime SHALL mark that gateway active-thread state as unsupported.

Unsupported active-thread state SHALL stop further active-thread polling for the affected gateway until the target or normalized gateway key changes.

Runtime selectors SHALL expose unsupported active-thread state separately from inactive, active, polling, and transient error states.

The runtime SHALL NOT dispatch active-thread set or clear mutations for a gateway while that gateway is known to be unsupported.

#### Scenario: Unsupported active-thread response stops lifecycle
- **WHEN** active-thread polling for a discovered gateway receives a `404` or `405` response from `/active-thread`
- **THEN** the runtime records unsupported active-thread state for that gateway
- **AND THEN** the runtime stops that gateway's active-thread poll lifecycle until a new target or gateway key is registered

#### Scenario: Unsupported state is visible through selectors
- **WHEN** a pane targets a gateway whose active-thread state is unsupported
- **THEN** runtime selectors expose an unsupported active-thread presentation state for that pane
- **AND THEN** the selector does not report the pane as inactive due only to unsupported active-thread routing

#### Scenario: Target change clears unsupported classification
- **WHEN** a pane retargets from an unsupported active-thread gateway to a different normalized gateway key
- **THEN** the runtime treats the new gateway key as a fresh active-thread lifecycle
- **AND THEN** prior unsupported state does not suppress polling for the new gateway key

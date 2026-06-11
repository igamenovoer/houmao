## ADDED Requirements

### Requirement: Runtime owns long-lived workbench lifecycles
The AG-UI workbench runtime SHALL own long-lived browser lifecycle workflows that can outlive a single React render.

Runtime-owned workflows SHALL include watched-target reconciliation, watched-target reconnect loops, AG-UI connect streams, AG-UI run streams, gateway active-thread polling, tmux status/session refreshes, tmux attach WebSockets, watched-target cache writes, and runtime teardown.

React components SHALL dispatch typed runtime actions for these workflows and SHALL render runtime-derived view models through selectors.

#### Scenario: Pane run lifecycle is owned by runtime
- **WHEN** a user submits a prompt from an agent pane
- **THEN** the pane dispatches a runtime run action
- **AND THEN** the runtime starts, tracks, reduces, and cancels the AG-UI run stream for that pane

#### Scenario: Runtime teardown stops live workflows
- **WHEN** the workbench runtime is disposed
- **THEN** active polling, reconnect timers, HTTP streams, WebSocket streams, and pending watched-target cache effects are stopped

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
The runtime SHALL define typed actions for pane lifecycle, target changes, watched-target storage snapshots, watched-target cache clear requests, AG-UI connect requests, AG-UI run requests, AG-UI stream cancellation, tmux refresh requests, tmux attach requests, tmux input, tmux resize, tmux detach, active-thread requests, and runtime disposal.

The runtime SHALL expose selectors for panes, watched targets, AG-UI stream status, reduced AG-UI event state, tmux status, tmux sessions, tmux attachment state, active-thread state, and runtime errors.

The runtime SHALL accept service interfaces for network, gateway, tmux, storage, cache, timer, and WebSocket work so tests can run with deterministic fakes.

#### Scenario: Target change dispatches one typed action
- **WHEN** a pane changes from one AG-UI target to another
- **THEN** the component dispatches a typed target-change action
- **AND THEN** runtime effects cancel obsolete streams and start required streams for the new target

#### Scenario: Component reads derived runtime status
- **WHEN** a pane needs AG-UI stream status or tmux attach status
- **THEN** it reads that status through a runtime selector
- **AND THEN** it does not subscribe directly to internal runtime subjects

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
The runtime SHALL own tmux status refreshes, tmux session refreshes, discovered Houmao agent refreshes needed by tmux tabs, tmux attach WebSockets, tmux input writes, tmux resize writes, and tmux detach cleanup.

React tmux panes SHALL keep xterm `Terminal`, `FitAddon`, and DOM refs outside runtime state and SHALL register an ephemeral output sink for the active attachment.

The runtime SHALL drop or report terminal output when no matching sink is registered, but SHALL NOT persist or replay raw terminal bytes.

#### Scenario: Tmux attach writes to registered sink
- **WHEN** a tmux pane attaches to a session and registers a terminal sink
- **AND WHEN** the runtime receives WebSocket output for that attachment
- **THEN** the runtime writes the output to the registered sink
- **AND THEN** the runtime updates attachment status without storing raw terminal output

#### Scenario: Pane close cleans up tmux attachment
- **WHEN** a tmux pane with an active attachment closes
- **THEN** the runtime closes the attach WebSocket and unregisters the terminal output sink
- **AND THEN** later WebSocket events cannot write to the removed pane

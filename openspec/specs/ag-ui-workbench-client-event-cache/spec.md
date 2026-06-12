# ag-ui-workbench-client-event-cache Specification

## Purpose
Define the AG-UI workbench model for browser-owned watched-target event caching, pane rendering from cached events, and live-only missed-event semantics.
## Requirements
### Requirement: Workbench tracks watched AG-UI targets independently from panes
The workbench SHALL maintain a watched-target registry separate from visible Dockview panes.

A watched target SHALL identify one AG-UI source and thread that the GUI is interested in receiving even when no visible pane is open.

For discovered Houmao agents, the watched target key SHALL use the durable agent address: canonical `agent_id` when available, otherwise an unambiguous `agent_name` until canonical id resolution is available.

For manual AG-UI targets, the watched target key SHALL use the normalized AG-UI base URL and thread id.

Each watched target SHALL own at most one active background AG-UI connect stream per browser workbench instance.

#### Scenario: User watches an agent without opening a pane
- **WHEN** a tester marks discovered agent `abc123` and thread `thread-1` as watched
- **THEN** the workbench records a watched target keyed by `abc123` and `thread-1`
- **AND THEN** the watcher may open an AG-UI connect stream without creating a visible pane

#### Scenario: Pane close preserves watched listener
- **WHEN** a pane is presenting watched target `abc123` and thread `thread-1`
- **AND WHEN** the tester closes that pane
- **THEN** the watched target remains registered
- **AND THEN** the background watcher remains responsible for the AG-UI stream

#### Scenario: Manual target watch is keyed by URL and thread
- **WHEN** a tester watches manual AG-UI target `http://127.0.0.1:8765/v1/ag-ui` with thread `manual-thread`
- **THEN** the workbench keys the watched target by the normalized URL and `manual-thread`
- **AND THEN** it does not infer a Houmao agent id from that URL

### Requirement: Workbench stores received AG-UI events in a client-owned cache
The workbench SHALL persist AG-UI events received by watched targets in a browser-owned cache.

The cache SHALL be separate from gateway storage and SHALL NOT require gateway replay support.

The cache SHALL store target key, thread id, receive timestamp, local monotonic sequence, optional non-durable SSE frame id, and the raw standard AG-UI event object.

The cache SHALL NOT store AG-UI request bodies, forwarded props, credentials, cookies, bearer tokens, authorization headers, passive-server response bodies, mailbox content, memory content, or raw terminal content.

The cache SHALL enforce bounded retention by event count, byte size, time window, or a documented combination of those limits.

#### Scenario: Received Plotly template chart event is cached
- **WHEN** a watched target receives a complete AG-UI tool-call sequence for `houmao.graphic.template`
- **THEN** the workbench stores the received standard AG-UI events in the client cache
- **AND THEN** the stored records include local receive ordering and target/thread metadata

#### Scenario: Cache does not depend on gateway replay
- **WHEN** a gateway capability response reports no resumable replay support
- **AND WHEN** the watched target receives AG-UI events live
- **THEN** the workbench still records those events in the client cache

#### Scenario: Sensitive request data is excluded from cache
- **WHEN** a watched target connect request contains forwarded props or authorization material
- **THEN** the cache does not store those request fields
- **AND THEN** only received stream events and safe target metadata are retained

### Requirement: Visible panes render from cached events plus live watcher updates
An agent pane presenting a watched target SHALL initialize its displayed AG-UI state by reading cached events for that watched target and thread.

The pane SHALL subscribe to future live events from the watcher for that target.

The pane SHALL render Houmao typed components, graphics, transcripts, raw events, state snapshots, activity records, errors, and unknown component fallbacks from the same reducer path for cached and live events.

Reopening a pane for a still-watched target SHALL show previously received cached graphics without asking the gateway to replay them.

#### Scenario: Reopened pane shows cached Plotly template chart
- **WHEN** a watched target receives and caches a `houmao.graphic.template` event sequence
- **AND WHEN** the tester closes the visible pane
- **AND WHEN** the tester opens a pane for the same watched target
- **THEN** the pane renders the cached Plotly-backed chart
- **AND THEN** the workbench does not require gateway replay for that chart

#### Scenario: Live events update open pane
- **WHEN** a pane is open for a watched target
- **AND WHEN** the watcher receives a new AG-UI event
- **THEN** the event is appended to the client cache
- **AND THEN** the pane updates its rendered state from that event

#### Scenario: Unknown cached component remains inspectable
- **WHEN** cached events contain a complete AG-UI tool call with an unknown `toolCallName`
- **THEN** the pane shows the raw tool-call record
- **AND THEN** later cached or live events continue to render normally

### Requirement: Events missed while unwatched are not recovered by the GUI
When a watched target is unwatched or explicitly disconnected, the workbench SHALL close the background AG-UI stream for that target.

The workbench SHALL NOT assume that the gateway retained events published while no watcher was connected.

After a target is watched again, the workbench SHALL keep any events already present in the client cache but SHALL only receive future live gateway events.

#### Scenario: Publish while unwatched is lost
- **WHEN** a tester unwatches target `abc123` and thread `thread-1`
- **AND WHEN** an external caller publishes a valid AG-UI chart batch to that gateway while no GUI watcher is connected
- **AND WHEN** the tester watches `abc123` and `thread-1` again
- **THEN** the newly opened pane does not show the missed chart from gateway replay
- **AND THEN** the pane remains ready for future live events

#### Scenario: Previously cached events survive unwatch until cache retention removes them
- **WHEN** a watched target has cached events
- **AND WHEN** the tester unwatches that target
- **THEN** the watcher stream closes
- **AND THEN** already cached events remain available until the client cache retention policy removes them or the user clears them

### Requirement: Watchers reconnect by target address without requesting event replay
For discovered Houmao agents, a watcher SHALL resolve the durable agent address through the configured passive server before opening an AG-UI stream.

If the agent is offline, live without a gateway, or temporarily unreachable, the watcher SHALL show a deterministic waiting, offline, reconnecting, or gateway-unavailable state and SHALL retry resolution using bounded backoff.

If an active AG-UI stream ends unexpectedly, the watcher SHALL return to the resolution loop without requiring a visible pane.

When opening or reopening a connect stream, the watcher SHALL NOT send a local cache cursor as `lastSeenEventId` for the purpose of gateway replay.

#### Scenario: GUI starts before gateway
- **WHEN** target `abc123` is watched
- **AND WHEN** the passive server reports that no current gateway is available
- **THEN** the watcher records a waiting or offline state
- **AND WHEN** the agent later publishes a live gateway for `abc123`
- **THEN** the watcher resolves the current gateway and connects without requiring a pane to be open

#### Scenario: Gateway restart resumes live listening only
- **WHEN** watcher `abc123` is connected and receives cached event `event-1`
- **AND WHEN** the gateway process goes offline and later returns on a different port
- **THEN** the watcher resolves the new gateway and opens a fresh AG-UI stream
- **AND THEN** it keeps cached event `event-1`
- **AND THEN** it receives only future live events from the new stream

#### Scenario: Reconnect omits replay cursor
- **WHEN** a watcher reconnects after receiving cached AG-UI events
- **THEN** the connect request does not include `lastSeenEventId` as a gateway replay cursor
- **AND THEN** the watcher relies on the client cache for previously received events

### Requirement: Client cache management is visible and deterministic
The workbench SHALL expose cache status for watched targets, including whether a target is currently watched, connected, reconnecting, offline, or unwatched.

The workbench SHALL provide a deterministic way to clear cached events globally or for a watched target.

Cache clearing SHALL remove cached stream events and reduced display evidence for the selected scope without sending Houmao agent lifecycle commands.

#### Scenario: Target cache can be cleared
- **WHEN** a watched target has cached chart events
- **AND WHEN** the tester clears that target's cache
- **THEN** the cached chart events are removed from the local client cache
- **AND THEN** the gateway and managed agent lifecycle are unchanged

#### Scenario: Watch status is visible
- **WHEN** target `abc123` is being watched in the background
- **THEN** the workbench shows that `abc123` is watched
- **AND THEN** the status distinguishes connected, reconnecting, offline, and unwatched states

### Requirement: Watched target clear-canvas resets cache and runtime display state
When an agent pane presents a watched target, the workbench SHALL make the pane's clear-canvas control clear the watched target's browser-owned cached stream events and reset the watched target's in-memory reduced display state.

Clear-canvas SHALL preserve the watched target registration, active watcher connection when present, reconnect loop, resolved target metadata, and future event caching behavior.

Clear-canvas SHALL NOT request gateway replay, gateway deletion, or managed agent lifecycle changes.

#### Scenario: Watched chart does not reappear after clear and reopen
- **WHEN** a watched target has cached AG-UI events that render a Houmao chart
- **AND WHEN** a tester clears the canvas from an agent pane presenting that target
- **AND WHEN** the tester closes and reopens a pane for the same watched target
- **THEN** the previously cached chart does not reappear
- **AND THEN** the watched target remains available for future live AG-UI events

#### Scenario: Clear watched target affects all panes for that target
- **WHEN** two visible agent panes present the same watched target
- **AND WHEN** one pane clears the canvas
- **THEN** cached watched-target evidence is removed from both panes
- **AND THEN** pane-local output that belongs only to the other pane is not cleared by the watched-target cache reset

#### Scenario: Clear keeps watcher connected
- **WHEN** a watched target has an active AG-UI connect stream
- **AND WHEN** the tester clears the canvas
- **THEN** the watcher remains watched and connected or reconnecting according to its current network state
- **AND THEN** future live events from the same stream or a later reconnect are cached and rendered normally

### Requirement: Runtime-owned watchers write watched events to client cache
Watched-target client cache writes SHALL be owned by runtime watched-target effects.

The runtime SHALL append only received AG-UI stream events for registered watched targets to the client event cache.

The runtime SHALL NOT cache AG-UI request bodies, forwarded props, credentials, cookies, bearer tokens, authorization headers, passive-server response bodies, mailbox content, memory content, raw terminal content, or stream events from unwatched pane-owned runs by default.

#### Scenario: Watched stream event is cached by runtime
- **WHEN** a registered watched target receives a standard AG-UI event from its background connect stream
- **THEN** the runtime appends that event to the client event cache with target key, thread id, receive timestamp, and local sequence metadata
- **AND THEN** visible panes for that target reduce the same event into display state

#### Scenario: Unwatched run event is not cached by default
- **WHEN** an unwatched agent pane run stream receives AG-UI events
- **THEN** the runtime may reduce those events into the pane's visible state
- **AND THEN** the runtime does not append those events to the watched-target client cache by default

### Requirement: Runtime-owned cache clearing is scoped and deterministic
Client cache clearing for watched targets SHALL be available through typed runtime actions.

Clearing a watched target cache through the runtime SHALL remove cached stream events and reset the in-memory reduced display state for that watched target while preserving the watched-target registration, active watcher connection or reconnect loop, target metadata, and future cache writes.

Clearing all watched caches through the runtime SHALL remove cached stream events and reset in-memory reduced display state for every watched target without sending Houmao agent lifecycle commands.

#### Scenario: Runtime clears one watched target cache
- **WHEN** a watched target has cached AG-UI events that render a chart
- **AND WHEN** the user clears that target through the runtime-backed clear action
- **THEN** the cached events for that target are removed
- **AND THEN** the target remains watched and future live events are cached normally

#### Scenario: Runtime clear does not control agent lifecycle
- **WHEN** the user clears one or all watched caches
- **THEN** the runtime does not send Houmao stop, restart, shutdown, interrupt, launch, gateway replay, or gateway deletion requests
- **AND THEN** active browser streams remain connected or reconnecting according to their current network state

### Requirement: Runtime cache loading preserves live-only missed-event semantics
When the runtime starts or restarts a watched-target effect, it SHALL load existing client cache records for that target before processing future live events.

The runtime SHALL NOT send a local cache cursor as a gateway replay request and SHALL NOT assume events missed while no watcher was connected can be recovered from the gateway.

#### Scenario: Runtime restart loads cache without requesting replay
- **WHEN** the workbench runtime starts with a watched target that already has cached events
- **THEN** it loads those cached events into reduced watched-target display state
- **AND THEN** the next connect request omits any cache-derived replay cursor

#### Scenario: Missed event remains lost after watcher gap
- **WHEN** a target is unwatched or its runtime watcher is stopped
- **AND WHEN** the gateway receives AG-UI events while no watcher is connected
- **AND WHEN** the target is watched again
- **THEN** the runtime keeps previously cached events and receives future live events
- **AND THEN** it does not recover the missed gateway events through replay


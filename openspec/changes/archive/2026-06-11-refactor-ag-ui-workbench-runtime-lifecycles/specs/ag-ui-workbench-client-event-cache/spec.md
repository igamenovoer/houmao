## ADDED Requirements

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

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

#### Scenario: Received chart event is cached
- **WHEN** a watched target receives a complete AG-UI tool-call sequence for `houmao.chart.bar`
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

#### Scenario: Reopened pane shows cached chart
- **WHEN** a watched target receives and caches a `houmao.chart.bar` event sequence
- **AND WHEN** the tester closes the visible pane
- **AND WHEN** the tester opens a pane for the same watched target
- **THEN** the pane renders the cached bar chart
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

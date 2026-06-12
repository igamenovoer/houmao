## MODIFIED Requirements

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

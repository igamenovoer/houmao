## ADDED Requirements

### Requirement: Discovered-agent panes actively reconnect by agent address
For a pane whose target source is a discovered Houmao agent, the workbench SHALL actively resolve the pane's durable agent address through the configured passive server before opening an AG-UI stream.

If the agent is offline, live without a gateway, or temporarily unreachable, the pane SHALL show a deterministic waiting, offline, reconnecting, or gateway-unavailable state and SHALL retry resolution using bounded backoff.

If an active AG-UI stream ends unexpectedly, the pane SHALL mark the stream disconnected and return to the agent-address resolution loop without requiring the user to reselect the agent.

If resolution later returns a different current gateway for the same authoritative agent id, the pane SHALL connect to the new gateway.

The reconnect loop SHALL NOT send Houmao lifecycle start, stop, restart, shutdown, interrupt, or launch requests.

#### Scenario: GUI starts before agent gateway
- **WHEN** a pane targets known agent `abc123`
- **AND WHEN** the passive server reports that no current gateway is available
- **THEN** the pane displays a waiting or offline state
- **AND WHEN** the agent later publishes a live gateway for `abc123`
- **THEN** the pane resolves the current gateway and connects without requiring a new target selection

#### Scenario: Agent gateway restarts on a new port
- **WHEN** a discovered-agent pane is connected to agent `abc123`
- **AND WHEN** the gateway stream fails because the gateway process went offline
- **AND WHEN** passive-server resolution later reports a new gateway port for `abc123`
- **THEN** the pane reconnects to the new gateway
- **AND THEN** the pane still treats `abc123` as the same durable target

#### Scenario: Reconnect does not control lifecycle
- **WHEN** a discovered-agent pane enters reconnecting state
- **THEN** the workbench performs only passive-server resolution and AG-UI connect attempts
- **AND THEN** it does not send start, stop, restart, shutdown, interrupt, launch, or prompt-control requests

### Requirement: Workbench reconnect uses event cursors when supported
The workbench SHALL track the latest applied SSE event id for each pane and thread when the AG-UI stream provides event ids.

When reconnecting to a gateway whose capabilities indicate resumable replay, the workbench SHALL send the latest applied event id as `lastSeenEventId` in the AG-UI connect input.

The workbench SHALL tolerate at-least-once replay by ignoring already applied SSE event ids when possible and by keeping existing AG-UI reducer behavior safe for duplicate payloads.

When replay is unavailable or cursor recovery fails, the pane SHALL still process the fresh `STATE_SNAPSHOT` and later live events.

#### Scenario: Reconnect sends last seen event id
- **WHEN** a pane receives an AG-UI event frame with SSE id `abc123:thread-1:42`
- **AND WHEN** the pane reconnects to a gateway that advertises resumable replay
- **THEN** the connect request includes `lastSeenEventId = "abc123:thread-1:42"`

#### Scenario: Duplicate replay does not duplicate visible state
- **WHEN** a reconnect stream replays an event whose SSE id was already applied
- **THEN** the workbench ignores the duplicate frame when the id is known
- **AND THEN** the pane continues processing later replayed or live events

#### Scenario: Snapshot fallback remains usable
- **WHEN** a reconnect request cannot be replayed from the saved cursor
- **THEN** the pane processes the gateway's current `STATE_SNAPSHOT`
- **AND THEN** the pane remains connected for future live events

### Requirement: Manual direct AG-UI targets remain explicit and non-reconnecting by agent address
For manual targets, the workbench SHALL continue to use the configured label, AG-UI URL, and thread id directly.

Manual targets SHALL NOT perform passive-server agent-address resolution unless the user converts or retargets the pane to a discovered-agent target.

Manual targets MAY retry the same configured URL after transient stream failures, but they SHALL NOT infer an agent id, scan the registry, or resolve a replacement gateway URL.

#### Scenario: Manual URL stays direct
- **WHEN** a tester enters `http://127.0.0.1:8765/v1/ag-ui` as a manual target
- **THEN** the pane uses that URL directly for capabilities, connect, run, and detach requests
- **AND THEN** it does not query passive-server agent resolution

#### Scenario: Manual reconnect does not guess agent identity
- **WHEN** a manual target stream fails
- **THEN** the workbench does not infer an agent id from the URL
- **AND THEN** it does not scan or resolve the registry for a replacement gateway

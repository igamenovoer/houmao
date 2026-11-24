# Spec Delta

## MODIFIED Requirements

### Requirement: Watchers reconnect by target address without requesting event replay

For discovered agents, a watcher SHALL resolve the durable agent address through the configured passive server before opening a stream. Signed reconnects SHALL verify the resolved listener against the approved target binding.

For an offline agent, detached gateway, or temporary transport failure, the watcher SHALL show the applicable waiting, offline, reconnecting, or gateway-unavailable state and retry resolution with bounded backoff.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

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
- **THEN** the watcher resolves and verifies the new gateway and opens a fresh AG-UI stream
- **AND THEN** it keeps cached event `event-1`
- **AND THEN** it receives only future live events from the new stream

#### Scenario: Reconnect omits replay cursor

- **WHEN** a watcher reconnects after receiving cached AG-UI events
- **THEN** the connect request does not include `lastSeenEventId` as a gateway replay cursor
- **AND THEN** the watcher relies on the client cache for previously received events

#### Scenario: The gateway refuses a reconnect

- **WHEN** a watcher receives an explicit authentication or authorization refusal for its connect attempt
- **THEN** it reports the refusal and waits for an explicit reconnect
- **AND THEN** it does not choose another signer or fall back to unsigned access

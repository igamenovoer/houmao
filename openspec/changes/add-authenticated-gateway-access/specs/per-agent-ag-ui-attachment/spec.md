# Spec Delta

## ADDED Requirements

### Requirement: Authenticated AG-UI operations require operator authority

Every AG-UI route on an authenticated gateway SHALL require operator authority before connection, run, destination-state, or event-publish handling. This includes capabilities, connect, runs, events, detach, and destination-state operations. Credentials SHALL use the gateway's explicit bearer-header contract and SHALL NOT appear in AG-UI payloads, stream URLs, events, or diagnostics.

#### Scenario: Unauthenticated caller opens a stream

- **WHEN** a caller without a valid credential requests AG-UI connect or runs
- **THEN** the response is HTTP 401 before stream admission or prompt submission

#### Scenario: Peer uses AG-UI as a prompt path

- **WHEN** a valid peer posts an AG-UI run
- **THEN** the response is HTTP 403 before submitting a gateway or native request

#### Scenario: Operator attaches without starting work

- **WHEN** an authenticated operator opens an AG-UI connect stream
- **THEN** existing sanitized snapshot and live-event semantics remain intact
- **AND** authentication does not turn connection into agent work

#### Scenario: Peer probes capabilities or publishes events

- **WHEN** a peer requests AG-UI capabilities or publishes an event batch
- **THEN** it receives HTTP 403 without private stream or routing effects

### Requirement: AG-UI streams revalidate their admitted operator grant

Authenticated AG-UI streams SHALL revalidate the admitted credential and operator role at their bounded heartbeat or before the next event emission. Observed revocation, role reduction, or unavailable policy SHALL close the affected stream without further private events. The documented heartbeat bound SHALL limit idle-stream revocation delay.

#### Scenario: Connected operator credential is revoked

- **WHEN** an open stream observes that its credential has been removed
- **THEN** it closes and releases connection bookkeeping within the documented revalidation bound
- **AND** it does not interrupt, stop, restart, or replay underlying agent work

#### Scenario: Operator is reduced to peer

- **WHEN** an open stream observes that its admitted credential now has peer authority
- **THEN** it stops delivering AG-UI events and detaches

#### Scenario: Policy cannot be loaded during a stream

- **WHEN** a stream revalidation observes unsafe, malformed, or unavailable policy
- **THEN** the stream closes without publishing private policy details or retaining its earlier authority
- **AND** a later valid reconnect must authenticate again


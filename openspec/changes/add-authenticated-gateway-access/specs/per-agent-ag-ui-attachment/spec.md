# Spec Delta

## ADDED Requirements

### Requirement: AG-UI operations apply current admin access

Every AG-UI route SHALL apply current admin access before handling capabilities, connect, runs, events, detach, or destination state. A valid empty list permits anonymous admission. A nonempty list requires an admin signature carried in headers. Payloads, stream URLs, events, and diagnostics SHALL omit proof material.

#### Scenario: Unauthenticated caller opens a stream

- **WHEN** a caller without signed proof requests AG-UI connect or runs while the admin list has entries
- **THEN** the response is HTTP 401 before stream admission or prompt submission

#### Scenario: Self uses AG-UI as a prompt path

- **WHEN** a caller with only self proof posts an AG-UI run while the admin list has entries
- **THEN** the response is HTTP 403 before submitting a gateway or native request

#### Scenario: Admin attaches without starting work

- **WHEN** a verified admin opens an AG-UI connect stream
- **THEN** existing sanitized snapshot and live-event semantics remain intact
- **AND** authentication does not turn connection into agent work

#### Scenario: Self probes capabilities or publishes events

- **WHEN** a caller with only self proof requests AG-UI capabilities or publishes an event batch in key-required mode
- **THEN** it receives HTTP 403 without private stream or routing effects

### Requirement: AG-UI streams revalidate their admitted admin access

AG-UI streams SHALL revalidate the admitted key and enrollment or the admitted empty-list revision, and the target, before event emission and at most every five seconds while idle. Loss of the admitted authority or policy SHALL close the stream before further protected events.

#### Scenario: Connected admin key is revoked

- **WHEN** an open stream observes that its credential has been removed
- **THEN** it closes and releases connection bookkeeping within the revalidation bound
- **AND** underlying agent work continues under its existing execution contract

#### Scenario: The same public key is enrolled again

- **WHEN** a stream's key is removed and subsequently re-enrolled under the same public key identity
- **THEN** it stops delivering AG-UI events and detaches

#### Scenario: First enrollment closes an open admin stream

- **WHEN** a stream was admitted anonymously and a first key is registered
- **THEN** it closes on revalidation and releases its bookkeeping
- **AND** a new stream uses the current admin access state

#### Scenario: Policy cannot be loaded during a stream

- **WHEN** a stream revalidation observes unsafe, malformed, or unavailable policy
- **THEN** the stream closes without publishing private policy details or retaining its earlier authority
- **AND** a new stream must pass current admission


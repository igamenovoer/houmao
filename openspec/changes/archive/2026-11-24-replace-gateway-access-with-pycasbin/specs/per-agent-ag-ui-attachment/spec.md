# Spec Delta

## MODIFIED Requirements

### Requirement: AG-UI operations apply current admin access

Every AG-UI route SHALL apply current policy to the verified caller, target domain, canonical resource, and action before effects. Capabilities, connect, run, event publication, detach, and destination operations SHALL have distinct permissions. A run SHALL authorize prompt submission and observation of its output. Payloads, stream URLs, events, and diagnostics SHALL omit proof material.

#### Scenario: Unauthenticated caller opens a stream

- **WHEN** a caller without signed proof requests AG-UI connect or runs when current policy requires proof
- **THEN** the response is HTTP 401 before stream admission or prompt submission

#### Scenario: Self uses AG-UI as a prompt path

- **WHEN** a caller proves its managed identity and submits an AG-UI run with observation permission alone
- **THEN** the response is HTTP 403 before submitting a gateway or native request

#### Scenario: Admin attaches without starting work

- **WHEN** an administrator with current observation permission opens an AG-UI connect stream
- **THEN** existing sanitized snapshot and live-event semantics remain intact
- **AND** the connection creates no agent work

#### Scenario: Self probes capabilities or publishes events

- **WHEN** a caller proves its managed identity and requests AG-UI capabilities or publishes an event batch outside its scoped permissions
- **THEN** it receives HTTP 403 without private stream or routing effects

#### Scenario: A scoped caller attaches without starting work

- **WHEN** a verified caller who is not an administrator opens a stream for a resource it may observe
- **THEN** the gateway delivers the existing sanitized snapshot and live events under that grant

#### Scenario: Event publication resolves another destination

- **WHEN** an event request resolves to a thread, run, or connection outside the caller's allowed resources
- **THEN** the gateway denies publication before storing or delivering the events

### Requirement: AG-UI streams revalidate their admitted admin access

AG-UI streams SHALL recheck caller, credential, admitted authority, target binding, and exact observation permission before event emission and at most every five seconds while idle. This includes the admitted admin key enrollment or open epoch when applicable. Loss of authority or unavailable policy SHALL close the stream before further protected events and preserve already-admitted work.

#### Scenario: Connected admin key is revoked

- **WHEN** a stream admitted through named-admin authority observes that its credential or exact admin roster entry has been removed
- **THEN** it closes and releases connection bookkeeping within the revalidation bound
- **AND** underlying agent work continues under its existing execution contract

#### Scenario: The same public key is enrolled again

- **WHEN** a stream's key is removed and subsequently re-enrolled under the same public key identity
- **THEN** it stops delivering AG-UI events and detaches

#### Scenario: First enrollment closes an open admin stream

- **WHEN** a signed or anonymous stream was admitted through open authority and a first admin key is registered
- **THEN** it closes on revalidation and releases its bookkeeping
- **AND** a new stream requires current observation permission

#### Scenario: A connected caller loses observation permission

- **WHEN** the current policy revokes observation of the stream's exact resource while the credential remains current
- **THEN** the stream closes before emitting further protected events
- **AND THEN** already-admitted agent work continues

#### Scenario: Policy cannot be loaded during a stream

- **WHEN** a stream revalidation observes unsafe, malformed, or unavailable policy
- **THEN** the stream closes without publishing private policy details or retaining its earlier authority
- **AND** a new stream must pass current admission

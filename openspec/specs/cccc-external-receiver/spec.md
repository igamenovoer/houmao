# cccc-external-receiver Specification

## Purpose

Define the provider-side contract that lets an external gateway receive CCCC delivery attempts and report actual handoff without giving CCCC control of its agent process.

## Requirements

### Requirement: Receiver Compatibility Is Explicitly Negotiated

The integration SHALL verify a versioned external-receiver protocol, required capabilities, selected Actor generation, and finite limits before enabling delivery. An incompatible service SHALL fail explicitly without falling back to human Web messaging, administrator MCP, terminal injection, or a body-specific native receiver.

#### Scenario: Stock Service Lacks the Receiver Interface

- **WHEN** a healthy CCCC service does not advertise the required receiver contract
- **THEN** the plugin reports receiver incompatibility and performs no delivery
- **AND THEN** successful Web health checks do not qualify chat integration

#### Scenario: Protocol Version Is Unsupported

- **WHEN** the service advertises an unsupported protocol version or omits a required capability
- **THEN** the affected operations remain unavailable with a safe compatibility diagnostic

### Requirement: Provider Credentials Authorize One Actor Registration

The receiver interface SHALL authenticate credentials bound to a preprovisioned Group, Actor, and registration generation. Provider operations SHALL derive sender and visibility authority from that grant. Binding credentials SHALL NOT authorize service administration, another Actor, or human-user impersonation.

#### Scenario: Actor Token Is Used With Another Group

- **WHEN** a request supplies Group or Actor selectors outside its authenticated grant
- **THEN** the provider rejects it before reading private history or changing state

#### Scenario: Actor Name Is Recreated

- **WHEN** an Actor is removed and recreated with the same display identifier
- **THEN** grants and receiver leases for its former registration fail as stale

### Requirement: External Receivers Do Not Grant Process Ownership

An externally controlled Actor SHALL identify its receive capability separately from a CCCC-managed runtime. Group, Actor, or receiver lifecycle operations SHALL NOT launch, stop, reset, or inject directly into the external agent body.

#### Scenario: CCCC Group Is Stopped

- **WHEN** an operator stops a Group containing a Houmao-backed external Actor
- **THEN** CCCC stops offers and retires applicable receive authority
- **AND THEN** the Houmao body remains running with its conversation intact

### Requirement: One Current Receiver Lease Controls Intake

The provider SHALL allow at most one active receiver lease per Actor registration. Leases SHALL have a connection generation and finite expiry. Replacement gateways SHALL wait for an existing lease to expire unless a CCCC operator explicitly authorizes early takeover. Ordinary Actor credentials SHALL NOT force takeover. Lease transitions SHALL fence stale polls, offers, and outcomes without transferring in-flight work.

#### Scenario: Two Receivers Claim the Same Actor

- **WHEN** a second receiver requests intake while a valid lease exists
- **THEN** it receives an explicit conflict unless a CCCC operator explicitly authorizes early takeover
- **AND THEN** both receivers cannot dispatch the same offered attempt

#### Scenario: Gateway Crashes Before Its Lease Expires

- **WHEN** a replacement gateway presents ordinary Actor credentials while the crashed gateway's lease remains valid
- **THEN** acquisition reports a lease conflict and the replacement waits for expiry before acquiring a new generation
- **AND THEN** lease recovery retains no local delivery payload and does not retry an earlier offered attempt

#### Scenario: Actor Credentials Attempt Forced Takeover

- **WHEN** a request with only normal Actor authority asks to replace an unexpired receiver lease
- **THEN** the provider refuses takeover without changing the current lease

#### Scenario: CCCC Operator Explicitly Takes Over

- **WHEN** a CCCC operator authorizes early receiver takeover through a separate management operation
- **THEN** the provider fences the old lease generation and permits the replacement to acquire intake
- **AND THEN** the operation neither controls the body nor re-offers unsettled delivery attempts

#### Scenario: Old Receiver Acknowledges After Replacement

- **WHEN** an acknowledgement presents an expired or replaced lease generation
- **THEN** it cannot settle a replacement receiver's attempt

### Requirement: Delivery Offers Are Bounded and Attempt-Scoped

Each offer SHALL identify the Actor registration, lease generation, delivery attempt, native source event, delivery mode, and finite deadline. The provider and plugin SHALL enforce negotiated payload and concurrency limits before handoff. Expired or invalid offers SHALL fail without body dispatch.

#### Scenario: Offer Exceeds the Event Envelope Limit

- **WHEN** a delivery offer cannot fit the negotiated gateway envelope budget
- **THEN** the attempt reports a permanent input or size error without partial prompt delivery

#### Scenario: Offer Deadline Expires Before Dispatch

- **WHEN** an offer reaches the plugin after its usable deadline
- **THEN** it fails without waiting for readiness or handing content to the body

### Requirement: Success Means Confirmed Ordinary Handoff

A receiver SHALL report accepted delivery only after the gateway confirms ordinary handoff to the same ready body observed for that request. Receipt of a poll response, queue admission, thread creation, or provider ledger append SHALL NOT establish handoff. Accepted delivery SHALL NOT imply completed agent work.

#### Scenario: Ready Body Confirms Handoff

- **WHEN** a current offer reaches a ready body and gateway handoff is confirmed
- **THEN** the receiver submits an accepted outcome for that exact attempt
- **AND THEN** the provider records handoff separately from any later reply or task completion

#### Scenario: Adapter Can Only Confirm Queued Work

- **WHEN** a body adapter cannot establish actual handoff within the request deadline
- **THEN** the receiver reports failure or uncertainty instead of accepted delivery

### Requirement: Readiness Refusal Is Immediate

A busy, not-ready, or uncertain body SHALL produce a retryable readiness refusal equivalent to HTTP 409. An unavailable gateway, plugin, or body SHALL produce an availability failure equivalent to HTTP 503. Neither outcome SHALL wait for readiness or retain a local payload for a later attempt.

#### Scenario: Body Is Busy When Offered Chat Arrives

- **WHEN** the plugin receives an offer while the body is busy
- **THEN** it immediately reports a retryable readiness failure to CCCC
- **AND THEN** becoming idle alone causes no later delivery of that payload

#### Scenario: Gateway Is Absent

- **WHEN** CCCC cannot reach an active receiver for the selected Actor
- **THEN** CCCC exposes receiver unavailability rather than body-handoff success

### Requirement: Body Loss Before Confirmation Fails the Attempt

Body death, replacement, gateway loss, cancellation, or timeout before confirmed handoff SHALL produce a failed or uncertain attempt. Expired work SHALL NOT reach a replacement body. Failure after an already completed successful handoff SHALL NOT retroactively change that handoff result.

#### Scenario: Body Restarts During Dispatch

- **WHEN** the observed body is replaced while an offer is being dispatched
- **THEN** the attempt fails or becomes uncertain
- **AND THEN** the event is not handed to the replacement body by delayed work

#### Scenario: Body Dies After Completed Success

- **WHEN** accepted handoff has completed and the body later dies
- **THEN** the delivery remains a recorded handoff without claiming work completion or scheduling automatic resend

### Requirement: Provider Outcomes Preserve Ambiguity

The provider SHALL retain attempt identity and distinguish in-progress, accepted, refused, failed, and uncertain outcomes. Lost acknowledgement or an unsettled offered attempt after receiver or daemon failure SHALL remain uncertain. Reconciliation SHALL NOT infer acceptance from observation cursors or infer safe retry from missing success.

#### Scenario: Body Receives Content but Acknowledgement Is Lost

- **WHEN** dispatch occurs but CCCC cannot obtain the accepted outcome
- **THEN** the provider records or exposes uncertainty
- **AND THEN** the integration does not claim exactly-once delivery or silently redispatch

#### Scenario: Daemon Restarts With an Offered Attempt

- **WHEN** CCCC reconstructs an offered attempt lacking a terminal outcome
- **THEN** it settles or reports the attempt as uncertain without re-offering it on receiver reconnect

### Requirement: Fresh Retries Belong to the Sender

An unsuccessful delivery SHALL retain its message only in the authoritative CCCC service. A new attempt SHALL require a fresh sender-authorized retry decision, preserve the source event identity, and receive a new attempt identity. Retrying an uncertain attempt SHALL explicitly acknowledge possible duplicate handoff.

#### Scenario: Sender Retries a Refused Message

- **WHEN** the original sender requests a fresh attempt after a readiness refusal
- **THEN** CCCC offers a new attempt and the gateway re-evaluates current readiness
- **AND THEN** the earlier refused request is not resumed

#### Scenario: Another Actor Attempts Delivery Retry

- **WHEN** an Actor requests retry of an outgoing event it does not own
- **THEN** the provider refuses the retry before creating another attempt

#### Scenario: Uncertain Retry Lacks Explicit Duplicate Consent

- **WHEN** a sender requests retry of an uncertain handoff without acknowledging duplication risk
- **THEN** the provider returns an uncertainty conflict without another delivery attempt

### Requirement: Duplicate Transport Activity Does Not Create New Handoffs

The provider SHALL serialize ownership of each attempt and preserve terminal outcomes. Duplicate polls, offer transport activity, or acknowledgement submissions SHALL NOT create a new attempt or automatically dispatch again. Generic gateway source IDs SHALL remain correlation identifiers rather than durable exactly-once receipts.

#### Scenario: Accepted Attempt Is Observed Again

- **WHEN** connection recovery encounters an already accepted provider attempt
- **THEN** it reconciles the provider receipt without invoking body dispatch again

#### Scenario: Outcome Is Submitted Twice

- **WHEN** the same live attempt outcome is submitted again with valid scope
- **THEN** the provider returns its settled outcome without generating another handoff

### Requirement: Reconnection Separates Observation From Delivery

Reconnect SHALL restore a current lease and reconcile bounded provider metadata using scoped observation cursors. A history or receipt cursor SHALL NOT acknowledge body delivery or consume Mail. Recovery gaps SHALL be visible and SHALL NOT cause automatic history-to-prompt replay.

#### Scenario: Events Arrive While the Gateway Is Down

- **WHEN** the plugin reconnects after events were retained in CCCC
- **THEN** it can inspect bounded history and delivery status
- **AND THEN** refused or uncertain events require fresh sender-authorized attempts before body delivery

#### Scenario: Observation Cursor Is Stale

- **WHEN** CCCC cannot resume an observation cursor
- **THEN** it reports an explicit gap or stale-cursor result and supports bounded reconciliation
- **AND THEN** the plugin does not scan unbounded history or treat the gap as a delivery request

### Requirement: Compatibility Evidence Is Reproducible

The supported deployment SHALL identify the CCCC source revision, protocol version, and any applied compatibility patches. Required receiver changes SHALL be reproducible from durable tracked inputs. Qualification SHALL exercise the actual provider interface and authoritative receipts, not only a fake service or Web health endpoint.

#### Scenario: Fresh Checkout Builds the Qualified Service

- **WHEN** a developer follows the documented pinned deployment procedure
- **THEN** receiver compatibility can be reproduced without private modifications in a reference checkout

#### Scenario: Compatible Service Is Unavailable During Qualification

- **WHEN** live receiver qualification lacks its required service build or credentials
- **THEN** the report identifies an explicit setup failure or unexecuted check instead of successful qualification

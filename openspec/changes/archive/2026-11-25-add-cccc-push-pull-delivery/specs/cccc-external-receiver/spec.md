# CCCC External Receiver Spec Delta

## ADDED Requirements

### Requirement: CCCC Retains Pending Chat Until a Receiver Can Deliver It

CCCC SHALL retain ordinary external chat and its ordered first-delivery work per recipient registration, including when no receiver holds the lease. Busy or unavailable receivers SHALL leave unstarted chat pending in CCCC. Provider storage and pending delivery SHALL have distinct outcomes from handoff or direct-read acknowledgment.

#### Scenario: Chat Arrives While the Gateway Is Down

- **WHEN** CCCC stores chat for an eligible external Actor while no receiver lease is active
- **THEN** the recipient's delivery is reported as pending and remains eligible for a pull under the next valid lease

#### Scenario: The Recipient Is Busy When Several Messages Arrive

- **WHEN** CCCC stores several chat messages for an Actor while its body is executing a turn
- **THEN** CCCC retains each message and its delivery order for the active receiver to process when ready
- **AND THEN** waiting alone creates neither a terminal refusal nor a new sender retry attempt

#### Scenario: CCCC Reaches Its Pending Chat Retention Limit

- **WHEN** an Actor's pending chat reaches a provider capacity or age limit
- **THEN** CCCC reports the affected delivery and the applicable limit explicitly
- **AND THEN** the reported outcome identifies the original event and recipient

### Requirement: A Pull Returns One Bounded Snapshot of Pending Chat

One pull SHALL atomically select and claim an ordered prefix of the eligible pending chat visible at its snapshot boundary under the current pull lease. The response SHALL contain complete offers within negotiated count and response byte limits. Messages beyond the snapshot or its limits SHALL stay eligible for a subsequent pull.

#### Scenario: Multiple Messages Are Pending at the Pull Boundary

- **WHEN** a pull finds multiple eligible messages that fit its count and byte limits
- **THEN** CCCC returns them in one ordered response
- **AND THEN** later arrivals belong to a subsequent pull

#### Scenario: The Next Message Does Not Fit in the Same Pull

- **WHEN** the next complete eligible offer would exceed the count or byte budget
- **THEN** CCCC returns the fitting prefix without skipping or partly claiming the next message
- **AND THEN** an individual offer that cannot fit the negotiated single-event limit receives a typed size failure

### Requirement: Push Publishes Ordered Offers on an Authorized Stream

CCCC SHALL publish chat offers on an authenticated stream that Houmao opens to CCCC under the current push lease and Actor registration. CCCC SHALL emit offers in delivery order as messages become eligible and the receiver has capacity. Transport flow control SHALL leave excess work pending in CCCC.

#### Scenario: An Actor Receives Chat Over the Push Stream

- **WHEN** an eligible chat message arrives for an Actor whose stream has available capacity
- **THEN** CCCC publishes an offer carrying that message without a separate receiver pull

#### Scenario: The Push Receiver Reaches Capacity

- **WHEN** the receiver's negotiated outstanding-offer count or byte budget is exhausted
- **THEN** CCCC retains subsequent messages as pending and resumes ordered offering when capacity becomes available

### Requirement: Direct Receivers Acknowledge Exact Retrieved Batches

A direct client SHALL use a temporary pull lease. CCCC SHALL durably record the exact direct retrieval before returning material to that client and issue a finite receipt scoped to the Actor registration and retrieved batch. An authorized client SHALL be able to acknowledge that exact read in a later request after releasing the intake lease.

#### Scenario: A Later CLI Invocation Acknowledges a Direct Pull

- **WHEN** the same Actor presents a current direct-retrieval receipt after releasing its pull lease
- **THEN** CCCC records an acknowledged direct read for exactly the retrieved messages
- **AND THEN** each delivery receipt identifies direct read separately from a gateway-confirmed body handoff

#### Scenario: A Direct Receipt Is Repeated or Used Outside Its Scope

- **WHEN** the same Actor repeats a previously settled direct acknowledgment
- **THEN** CCCC returns the original result without advancing another claim
- **AND WHEN** another Actor, a replacement registration, or an expired unsettled receipt is presented
- **THEN** the provider rejects the request with a typed scope or expiry error and leaves other deliveries unchanged

#### Scenario: A Direct Retrieval Is Never Acknowledged

- **WHEN** the acknowledgment window expires for a direct retrieval whose content may have reached the CLI caller
- **THEN** CCCC records uncertainty for that exact retrieval and excludes it from automatic re-offering

### Requirement: Mail Notices Use Their Separate Immediate Contract

The provider SHALL identify Mail notices as a distinct bounded offer type and keep ordinary chat pending and batching rules scoped to chat. Mail notices SHALL use immediate ordinary admission and their existing outcome and consumption semantics.

#### Scenario: A Mail Notice Reaches a Busy Gateway

- **WHEN** the current receiver offers a Mail notice while the body is busy
- **THEN** the integration records the ordinary readiness refusal for the notice and leaves the deferred Mail cursor unchanged
- **AND THEN** ordinary chat retained for that Actor remains independently eligible for delivery

## MODIFIED Requirements

### Requirement: Receiver Compatibility Is Explicitly Negotiated

The integration SHALL verify external receiver protocol v2, the capabilities required for the selected transport and client, the selected Actor generation, and finite limits before enabling delivery. Incompatibility SHALL produce an explicit diagnostic and leave the affected receiver operation unavailable.

#### Scenario: Stock Service Lacks the Receiver Interface

- **WHEN** a healthy CCCC service does not advertise the required receiver contract
- **THEN** the client reports receiver incompatibility before receiving chat
- **AND THEN** it excludes human Web messaging, administrator MCP, terminal injection, and body-specific native receivers as substitutes

#### Scenario: Protocol Version Is Unsupported

- **WHEN** the service advertises an unsupported protocol version or omits a required capability for the selected transport or client
- **THEN** the affected operations remain unavailable with a safe compatibility diagnostic

### Requirement: One Current Receiver Lease Controls Intake

CCCC SHALL allow one active intake lease per Actor registration across gateways and direct clients. Each lease SHALL authorize one transport for a finite generation. CCCC SHALL fence retired polls, streams, batch starts, and gateway outcomes. Replacement receivers SHALL wait for release or expiry, with early takeover reserved to a CCCC operator.

#### Scenario: Two Receivers Claim the Same Actor

- **WHEN** a gateway or direct CLI tries to acquire intake while another receiver holds a valid lease for the same Actor
- **THEN** the second receiver receives an explicit lease conflict
- **AND THEN** one lease exclusively authorizes claiming and starting each delivery

#### Scenario: Gateway Crashes Before Its Lease Expires

- **WHEN** a replacement gateway or direct CLI presents ordinary Actor credentials while the crashed gateway's lease remains valid
- **THEN** acquisition reports a conflict until the old lease expires or a CCCC operator retires it
- **AND THEN** the replacement can resume provider-owned unstarted work under its new generation

#### Scenario: Gateway Switches Transport

- **WHEN** a running gateway changes between pull and push
- **THEN** it retires the old receiver generation before the new transport acquires intake
- **AND THEN** CCCC rejects new delivery operations from the retired generation

#### Scenario: Actor Credentials Attempt Forced Takeover

- **WHEN** a request with only ordinary Actor authority asks to replace an unexpired receiver lease
- **THEN** CCCC refuses takeover and preserves the current lease

#### Scenario: CCCC Operator Explicitly Takes Over

- **WHEN** a CCCC operator authorizes early receiver takeover through a separate management operation
- **THEN** CCCC fences the old lease generation and permits a replacement to acquire intake
- **AND THEN** CCCC recovers unstarted work, preserves settled outcomes, and classifies exposed unsettled gateway handoffs as uncertain
- **AND THEN** the external agent body stays under Houmao control

#### Scenario: Old Receiver Acknowledges After Replacement

- **WHEN** a gateway outcome presents an expired or replaced lease generation
- **THEN** CCCC rejects it without settling a replacement receiver's attempt

### Requirement: Delivery Offers Are Bounded and Attempt-Scoped

Each chat offer SHALL identify the Actor registration, lease generation, attempt, native event, delivery order, original CCCC timestamp, delivery mode, and finite validity. It SHALL carry the sender, text, and reply ancestry when present. The provider and receiver SHALL enforce negotiated limits on payloads and outstanding offers. Expired or invalid offers SHALL be ineligible for body dispatch.

#### Scenario: Offer Exceeds the Event Envelope Limit

- **WHEN** a delivery offer cannot fit the negotiated gateway envelope budget
- **THEN** the attempt reports a permanent size error without partial prompt delivery

#### Scenario: Offer Deadline Expires Before Dispatch

- **WHEN** a staged chat offer loses its validity before handoff starts
- **THEN** the receiver discards the stale offer and can claim still-pending work only through a current lease

### Requirement: Success Means Confirmed Ordinary Handoff

Before attempting body delivery, a receiver SHALL durably register with CCCC the exact ordered set of attempts it will dispatch together. CCCC SHALL settle all attempts in that dispatch together after confirmed ordinary handoff to the selected ready body. Queue admission, stream or pull receipt, and provider storage SHALL remain distinct from confirmed handoff and task completion.

#### Scenario: Ready Body Confirms Handoff

- **WHEN** a current receiver confirms ordinary handoff of a registered batch to a ready body
- **THEN** CCCC records accepted handoff for every exact attempt in that batch
- **AND THEN** the provider tracks any later reply or task completion separately

#### Scenario: Adapter Can Only Confirm Queued Work

- **WHEN** a body adapter reports queued work and cannot establish actual handoff within the confirmation deadline
- **THEN** the receiver reports failure or uncertainty according to whether the adapter can establish that no handoff occurred

#### Scenario: Readiness Changes Before Any Handoff

- **WHEN** a registered batch encounters a definitive ready-only refusal before the body can receive it
- **THEN** CCCC records the dispatch as having had no handoff and allows the same receiver to defer that exact batch until readiness returns
- **AND THEN** only a new fenced start can authorize the later dispatch

### Requirement: Body Loss Before Confirmation Fails the Attempt

After dispatch start, body death, replacement, gateway loss, cancellation, or timeout SHALL produce a known unsuccessful outcome or uncertainty unless handoff was already confirmed. The same receiver SHALL only resume work it can establish had no handoff. Pending work SHALL return to CCCC when its unstarted claim retires.

#### Scenario: Body Restarts During Dispatch

- **WHEN** the selected body is replaced after the receiver records dispatch start and before handoff confirmation
- **THEN** the attempt fails or becomes uncertain according to the available evidence
- **AND THEN** the old dispatch authority is fenced from the replacement body

#### Scenario: Body Dies After Completed Success

- **WHEN** accepted handoff has completed and the body later dies
- **THEN** the accepted handoff remains recorded separately from task completion and is excluded from recovery delivery

### Requirement: Provider Outcomes Preserve Ambiguity

CCCC SHALL retain stable attempt identity and distinguish pending, staged, started, accepted, direct-read, refused, failed, and uncertain outcomes. Recovery SHALL return eligible unstarted or definitively unsent work to the pending queue. Started work with an unresolved exposure SHALL become uncertain and require explicit sender reconciliation.

#### Scenario: Body Receives Content but Acknowledgement Is Lost

- **WHEN** dispatch occurs and CCCC cannot establish a confirmed handoff outcome
- **THEN** the provider reports uncertainty and excludes that attempt from automatic re-offering

#### Scenario: Daemon Restarts With an Offered Attempt

- **WHEN** CCCC reconstructs a staged offer whose start was never durably recorded
- **THEN** the same pending work is available once under a current receiver lease
- **AND WHEN** the recovered attempt has a start marker with possible exposure and an unresolved outcome
- **THEN** it is reported as uncertain

### Requirement: Fresh Retries Belong to the Sender

CCCC SHALL retain chat after unsuccessful delivery. A fresh attempt following a terminal unsuccessful outcome SHALL require sender authorization, preserve the native source event, and use a new attempt identity. Retry of an uncertain handoff SHALL require explicit acknowledgment of possible duplication.

#### Scenario: Sender Retries a Refused Message

- **WHEN** the original sender requests a fresh attempt after a terminal readiness or capacity refusal recorded as retryable
- **THEN** CCCC queues a new attempt while retaining the earlier refusal receipt for the same event

#### Scenario: Another Actor Attempts Delivery Retry

- **WHEN** an Actor requests retry of an outgoing event it does not own
- **THEN** CCCC refuses the request before creating an attempt

#### Scenario: Uncertain Retry Lacks Explicit Duplicate Consent

- **WHEN** a sender requests retry of an uncertain handoff without acknowledging possible duplication
- **THEN** CCCC returns an uncertainty conflict without creating an attempt

### Requirement: Duplicate Transport Activity Does Not Create New Handoffs

CCCC SHALL serialize ownership of each attempt and preserve terminal outcomes. Repeated offers, starts, and settlements for the same delivery identity SHALL preserve exact membership without authorizing another handoff. Generic gateway source IDs SHALL remain correlation identifiers.

#### Scenario: Accepted Attempt Is Observed Again

- **WHEN** recovery encounters an accepted attempt
- **THEN** it reconciles the CCCC receipt without invoking body dispatch again

#### Scenario: Outcome Is Submitted Twice

- **WHEN** the receiver repeats the outcome for the same dispatched batch with valid scope and matching membership
- **THEN** CCCC returns the original settled outcome without generating another handoff

#### Scenario: A Batch Identity Is Reused With Different Attempts

- **WHEN** a receiver reuses a start or settlement identity with a different ordered set of attempts
- **THEN** CCCC returns a typed conflict and preserves the original dispatch decision

### Requirement: Reconnection Separates Observation From Delivery

Reconnect SHALL restore a current lease and recover eligible pending work through the receiver contract. History and receipt cursors SHALL support bounded observation independently of body delivery and Mail consumption. Recovery SHALL report observation gaps explicitly and keep history reads separate from prompt delivery.

#### Scenario: Events Arrive While the Gateway Is Down

- **WHEN** CCCC stores first-delivery chat work while the gateway is down
- **THEN** a gateway or direct CLI holding the current lease can pull the pending work in delivery order
- **AND THEN** failed, refused, or uncertain terminal events require a fresh sender-authorized attempt before delivery

#### Scenario: Observation Cursor Is Stale

- **WHEN** CCCC cannot resume an observation cursor
- **THEN** it reports an explicit gap or stale-cursor result and exposes bounded reconciliation
- **AND THEN** only the receiver's pending queue determines eligible delivery

## REMOVED Requirements

### Requirement: Readiness Refusal Is Immediate

**Reason**: Ordinary chat stays pending through receiver unavailability and body busy periods.

**Migration**: Use the pending chat delivery state and inspect exact per-message receipts. Continue applying immediate readiness admission to Mail notices.

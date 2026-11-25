# CCCC External Receiver Spec Delta

## ADDED Requirements

### Requirement: Gateway Queue Reads Have an Additive Receiver Capability

A compatible external receiver v2 service SHALL advertise `chat_gateway_queue_reads` when it supports `chat.gateway-read.claim`, `chat.gateway-read.result`, and gateway tool-read receipts through `chat.ack`. The gateway SHALL require the advertised capability for these tool-read operations.

#### Scenario: Provider Supports Ordinary Delivery Only

- **WHEN** an otherwise compatible v2 service omits `chat_gateway_queue_reads`
- **THEN** gateway tool-read claims report a capability error
- **AND THEN** ordinary prompt delivery and direct pull remain available under their existing negotiated capabilities

### Requirement: Gateway Tool Reads Claim an Exact Ordered Head

CCCC SHALL authorize a tool-read claim under the current gateway lease for the authenticated Actor registration. It SHALL atomically claim the requested ordered FIFO prefix of eligible staged chat attempts and preserve the supplied whole-batch boundaries. CCCC SHALL durably record the exact membership and grouping before authorizing the gateway to expose the result.

#### Scenario: Gateway Claims Whole Staged Batches

- **WHEN** a current gateway requests an exact eligible prefix of whole batches within the negotiated count and byte bounds
- **THEN** CCCC records all selected attempts and their ordered batch grouping in one claim
- **AND THEN** later arrivals remain eligible for a subsequent claim

#### Scenario: The Request Exceeds Its Negotiated Bounds

- **WHEN** the exact submitted prefix exceeds the negotiated count or byte bounds
- **THEN** CCCC rejects the claim with a typed limit error before changing any selected attempt

#### Scenario: The Submitted Head Is Stale

- **WHEN** the submitted attempts differ from the eligible staged head or the gateway lease has retired
- **THEN** CCCC rejects the claim without consuming a replacement batch
- **AND THEN** offers already deferred as one batch retain their recorded membership

#### Scenario: Tool Read Races Ordinary Prompt Dispatch

- **WHEN** a gateway read claim and ordinary prompt start compete for the same head
- **THEN** CCCC grants exactly one path authority over the contested attempts
- **AND THEN** the other path reports a conflict before exposing those attempts or changing their disposition

### Requirement: Gateway Tool Reads Reconcile by Caller Operation ID

CCCC SHALL scope a gateway read record to the authenticated Actor registration, the logical gateway binding tag derived by Houmao, and the caller operation ID. The durable record SHALL include the snapshot fingerprint, ordered attempt IDs, whole-batch grouping, and receipt state. Reusing an operation ID SHALL reconcile the recorded read or return a typed conflict on changed selection.

#### Scenario: Gateway Reconciles a Lost Pop Response

- **WHEN** the authorized gateway requests the result for the same binding and operation ID after a lost response, gateway restart, or lease rotation
- **THEN** CCCC returns the recorded selection, grouping, and receipt state during its advertised recovery period
- **AND THEN** lookup requires the Actor grant and matching binding tag and makes no new delivery attempt

#### Scenario: Caller Repeats a Successful Claim

- **WHEN** a caller repeats the operation ID with the same snapshot fingerprint and exact ordered batch membership
- **THEN** CCCC returns the original read decision without claiming another batch

#### Scenario: Caller Reuses an Operation ID With a Different Selection

- **WHEN** a caller presents the same scoped operation ID with a different fingerprint, attempt order, or grouping
- **THEN** CCCC returns a typed operation conflict and preserves the original record

#### Scenario: The Read Result Has Aged Out

- **WHEN** the caller requests reconciliation after the finite result recovery period
- **THEN** CCCC returns an explicit expiry outcome rather than using the operation ID to claim new work
- **AND THEN** CCCC retains the expired operation identity within the same Actor registration's scope

### Requirement: Gateway Tool Receipts Confirm Only the Exact Read

CCCC SHALL issue a finite gateway tool-read receipt scoped to the Actor registration, logical gateway binding tag, and exact claim. Acknowledgment through `chat.ack` SHALL confirm those attempts as a gateway tool read. A valid acknowledgment SHALL survive release or replacement of the intake lease.

#### Scenario: The Agent Acknowledges After Lease Rotation

- **WHEN** the gateway presents a valid receipt with the original Actor registration and matching binding tag after lease rotation
- **THEN** CCCC records the tool-read outcome for exactly those attempts
- **AND THEN** delivery status distinguishes that outcome from ordinary prompt handoff and direct CLI read

#### Scenario: The Same Receipt Is Acknowledged Again

- **WHEN** the authorized caller repeats acknowledgment of an already confirmed gateway tool read
- **THEN** CCCC returns the recorded outcome without changing any other delivery

#### Scenario: Receipt Authority Does Not Match the Claim

- **WHEN** an acknowledgment or result lookup uses another Actor registration or a different logical gateway binding tag
- **THEN** CCCC refuses access to the claim and leaves delivery state intact

#### Scenario: The Acknowledgment Deadline Expires With Possible Exposure

- **WHEN** a committed gateway tool read expires without acknowledgment and CCCC cannot rule out exposure
- **THEN** CCCC reports those exact attempts as uncertain and excludes them from automatic re-offering
- **AND THEN** a fresh delivery attempt requires the sender's explicit authorization for possible duplication

# Spec Delta

## Purpose

Define how Houmao owns, supervises, and recovers an agent whose native protocol endpoint persists across multiple managed requests.

## ADDED Requirements

### Requirement: One owner maintains the native connection

A service-mode launch SHALL establish an owner in the selected execution context that supervises the provider, owns its protocol connection, and serves the same agent across turns. Readiness SHALL require native initialization and a verified logical session. A client or gateway lifecycle change SHALL preserve the existing owner and provider.

#### Scenario: A client disconnects between turns

- **WHEN** two independent manager or gateway invocations submit successive prompts
- **THEN** both use the verified service incarnation and logical session and no provider is started for the second prompt

#### Scenario: Gateway restarts during active work

- **WHEN** the authenticated gateway reattaches to the current owner
- **THEN** the active operation remains observable and any terminal evidence stays attributable to its original request

### Requirement: Dispatch and recovery bind service and operation identities

The owner SHALL bind each accepted operation to the managed generation, service incarnation, native session, and request or turn correlation available on the wire. It SHALL persist active or uncertain work across caller loss and fence stale input, cancellation, replies, and events. Uncertain handoff SHALL NOT trigger automatic replay.

#### Scenario: Two public callers target one service

- **WHEN** manager and gateway calls compete before a service accepts either request
- **THEN** they share the same verified owner reservation
- **AND** only the request that owns the current service slot can cross the native prompt boundary

#### Scenario: An old service sends a late notification

- **WHEN** a new incarnation exists after the previous connection was lost
- **THEN** the late event cannot release the new slot or settle a different request

#### Scenario: Owner dies during a native write

- **WHEN** a replacement controller finds a request with uncertain native admission
- **THEN** it preserves the uncertainty, refuses conflicting mutation, and reconciles only from bound evidence

### Requirement: Service lifecycle and access are owner-bound

Verified owner-side stop SHALL reap the service and owned descendants. Explicit relaunch SHALL establish a new incarnation and require exact native continuation when selected. Missing or incompatible saved authorities SHALL fail before native prompt dispatch. Raw protocol endpoints and authentication material SHALL remain owner-private.

#### Scenario: Relaunch requests continuation

- **WHEN** the operator asks to continue a saved native session on a new service incarnation
- **THEN** the adapter verifies the saved ID, home and workspace before marking the new connection ready or fails explicitly

#### Scenario: Another local owner has an endpoint

- **WHEN** a client presents a service handle from another agent or obsolete generation
- **THEN** the owner refuses control without exposing the native protocol or its credentials

### Requirement: Bidirectional service traffic continues during a turn

The owner SHALL continuously drain protocol output and separate diagnostics. It SHALL route correlated notifications, settlements, and provider-initiated interactions while requests are pending. Unsupported interactions SHALL resolve through a documented bounded failure, and native policy SHALL remain enforceable.

#### Scenario: Native approval blocks prompt settlement

- **WHEN** the provider issues an approval request before returning a prompt response
- **THEN** the negotiated policy handles or declines it while the protocol reader continues draining messages

#### Scenario: A cancellation response precedes terminal evidence

- **WHEN** the provider accepts an interrupt while the native turn is still running
- **THEN** the owner retains that operation as pending until native settlement or explicitly bounded uncertainty

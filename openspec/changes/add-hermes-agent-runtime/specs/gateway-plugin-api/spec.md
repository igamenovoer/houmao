# Spec Delta

## MODIFIED Requirements

### Requirement: Ordinary Events Use Immediate Request-Scoped Dispatch

The SDK SHALL dispatch ordinary events immediately only after verifying gateway, plugin, and current body readiness. Success SHALL follow confirmed handoff to that body. The SDK SHALL let a verified Hermes TUI receipt confirm handoff while native execution is queued. It SHALL NOT acknowledge locally pending work, cache an event for later delivery, or enqueue a retry. Invalid and oversized input SHALL fail explicitly within finite request bounds.

#### Scenario: Ready Body Receives an Ordinary Event

- **WHEN** an authorized plugin dispatches a valid event to a ready body and the adapter confirms handoff to that same body
- **THEN** the request succeeds with a dispatched result and its source event ID
- **AND THEN** success does not claim that the agent finished processing the message or completed its turn

#### Scenario: Busy Body Refuses an Event

- **WHEN** the body is busy or not decisively ready when an event arrives
- **THEN** the request returns a retryable readiness error without waiting for readiness
- **AND THEN** no message payload is accepted into a deferred inbox or retry spool

#### Scenario: Invalid or Oversized Event Is Supplied

- **WHEN** the supplied event violates its schema or configured finite envelope-size bound
- **THEN** the request returns a non-retryable input error without dispatch or deferred acceptance

#### Scenario: Old Worker Uses a Revoked Context

- **WHEN** a worker tries to dispatch after its instance's context generation has been revoked
- **THEN** the SDK returns an explicit unavailable error
- **AND THEN** it does not retain the message or send it through a replacement context

#### Scenario: Hermes Native Queue Owns the Accepted Event

- **WHEN** the plugin passes the final native idle check and Hermes commits a queue entry for that exact event
- **THEN** the SDK returns confirmed handoff with the source event ID and the native queued disposition
- **AND THEN** the request creates no Houmao deferred copy or retry
- **AND THEN** the disposition leaves native turn start and completion separate

### Requirement: Plugin Workers Can Observe Ordinary Prompt Readiness

The SDK SHALL expose a read-only ordinary prompt readiness signal to supervised workers under their current plugin context. The signal SHALL only advertise readiness for the current body and stop on context revocation. Dispatch SHALL still apply the host's authoritative readiness and identity checks for the specific event. For Hermes TUI, the final native idle observation authorizes one submit attempt and does not reserve native idle against concurrent human input.

#### Scenario: An Agent Becomes Ready

- **WHEN** a supervised worker observes a transition to ordinary prompt readiness
- **THEN** it can consider submitting an event through the existing immediate dispatch operation
- **AND THEN** the observation itself reserves no admission and submits no work

#### Scenario: The Body Becomes Busy After a Ready Signal

- **WHEN** a worker submits an ordinary event after a ready observation and the body is busy at the final readiness check
- **THEN** dispatch returns the ordinary typed readiness error without submitting the event to the body or storing it for later admission

#### Scenario: The Host Revokes a Waiting Plugin Context

- **WHEN** a plugin context is revoked while its worker is observing readiness
- **THEN** the observation ends or fails explicitly and supplies no readiness from a replacement context

#### Scenario: A Human Turn Starts After the Hermes Readiness Check

- **WHEN** the final check succeeds and native submit returns a verified queued receipt because a human input reached Hermes first
- **THEN** the SDK reports the accepted native disposition to that event's caller
- **AND THEN** the gateway observes that admission without sending the event again

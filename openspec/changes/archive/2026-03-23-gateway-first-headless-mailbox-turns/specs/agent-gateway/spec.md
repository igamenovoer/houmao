## ADDED Requirements

### Requirement: Shared gateway mailbox facade supports explicit read-state updates by opaque message reference
For mailbox-enabled sessions whose live gateway listener is bound to loopback, the shared gateway mailbox facade SHALL expose `POST /v1/mail/state` alongside the existing shared mailbox routes.

That shared mailbox state-update route SHALL accept exactly one opaque `message_ref` target and the explicit read-state mutation field it supports in this change.

For this change, the shared mailbox state-update contract SHALL support explicit single-message `read` mutation for one message addressed to the current session principal and SHALL reject broader mailbox-state fields such as `starred`, `archived`, or `deleted`.

The gateway SHALL resolve that request through the same manifest-backed mailbox adapter boundary used by the other `/v1/mail/*` routes rather than by inventing a second transport-local state path inside the gateway service layer.

The shared mailbox state-update route SHALL remain loopback-only under the same listener-availability rules as the rest of the shared `/v1/mail/*` surface.

The shared mailbox state-update route SHALL NOT consume the single terminal-mutation slot used by `POST /v1/requests`.

The shared mailbox state-update route SHALL return a structured acknowledgment of the resulting read state for that `message_ref` rather than a full delivered-message envelope.

#### Scenario: Filesystem-backed session marks one processed message read through the shared facade
- **WHEN** a caller invokes `POST /v1/mail/state` for a loopback-bound filesystem mailbox session with a valid opaque `message_ref` and `read=true`
- **THEN** the gateway applies that read-state update for the current session principal through the filesystem mailbox adapter
- **AND THEN** the canonical message content remains immutable while recipient-local read state changes

#### Scenario: Stalwart-backed session marks one processed message read through the shared facade
- **WHEN** a caller invokes `POST /v1/mail/state` for a loopback-bound `stalwart` mailbox session with a valid opaque `message_ref` and `read=true`
- **THEN** the gateway applies that read-state update through the Stalwart-backed mailbox adapter
- **AND THEN** the caller does not need to understand transport-owned message identifiers to complete that update

## ADDED Requirements

### Requirement: Shared gateway mailbox facade exposes lifecycle routes
For mailbox-enabled sessions whose live gateway listener is bound to loopback, the shared gateway mailbox facade SHALL expose lifecycle routes for:

- `GET /v1/mail/status`,
- `POST /v1/mail/list`,
- `POST /v1/mail/peek`,
- `POST /v1/mail/read`,
- `POST /v1/mail/send`,
- `POST /v1/mail/post`,
- `POST /v1/mail/reply`,
- `POST /v1/mail/mark`,
- `POST /v1/mail/move`,
- `POST /v1/mail/archive`.

`POST /v1/mail/list` SHALL accept a mailbox box selector and return metadata suitable for triage without marking listed messages read.

`POST /v1/mail/peek` SHALL return one selected message without changing read state.

`POST /v1/mail/read` SHALL return one selected message and mark it read for the current mailbox principal.

`POST /v1/mail/mark` SHALL allow explicit manual marking of supported recipient-local state fields, including `read` and `answered`.

`POST /v1/mail/move` SHALL move selected messages among supported mailbox boxes.

`POST /v1/mail/archive` SHALL remain as a shortcut for moving selected messages to the archive box and marking them archived.

The gateway SHALL continue to use the manifest-backed mailbox adapter boundary for all shared mailbox lifecycle routes and SHALL NOT require callers to read or write transport-local SQLite state, filesystem `rules/`, or Stalwart-native objects directly.

#### Scenario: Peek does not mutate read state through the gateway
- **WHEN** a caller invokes `POST /v1/mail/peek` with a valid opaque `message_ref`
- **THEN** the gateway returns the message body and metadata through the shared mailbox facade
- **AND THEN** the recipient-local read state for that message does not change

#### Scenario: Read mutates read state through the gateway
- **WHEN** a caller invokes `POST /v1/mail/read` with a valid opaque `message_ref`
- **THEN** the gateway returns the message body and metadata through the shared mailbox facade
- **AND THEN** the recipient-local read state for that message is `true`

#### Scenario: Archive shortcut remains available
- **WHEN** a caller invokes `POST /v1/mail/archive` with selected opaque message refs
- **THEN** the gateway moves those messages into the archive box through the shared mailbox adapter
- **AND THEN** the response reports those messages as archived and no longer open inbox work

### Requirement: Gateway reply marks the parent message answered
When `POST /v1/mail/reply` succeeds, the gateway SHALL ask the shared mailbox adapter to mark the replied message `answered=true` and `read=true` for the current mailbox principal.

That automatic reply state update SHALL NOT archive the replied message.

#### Scenario: Gateway reply acknowledges without closing the mail
- **WHEN** a caller sends a reply through `POST /v1/mail/reply`
- **THEN** the gateway response reflects that the parent message is answered for the current principal
- **AND THEN** the parent message remains open inbox work until an archive or move operation closes it

## REMOVED Requirements

### Requirement: Shared gateway mailbox facade supports explicit read-state updates by opaque message reference
**Reason**: The old `/v1/mail/state` contract only supported `read=true`; lifecycle state now requires explicit read versus peek behavior, answered state, box moves, and archive.
**Migration**: No compatibility migration is required. Callers must use `/v1/mail/read` for mutating body reads, `/v1/mail/mark` for manual state repair, `/v1/mail/move` for box changes, and `/v1/mail/archive` for the common archive shortcut.

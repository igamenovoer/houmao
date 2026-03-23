## MODIFIED Requirements

### Requirement: Gateway HTTP API provides dedicated shared mailbox routes without broadening terminal-mutating request kinds
The gateway SHALL expose dedicated mailbox routes for mailbox-enabled sessions in addition to its existing health, status, request, and notifier routes.

That shared mailbox surface SHALL include:

- `GET /v1/mail/status`
- `POST /v1/mail/check`
- `POST /v1/mail/send`
- `POST /v1/mail/reply`

The shared mailbox routes in this change SHALL be limited to mailbox functions supported by both the filesystem transport and the `stalwart` transport.

The shared mailbox routes SHALL use structured request and response payloads and SHALL NOT require callers to read or write transport-local SQLite state, filesystem `rules/`, or Stalwart-native objects directly.

In this change, the shared mailbox routes SHALL be served only when the live gateway listener is bound to loopback.

When the live gateway listener is bound to `0.0.0.0`, `GET /v1/mail/status`, `POST /v1/mail/check`, `POST /v1/mail/send`, and `POST /v1/mail/reply` SHALL fail explicitly as unavailable until an explicit authentication model exists for broader listeners.

Read-oriented mailbox routes and mailbox send or reply routes SHALL NOT consume the terminal-mutation slot used by `POST /v1/requests`.

If the managed session has no mailbox binding or the gateway cannot construct a mailbox adapter from the manifest-backed binding, mailbox route calls SHALL fail explicitly rather than pretending mailbox support exists.

#### Scenario: Filesystem-backed mailbox check uses the dedicated gateway mail surface
- **WHEN** a caller performs mailbox `check` against a mailbox-enabled session whose resolved mailbox transport is `filesystem`
- **THEN** the live gateway serves that operation through `POST /v1/mail/check`
- **AND THEN** the caller receives normalized mailbox message metadata without reading mailbox-local SQLite directly

#### Scenario: Stalwart-backed mailbox reply uses the same dedicated gateway mail surface
- **WHEN** a caller performs mailbox `reply` against a mailbox-enabled session whose resolved mailbox transport is `stalwart`
- **THEN** the live gateway serves that operation through `POST /v1/mail/reply`
- **AND THEN** the caller uses the same shared gateway mailbox contract rather than Stalwart-native transport objects directly

#### Scenario: Session without mailbox binding rejects gateway mailbox routes explicitly
- **WHEN** a caller invokes a gateway mailbox route for a managed session whose manifest has no mailbox binding
- **THEN** the gateway rejects that mailbox route call explicitly
- **AND THEN** it does not claim mailbox support for that session

#### Scenario: Non-loopback gateway listener rejects shared mailbox routes
- **WHEN** a live gateway listener is bound to `0.0.0.0`
- **AND WHEN** a caller invokes one of the shared `/v1/mail/*` routes
- **THEN** the gateway rejects that mailbox route call as unavailable for the current listener configuration
- **AND THEN** terminal-mutating routes remain available under their existing listener rules

### Requirement: The gateway serializes terminal-mutating work and applies admission policy
In v1, the public terminal-mutating request kinds SHALL remain exactly `submit_prompt` and `interrupt`.

Mailbox transport operations SHALL use the dedicated `/v1/mail/*` routes rather than introducing new public terminal-mutating request kinds.

#### Scenario: Mailbox send does not create a new public terminal-mutating request kind
- **WHEN** a caller uses the gateway to perform mailbox `send`
- **THEN** that operation uses the dedicated gateway mailbox surface rather than `POST /v1/requests`
- **AND THEN** the public terminal-mutating request-kind set remains limited to `submit_prompt` and `interrupt`

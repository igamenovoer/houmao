## ADDED Requirements

### Requirement: Gateway supports ephemeral ranked reminder records
The live gateway SHALL expose dedicated reminder routes for direct timer-backed reminder registration without requiring mailbox participation.

That reminder surface SHALL include:

- `POST /v1/reminders`
- `GET /v1/reminders`
- `GET /v1/reminders/{reminder_id}`
- `PUT /v1/reminders/{reminder_id}`
- `DELETE /v1/reminders/{reminder_id}`

Each reminder record SHALL include:

- a non-empty `title`
- a non-empty `prompt`
- a signed `ranking` value whose ordering is ascending and is not restricted to non-negative values
- a `paused` flag
- either one-off scheduling with exactly one requested due time or repeating scheduling with an interval and next due time

The gateway SHALL keep registered reminders entirely in the live gateway process memory. Pending reminders and due-but-not-yet-executed reminder occurrences SHALL NOT survive gateway shutdown or restart.

The live gateway SHALL nominate exactly one effective reminder at a time using this deterministic order:

1. smallest `ranking`
2. earliest `created_at`
3. smallest `reminder_id` in lexical order

All non-effective reminders SHALL remain blocked behind that selected reminder even when they are already due.

Deleting a reminder SHALL remove that reminder while it remains registered. If execution of one reminder occurrence has already started, deleting the reminder SHALL NOT retroactively retract that already-started prompt execution.

Unknown `reminder_id` lookups, updates, or deletions SHALL fail explicitly rather than pretending the reminder still exists.

#### Scenario: Caller registers multiple reminders in one request
- **WHEN** a caller submits `POST /v1/reminders` with more than one reminder definition
- **THEN** the live gateway creates one reminder record for each submitted definition
- **AND THEN** `GET /v1/reminders` exposes the created reminder set through the live gateway listener

#### Scenario: Smallest ranking becomes the effective reminder
- **WHEN** the live gateway holds reminder records with different ranking values
- **THEN** the reminder with the smallest ranking value is the effective reminder
- **AND THEN** all higher-ranking reminders remain blocked until the effective reminder is updated or removed

#### Scenario: Equal ranking uses deterministic tie-breaking
- **WHEN** two reminder records have the same ranking value
- **THEN** the live gateway breaks the tie by creation order and then `reminder_id`
- **AND THEN** repeated inspection returns the same effective reminder until the reminder set changes

#### Scenario: Gateway restart drops pending reminders
- **WHEN** the live gateway stops or restarts while one or more reminders are still registered
- **THEN** those pending reminders are lost
- **AND THEN** the restarted gateway does not recover them from gateway persistence artifacts

#### Scenario: Removing the effective reminder promotes the next reminder
- **WHEN** a caller deletes the current effective reminder while another reminder remains registered
- **THEN** the live gateway removes the deleted reminder explicitly
- **AND THEN** the next reminder in ranking order becomes the effective reminder

### Requirement: Due effective reminders remain gateway-owned low-priority internal prompt delivery
When the effective reminder becomes due, the gateway SHALL treat delivery of that reminder prompt as gateway-owned internal execution behavior rather than as a new externally visible public request kind.

The public terminal-mutating request-kind set SHALL remain limited to `submit_prompt` and `interrupt`.

Before a due effective reminder prompt starts execution, the gateway SHALL require:

- request admission to be open
- no active terminal-mutating execution
- zero durable public queue depth
- the effective reminder not to be paused

If those conditions are not satisfied when the effective reminder becomes due, the gateway SHALL keep that reminder pending in memory and SHALL retry later instead of dropping the reminder or converting it into durable queued work.

A paused effective reminder SHALL keep its ranking position and SHALL continue blocking lower-ranked reminders until it is resumed, reranked, or removed.

Repeating reminders SHALL maintain at most one pending due occurrence per reminder. Missed intervals during a busy or paused period SHALL NOT produce a catch-up burst of multiple immediate prompt deliveries once the reminder becomes eligible again.

#### Scenario: Busy gateway defers a due effective reminder
- **WHEN** the effective reminder becomes due while request admission is blocked, active execution is running, or durable public queue depth is non-zero
- **THEN** the gateway does not start that reminder prompt immediately
- **AND THEN** the effective reminder remains pending in memory until a later safe execution opportunity

#### Scenario: Paused effective reminder blocks lower-ranked due reminders
- **WHEN** the effective reminder is paused and one or more lower-ranked reminders are already due
- **THEN** the gateway does not submit the paused reminder prompt
- **AND THEN** it also does not submit the lower-ranked reminder prompts while the paused effective reminder still owns the ranking slot

#### Scenario: Due reminder does not expand the public request-kind set
- **WHEN** an effective reminder prompt is delivered after becoming due
- **THEN** that delivery happens through gateway-owned internal behavior rather than a new public `POST /v1/requests` kind
- **AND THEN** the public terminal-mutating request kinds remain exactly `submit_prompt` and `interrupt`

#### Scenario: Repeating reminder does not backfill missed intervals as a burst
- **WHEN** a repeating effective reminder remains overdue across multiple interval boundaries because the gateway is busy or the effective reminder is paused
- **THEN** the gateway preserves at most one pending overdue occurrence for that reminder
- **AND THEN** the gateway does not emit one immediate prompt for every missed interval once the reminder becomes eligible again

## MODIFIED Requirements

### Requirement: The gateway exposes a structured HTTP API on the resolved listener address
The gateway SHALL expose an HTTP API for health inspection, status inspection, gateway-managed request submission, reminder registration and inspection, gateway-owned notifier control, and, when permitted by mailbox bindings and listener policy, shared mailbox operations on the resolved listener address for that session.

The base gateway HTTP API SHALL expose `GET /health`, `GET /v1/status`, and `POST /v1/requests`.

The reminder HTTP API SHALL additionally expose `POST /v1/reminders`, `GET /v1/reminders`, `GET /v1/reminders/{reminder_id}`, `PUT /v1/reminders/{reminder_id}`, and `DELETE /v1/reminders/{reminder_id}`.

For mailbox-enabled sessions whose live gateway listener is bound to loopback, that HTTP API SHALL additionally expose `GET /v1/mail/status`, `POST /v1/mail/check`, `POST /v1/mail/send`, `POST /v1/mail/post`, `POST /v1/mail/reply`, and `POST /v1/mail/state`.

When the gateway mail notifier capability is implemented, that HTTP API SHALL additionally expose `PUT /v1/mail-notifier`, `GET /v1/mail-notifier`, and `DELETE /v1/mail-notifier`.

`GET /health` SHALL return a structured response suitable for runtime launch-readiness checks and SHALL include gateway protocol-version information.

`GET /health` SHALL reflect gateway-local process and control-plane health, and SHALL NOT fail solely because the managed agent is unavailable, recovering, or awaiting rebind.

`GET /v1/status` SHALL return the same versioned status model that the gateway persists to `state.json`.

`POST /v1/requests` SHALL accept typed request-creation payloads and SHALL return the accepted queued request record.

The reminder routes SHALL be served by the gateway sidecar itself and SHALL use structured request and response payloads rather than requiring callers to mutate gateway memory or private runtime objects directly.

The notifier control endpoints SHALL be served by the gateway sidecar itself and SHALL use structured request and response payloads rather than requiring callers to read or write gateway SQLite state directly.

The shared mailbox routes SHALL be limited to mailbox status, `check`, ordinary `send`, operator-origin `post`, `reply`, and explicit single-message read-state update behavior.

Ordinary `send`, `reply`, and read-state update behavior SHALL continue using the shared mailbox abstraction across both the filesystem and `stalwart` transports. Operator-origin `post` SHALL support only filesystem mailbox bindings in v1 and SHALL fail explicitly for other transports.

Those shared mailbox routes SHALL use structured request and response payloads and SHALL NOT require callers to read or write transport-local SQLite state, filesystem `rules/`, or Stalwart-native objects directly.

That HTTP API SHALL be served by the gateway sidecar itself and SHALL use structured request and response payloads rather than requiring callers to read or write SQLite state directly.

Request-validation failures on `POST /v1/requests` SHALL return HTTP `422`. Explicit gateway policy rejection SHALL return HTTP `403`. Request-state conflicts such as reconciliation-required admission blocking SHALL return HTTP `409`. Managed-agent unavailable or recovery-blocked admission failures SHALL return HTTP `503`.

Reminder-route validation failures SHALL return HTTP `422`. Unknown reminder identifiers on `GET /v1/reminders/{reminder_id}`, `PUT /v1/reminders/{reminder_id}`, or `DELETE /v1/reminders/{reminder_id}` SHALL return HTTP `404`.

Notifier validation failures SHALL return HTTP `422`. Attempts to enable notifier behavior for sessions that cannot support it SHALL fail explicitly rather than pretending that notifier polling is active.

Shared mailbox route validation failures SHALL return HTTP `422`. Calls to mailbox routes for sessions without mailbox bindings SHALL fail explicitly rather than pretending mailbox support exists. When the live gateway listener is bound to `0.0.0.0`, the `/v1/mail/*` routes SHALL fail explicitly as unavailable until an authentication model exists for broader listeners.

Read-oriented HTTP endpoints and mailbox read routes SHALL NOT consume the terminal-mutation slot solely to report current gateway health, core status, reminder state, notifier status, or shared mailbox state.

#### Scenario: Health inspection uses default loopback surface
- **WHEN** a tool inspects a gateway-managed session whose resolved gateway host is `127.0.0.1`
- **THEN** it can query `GET /health` through the loopback HTTP surface on the resolved port
- **AND THEN** the gateway returns a structured health response without requiring direct SQLite access

#### Scenario: Gateway health remains readable during upstream recovery
- **WHEN** the gateway companion remains healthy but the managed agent is unavailable, recovering, or awaiting rebind
- **THEN** `GET /health` still returns a structured gateway-local health response for that running gateway instance
- **AND THEN** callers use `GET /v1/status` to inspect managed-agent connectivity, recovery, and admission state

#### Scenario: Status inspection matches the stable state artifact
- **WHEN** a tool queries `GET /v1/status` for a gateway-managed session
- **THEN** the gateway returns the same versioned status model that it persists to `state.json`
- **AND THEN** local readers can rely on either surface without schema drift

#### Scenario: Request submission uses all-interface surface when configured
- **WHEN** a tool submits gateway-managed terminal-mutating work for a session whose resolved gateway host is `0.0.0.0`
- **THEN** it may submit that work through `POST /v1/requests` on any reachable host interface address on the resolved port
- **AND THEN** the gateway validates and records the request before it can compete for execution

#### Scenario: Reminder registration uses the live gateway HTTP surface
- **WHEN** a caller needs to register, inspect, update, or cancel live reminders for an attached gateway-managed session
- **THEN** the caller uses the dedicated `/v1/reminders` route family on that live gateway listener
- **AND THEN** the caller does not need to mutate private runtime state or transport queue artifacts directly

#### Scenario: Unknown reminder identifier fails explicitly
- **WHEN** a caller requests `GET /v1/reminders/{reminder_id}`, `PUT /v1/reminders/{reminder_id}`, or `DELETE /v1/reminders/{reminder_id}` for a non-existent reminder
- **THEN** the gateway rejects that call explicitly
- **AND THEN** it does not pretend that the requested reminder still exists

#### Scenario: Filesystem-backed mailbox check uses the dedicated gateway mail surface
- **WHEN** a caller performs mailbox `check` against a mailbox-enabled session whose resolved mailbox transport is `filesystem`
- **THEN** the live gateway serves that operation through `POST /v1/mail/check`
- **AND THEN** the caller receives normalized mailbox message metadata without reading mailbox-local SQLite directly

## REMOVED Requirements

### Requirement: Gateway supports ephemeral one-off and repeating wakeup jobs
**Reason**: The wakeup job contract is being replaced by ranked reminder records with batch creation, title, ranking, and pause semantics.
**Migration**: Use the `/v1/reminders` route family and the reminder record model instead of `/v1/wakeups` and wakeup jobs.

### Requirement: Due wakeups remain gateway-owned low-priority internal prompt delivery
**Reason**: The internal-delivery rules now apply to the effective reminder selected from the ranked reminder set, not to independent wakeup jobs.
**Migration**: Apply the same readiness-gated internal prompt-delivery expectations to effective reminders under the new reminder model.

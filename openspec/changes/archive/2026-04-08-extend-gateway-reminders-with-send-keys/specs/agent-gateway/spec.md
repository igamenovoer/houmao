## MODIFIED Requirements

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
- exactly one delivery form:
  - a non-empty semantic `prompt`, or
  - a `send_keys` object with a non-empty `sequence`
- a `delivery_kind` inspection value that distinguishes `prompt` from `send_keys`
- a signed `ranking` value whose ordering is ascending and is not restricted to non-negative values
- a `paused` flag
- either one-off scheduling with exactly one requested due time or repeating scheduling with an interval and next due time

The reminder `send_keys` object SHALL support:

- `sequence`
- `ensure_enter`, defaulting to `true`

The gateway SHALL keep registered reminders entirely in the live gateway process memory. Pending reminders and due-but-not-yet-executed reminder occurrences SHALL NOT survive gateway shutdown or restart.

The live gateway SHALL nominate exactly one effective reminder at a time using this deterministic order:

1. smallest `ranking`
2. earliest `created_at`
3. smallest `reminder_id` in lexical order

All non-effective reminders SHALL remain blocked behind that selected reminder even when they are already due.

Deleting a reminder SHALL remove that reminder while it remains registered. If execution of one reminder occurrence has already started, deleting the reminder SHALL NOT retroactively retract that already-started reminder execution.

Unknown `reminder_id` lookups, updates, or deletions SHALL fail explicitly rather than pretending the reminder still exists.

When a reminder uses `send_keys`, the gateway SHALL validate support for raw control input against the current attached gateway target during create and update. If the attached target cannot preserve exact raw control-input semantics, the gateway SHALL reject that reminder definition explicitly instead of accepting it for later failure.

#### Scenario: Caller registers a prompt reminder
- **WHEN** a caller submits `POST /v1/reminders` with a reminder definition containing a non-empty `prompt` and no `send_keys`
- **THEN** the live gateway creates that reminder successfully
- **AND THEN** the created reminder reports `delivery_kind = "prompt"`

#### Scenario: Caller registers a send-keys reminder
- **WHEN** a caller submits `POST /v1/reminders` with a reminder definition containing `send_keys.sequence`
- **THEN** the live gateway creates that reminder successfully when the attached target supports raw control input
- **AND THEN** the created reminder reports `delivery_kind = "send_keys"`

#### Scenario: Smallest ranking becomes the effective reminder
- **WHEN** the live gateway holds reminder records with different ranking values
- **THEN** the reminder with the smallest ranking value is the effective reminder
- **AND THEN** all higher-ranking reminders remain blocked until the effective reminder is updated or removed

#### Scenario: Reminder definition with both delivery forms is rejected
- **WHEN** a caller submits a reminder definition that includes both `prompt` and `send_keys`
- **THEN** the gateway rejects that reminder definition explicitly
- **AND THEN** it does not accept an ambiguous delivery mode

#### Scenario: Unsupported backend rejects a send-keys reminder
- **WHEN** a caller submits or updates a reminder definition with `send_keys`
- **AND WHEN** the current attached gateway target cannot preserve raw control-input semantics
- **THEN** the gateway rejects that reminder definition explicitly
- **AND THEN** it does not keep a reminder that would only fail later when due

### Requirement: Due effective reminders remain gateway-owned low-priority internal prompt delivery
When the effective reminder becomes due, the gateway SHALL treat delivery of that reminder as gateway-owned internal execution behavior rather than as a new externally visible public request kind.

The public terminal-mutating request-kind set SHALL remain limited to `submit_prompt` and `interrupt`.

Before a due effective reminder starts execution, the gateway SHALL require:

- request admission to be open
- no active terminal-mutating execution
- zero durable public queue depth
- the effective reminder not to be paused

If those conditions are not satisfied when the effective reminder becomes due, the gateway SHALL keep that reminder pending in memory and SHALL retry later instead of dropping the reminder or converting it into durable queued work.

A paused effective reminder SHALL keep its ranking position and SHALL continue blocking lower-ranked reminders until it is resumed, reranked, or removed.

Repeating reminders SHALL maintain at most one pending due occurrence per reminder. Missed intervals during a busy or paused period SHALL NOT produce a catch-up burst of multiple immediate deliveries once the reminder becomes eligible again.

When a due effective reminder uses semantic `prompt` delivery, the gateway SHALL submit exactly that reminder prompt through the existing internal prompt-delivery path.

When a due effective reminder uses `send_keys` delivery, the gateway SHALL submit raw control input through the same exact control-input lane used by gateway send-keys behavior.

For send-keys reminders:

- the gateway SHALL interpret `<[key-name]>` tokens using the same raw control-input grammar used by the gateway send-keys path,
- the reminder SHALL NOT expose a reminder-specific `escape_special_keys` override,
- the gateway SHALL NOT submit `title` or `prompt` text as terminal input for that reminder,
- `ensure_enter=true` SHALL ensure that the delivered control-input sequence ends with exactly one trailing Enter,
- `ensure_enter=false` SHALL preserve the supplied sequence exactly.

#### Scenario: Busy gateway defers a due effective reminder
- **WHEN** the effective reminder becomes due while request admission is blocked, active execution is running, or durable public queue depth is non-zero
- **THEN** the gateway does not start that reminder immediately
- **AND THEN** the effective reminder remains pending in memory until a later safe execution opportunity

#### Scenario: Paused effective reminder blocks lower-ranked due reminders
- **WHEN** the effective reminder is paused and one or more lower-ranked reminders are already due
- **THEN** the gateway does not submit the paused reminder delivery
- **AND THEN** it also does not submit the lower-ranked reminder deliveries while the paused effective reminder still owns the ranking slot

#### Scenario: Due reminder does not expand the public request-kind set
- **WHEN** an effective reminder is delivered after becoming due
- **THEN** that delivery happens through gateway-owned internal behavior rather than a new public `POST /v1/requests` kind
- **AND THEN** the public terminal-mutating request kinds remain exactly `submit_prompt` and `interrupt`

#### Scenario: Send-keys reminder delivers raw control input without title or prompt text
- **WHEN** a due effective reminder uses `send_keys`
- **THEN** the gateway submits the reminder's control-input sequence through the raw control-input lane
- **AND THEN** it does not synthesize `title` or semantic `prompt` text into that terminal input

#### Scenario: Send-keys reminder with ensure-enter true ends with one trailing Enter
- **WHEN** a due effective reminder uses `send_keys` with `ensure_enter=true`
- **THEN** the gateway delivers a control-input sequence that ends with one trailing Enter
- **AND THEN** it does not deliver two trailing Enter presses when the caller already supplied `<[Enter]>`

#### Scenario: Send-keys reminder with ensure-enter false preserves exact sequence
- **WHEN** a due effective reminder uses `send_keys` with `ensure_enter=false`
- **THEN** the gateway delivers the supplied control-input sequence exactly
- **AND THEN** it does not append an implicit Enter

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

The reminder request models SHALL support either semantic `prompt` delivery or raw `send_keys` delivery, but SHALL require exactly one of those delivery forms for each reminder definition.

Reminder-route validation failures SHALL return HTTP `422`. Unknown reminder identifiers on `GET /v1/reminders/{reminder_id}`, `PUT /v1/reminders/{reminder_id}`, or `DELETE /v1/reminders/{reminder_id}` SHALL return HTTP `404`.

The notifier control endpoints SHALL be served by the gateway sidecar itself and SHALL use structured request and response payloads rather than requiring callers to read or write gateway SQLite state directly.

The shared mailbox routes SHALL be limited to mailbox status, `check`, ordinary `send`, operator-origin `post`, `reply`, and explicit single-message read-state update behavior.

Ordinary `send`, `reply`, and read-state update behavior SHALL continue using the shared mailbox abstraction across both the filesystem and `stalwart` transports. Operator-origin `post` SHALL support only filesystem mailbox bindings in v1 and SHALL fail explicitly for other transports.

Those shared mailbox routes SHALL use structured request and response payloads and SHALL NOT require callers to read or write transport-local SQLite state, filesystem `rules/`, or Stalwart-native objects directly.

That HTTP API SHALL be served by the gateway sidecar itself and SHALL use structured request and response payloads rather than requiring callers to read or write SQLite state directly.

Request-validation failures on `POST /v1/requests` SHALL return HTTP `422`. Explicit gateway policy rejection SHALL return HTTP `403`. Request-state conflicts such as reconciliation-required admission blocking SHALL return HTTP `409`. Managed-agent unavailable or recovery-blocked admission failures SHALL return HTTP `503`.

Notifier validation failures SHALL return HTTP `422`. Attempts to enable notifier behavior for sessions that cannot support it SHALL fail explicitly rather than pretending that notifier polling is active.

Shared mailbox route validation failures SHALL return HTTP `422`. Calls to mailbox routes for sessions without mailbox bindings SHALL fail explicitly rather than pretending mailbox support exists. When the live gateway listener is bound to `0.0.0.0`, the `/v1/mail/*` routes SHALL fail explicitly as unavailable until an authentication model exists for broader listeners.

Read-oriented HTTP endpoints and mailbox read routes SHALL NOT consume the terminal-mutation slot solely to report current gateway health, core status, reminder state, notifier status, or shared mailbox state.

#### Scenario: Reminder registration uses the live gateway HTTP surface
- **WHEN** a caller needs to register, inspect, update, or cancel live reminders for an attached gateway-managed session
- **THEN** the caller uses the dedicated `/v1/reminders` route family on that live gateway listener
- **AND THEN** the caller does not need to mutate private runtime state or transport queue artifacts directly

#### Scenario: Send-keys reminder request is validated through the reminder route family
- **WHEN** a caller submits a reminder definition with `send_keys` through `/v1/reminders`
- **THEN** the reminder request is validated on that reminder route family
- **AND THEN** the caller does not need to use a separate reminder-specific control-input route

#### Scenario: Unknown reminder identifier fails explicitly
- **WHEN** a caller requests `GET /v1/reminders/{reminder_id}`, `PUT /v1/reminders/{reminder_id}`, or `DELETE /v1/reminders/{reminder_id}` for a non-existent reminder
- **THEN** the gateway rejects that call explicitly
- **AND THEN** it does not pretend that the requested reminder still exists

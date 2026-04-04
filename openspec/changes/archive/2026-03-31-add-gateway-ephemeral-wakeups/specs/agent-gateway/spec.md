## ADDED Requirements

### Requirement: Gateway supports ephemeral one-off and repeating wakeup jobs
The live gateway SHALL expose dedicated wakeup routes for direct timer registration without requiring mailbox participation.

That wakeup surface SHALL include:

- `POST /v1/wakeups`
- `GET /v1/wakeups`
- `GET /v1/wakeups/{job_id}`
- `DELETE /v1/wakeups/{job_id}`

Each wakeup job SHALL include a predefined prompt and SHALL use either:

- one-off mode with exactly one requested due time, or
- repeating mode with an interval and next due time.

The gateway SHALL keep registered wakeup jobs entirely in the live gateway process memory. Pending wakeup jobs and due-but-not-yet-executed wakeup occurrences SHALL NOT survive gateway shutdown or restart.

Deleting a wakeup job SHALL cancel that job while it remains scheduled. Deleting a repeating wakeup job SHALL stop future repetitions. If execution of one wakeup occurrence has already started, deleting the job SHALL NOT retroactively retract that already-started prompt execution.

Unknown `job_id` lookups or cancellations SHALL fail explicitly rather than pretending the wakeup still exists.

#### Scenario: Caller registers one one-off wakeup
- **WHEN** a caller submits `POST /v1/wakeups` with a predefined prompt and one one-off due time
- **THEN** the live gateway returns a wakeup job identifier for that scheduled wakeup
- **AND THEN** the new wakeup is visible through `GET /v1/wakeups` and `GET /v1/wakeups/{job_id}` while it remains scheduled

#### Scenario: Caller registers one repeating wakeup
- **WHEN** a caller submits `POST /v1/wakeups` with mode `repeat`, a predefined prompt, and a repeat interval
- **THEN** the live gateway schedules a repeating wakeup for that job
- **AND THEN** later inspection shows that the job remains registered until it is canceled or the gateway stops

#### Scenario: Gateway restart drops pending wakeups
- **WHEN** the live gateway stops or restarts while one or more wakeup jobs are still scheduled
- **THEN** those pending wakeup jobs are lost
- **AND THEN** the restarted gateway does not recover them from gateway persistence artifacts

#### Scenario: Canceling a repeating wakeup stops future occurrences
- **WHEN** a caller deletes a repeating wakeup job that is still registered
- **THEN** the live gateway cancels that wakeup job explicitly
- **AND THEN** no later repeating occurrences are scheduled for that deleted job

### Requirement: Due wakeups remain gateway-owned low-priority internal prompt delivery
When a wakeup becomes due, the gateway SHALL treat delivery of that wakeup prompt as gateway-owned internal execution behavior rather than as a new externally visible public request kind.

The public terminal-mutating request-kind set SHALL remain limited to `submit_prompt` and `interrupt`.

Before a due wakeup prompt starts execution, the gateway SHALL require:

- request admission to be open,
- no active terminal-mutating execution,
- zero durable public queue depth.

If those conditions are not satisfied when a wakeup becomes due, the gateway SHALL keep that wakeup pending in memory and SHALL retry later instead of dropping the reminder or converting it into durable queued work.

Repeating wakeups SHALL maintain at most one pending due occurrence per job. Missed intervals during a busy period SHALL NOT produce a catch-up burst of multiple immediate prompt deliveries once the gateway becomes idle again.

#### Scenario: Busy gateway defers a due wakeup
- **WHEN** a wakeup becomes due while request admission is blocked, active execution is running, or durable public queue depth is non-zero
- **THEN** the gateway does not start that wakeup prompt immediately
- **AND THEN** the wakeup remains pending in memory until a later safe execution opportunity

#### Scenario: Due wakeup does not expand the public request-kind set
- **WHEN** a wakeup prompt is delivered after becoming due
- **THEN** that delivery happens through gateway-owned internal behavior rather than a new public `POST /v1/requests` kind
- **AND THEN** the public terminal-mutating request kinds remain exactly `submit_prompt` and `interrupt`

#### Scenario: Repeating wakeup does not backfill missed intervals as a burst
- **WHEN** a repeating wakeup remains overdue across multiple interval boundaries because the gateway is busy
- **THEN** the gateway preserves at most one pending overdue occurrence for that repeating job
- **AND THEN** the gateway does not emit one immediate prompt for every missed interval once the gateway becomes idle

## MODIFIED Requirements

### Requirement: The gateway exposes a structured HTTP API on the resolved listener address
The gateway SHALL expose an HTTP API for health inspection, status inspection, gateway-managed request submission, wakeup registration and inspection, gateway-owned notifier control, and, when permitted by mailbox bindings and listener policy, shared mailbox operations on the resolved listener address for that session.

The base gateway HTTP API SHALL expose `GET /health`, `GET /v1/status`, and `POST /v1/requests`.

The wakeup HTTP API SHALL additionally expose `POST /v1/wakeups`, `GET /v1/wakeups`, `GET /v1/wakeups/{job_id}`, and `DELETE /v1/wakeups/{job_id}`.

For mailbox-enabled sessions whose live gateway listener is bound to loopback, that HTTP API SHALL additionally expose `GET /v1/mail/status`, `POST /v1/mail/check`, `POST /v1/mail/send`, `POST /v1/mail/reply`, and `POST /v1/mail/state`.

When the gateway mail notifier capability is implemented, that HTTP API SHALL additionally expose `PUT /v1/mail-notifier`, `GET /v1/mail-notifier`, and `DELETE /v1/mail-notifier`.

`GET /health` SHALL return a structured response suitable for runtime launch-readiness checks and SHALL include gateway protocol-version information.

`GET /health` SHALL reflect gateway-local process and control-plane health, and SHALL NOT fail solely because the managed agent is unavailable, recovering, or awaiting rebind.

`GET /v1/status` SHALL return the same versioned status model that the gateway persists to `state.json`.

`POST /v1/requests` SHALL accept typed request-creation payloads and SHALL return the accepted queued request record.

The wakeup routes SHALL be served by the gateway sidecar itself and SHALL use structured request and response payloads rather than requiring callers to mutate gateway memory or private runtime objects directly.

The notifier control endpoints SHALL be served by the gateway sidecar itself and SHALL use structured request and response payloads rather than requiring callers to read or write gateway SQLite state directly.

The shared mailbox routes SHALL be limited to mailbox status, `check`, `send`, `reply`, and explicit single-message read-state update behaviors supported by both the filesystem and `stalwart` transports.

Those shared mailbox routes SHALL use structured request and response payloads and SHALL NOT require callers to read or write transport-local SQLite state, filesystem `rules/`, or Stalwart-native objects directly.

That HTTP API SHALL be served by the gateway sidecar itself and SHALL use structured request and response payloads rather than requiring callers to read or write SQLite state directly.

Request-validation failures on `POST /v1/requests` SHALL return HTTP `422`. Explicit gateway policy rejection SHALL return HTTP `403`. Request-state conflicts such as reconciliation-required admission blocking SHALL return HTTP `409`. Managed-agent unavailable or recovery-blocked admission failures SHALL return HTTP `503`.

Wakeup-route validation failures SHALL return HTTP `422`. Unknown wakeup identifiers on `GET /v1/wakeups/{job_id}` or `DELETE /v1/wakeups/{job_id}` SHALL return HTTP `404`.

Notifier validation failures SHALL return HTTP `422`. Attempts to enable notifier behavior for sessions that cannot support it SHALL fail explicitly rather than pretending that notifier polling is active.

Shared mailbox route validation failures SHALL return HTTP `422`. Calls to mailbox routes for sessions without mailbox bindings SHALL fail explicitly rather than pretending mailbox support exists. When the live gateway listener is bound to `0.0.0.0`, the `/v1/mail/*` routes SHALL fail explicitly as unavailable until an authentication model exists for broader listeners.

Read-oriented HTTP endpoints and mailbox read routes SHALL NOT consume the terminal-mutation slot solely to report current gateway health, core status, wakeup state, notifier status, or shared mailbox state.

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

#### Scenario: Wakeup registration uses the live gateway HTTP surface
- **WHEN** a caller needs to register or inspect one live wakeup job for an attached gateway-managed session
- **THEN** the caller uses the dedicated `/v1/wakeups` route family on that live gateway listener
- **AND THEN** the caller does not need to mutate private runtime state or transport queue artifacts directly

#### Scenario: Unknown wakeup identifier fails explicitly
- **WHEN** a caller requests `GET /v1/wakeups/{job_id}` or `DELETE /v1/wakeups/{job_id}` for a non-existent wakeup job
- **THEN** the gateway rejects that call explicitly
- **AND THEN** it does not pretend that the requested wakeup still exists

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

#### Scenario: Invalid request payload is rejected with validation semantics
- **WHEN** a caller submits a malformed `POST /v1/requests` payload
- **THEN** the gateway returns HTTP `422`
- **AND THEN** the malformed request is not accepted into durable queue state

#### Scenario: Notifier control surface is available alongside the base gateway API
- **WHEN** a caller needs to enable, inspect, or disable gateway mail notification for a mailbox-enabled session
- **THEN** the gateway exposes the dedicated `/v1/mail-notifier` control routes on the same resolved listener
- **AND THEN** callers do not need to mutate gateway queue persistence directly to manage notifier behavior

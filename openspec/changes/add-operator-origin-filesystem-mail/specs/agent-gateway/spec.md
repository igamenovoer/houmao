## MODIFIED Requirements

### Requirement: The gateway exposes a structured HTTP API on the resolved listener address
The gateway SHALL expose an HTTP API for health inspection, status inspection, gateway-managed request submission, wakeup registration and inspection, gateway-owned notifier control, and, when permitted by mailbox bindings and listener policy, shared mailbox operations on the resolved listener address for that session.

The base gateway HTTP API SHALL expose `GET /health`, `GET /v1/status`, and `POST /v1/requests`.

The wakeup HTTP API SHALL additionally expose `POST /v1/wakeups`, `GET /v1/wakeups`, `GET /v1/wakeups/{job_id}`, and `DELETE /v1/wakeups/{job_id}`.

For mailbox-enabled sessions whose live gateway listener is bound to loopback, that HTTP API SHALL additionally expose `GET /v1/mail/status`, `POST /v1/mail/check`, `POST /v1/mail/send`, `POST /v1/mail/post`, `POST /v1/mail/reply`, and `POST /v1/mail/state`.

When the gateway mail notifier capability is implemented, that HTTP API SHALL additionally expose `PUT /v1/mail-notifier`, `GET /v1/mail-notifier`, and `DELETE /v1/mail-notifier`.

`GET /health` SHALL return a structured response suitable for runtime launch-readiness checks and SHALL include gateway protocol-version information.

`GET /health` SHALL reflect gateway-local process and control-plane health, and SHALL NOT fail solely because the managed agent is unavailable, recovering, or awaiting rebind.

`GET /v1/status` SHALL return the same versioned status model that the gateway persists to `state.json`.

`POST /v1/requests` SHALL accept typed request-creation payloads and SHALL return the accepted queued request record.

The wakeup routes SHALL be served by the gateway sidecar itself and SHALL use structured request and response payloads rather than requiring callers to mutate gateway memory or private runtime objects directly.

The notifier control endpoints SHALL be served by the gateway sidecar itself and SHALL use structured request and response payloads rather than requiring callers to read or write gateway SQLite state directly.

The shared mailbox routes SHALL be limited to mailbox status, `check`, ordinary `send`, operator-origin `post`, `reply`, and explicit single-message read-state update behavior.

Ordinary `send`, `reply`, and read-state update behavior SHALL continue using the shared mailbox abstraction across both the filesystem and `stalwart` transports. Operator-origin `post` SHALL support only filesystem mailbox bindings in v1 and SHALL fail explicitly for other transports.

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

#### Scenario: Filesystem-backed mailbox post uses the dedicated gateway mail surface
- **WHEN** a caller performs operator-origin mailbox delivery against a mailbox-enabled session whose resolved mailbox transport is `filesystem`
- **THEN** the live gateway serves that operation through `POST /v1/mail/post`
- **AND THEN** the resulting delivery uses the reserved Houmao operator mailbox sender rather than the managed agent sender principal

#### Scenario: Stalwart-backed mailbox reply uses the same dedicated gateway mail surface
- **WHEN** a caller performs mailbox `reply` against a mailbox-enabled session whose resolved mailbox transport is `stalwart`
- **THEN** the live gateway serves that operation through `POST /v1/mail/reply`
- **AND THEN** the caller uses the same shared gateway mailbox contract rather than Stalwart-native transport objects directly

#### Scenario: Stalwart-backed mailbox post fails explicitly
- **WHEN** a caller performs operator-origin mailbox delivery against a mailbox-enabled session whose resolved mailbox transport is `stalwart`
- **THEN** the live gateway rejects that operation explicitly
- **AND THEN** it does not pretend that filesystem operator-origin semantics are available for the current transport

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


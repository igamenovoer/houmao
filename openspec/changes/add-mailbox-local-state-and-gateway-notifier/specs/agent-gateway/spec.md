## ADDED Requirements

### Requirement: Gateway writes a tail-friendly running log to disk
The gateway SHALL maintain a running log on disk under its gateway-owned root so operators can monitor live behavior by tailing one stable file.

That running log SHALL live under the gateway log directory and SHALL be append-only and line-oriented so common file-tail tools can follow it while the gateway is active.

The running log SHALL cover at minimum:

- gateway process start and stop,
- attach and detach outcomes,
- notifier enable, disable, and configuration changes when notifier is supported,
- notifier poll outcomes such as unread detected, busy deferral, and enqueue success when notifier is supported,
- request execution start and terminal outcome,
- explicit gateway-side errors that affect live behavior.

The running log SHALL remain a human-oriented observability surface. Structured artifacts such as `state.json`, `events.jsonl`, and gateway SQLite state remain the authoritative machine-readable contracts for status, history, and recovery.

The gateway SHALL avoid unbounded log spam from high-frequency identical poll outcomes by rate-limiting, coalescing, or periodically summarizing repetitive messages.

#### Scenario: Operator can tail one stable gateway log file
- **WHEN** an operator wants to watch live gateway behavior for one session
- **THEN** the gateway writes append-only log lines to one stable file under the gateway root
- **AND THEN** the operator can follow that file with ordinary tail-style tooling while the gateway is active

#### Scenario: Busy notifier retries are visible without flooding the log
- **WHEN** unread mail exists but the notifier keeps finding the managed agent busy across multiple polling cycles
- **THEN** the gateway running log records that notifier work is being deferred for retry
- **AND THEN** the gateway avoids emitting an unbounded identical busy message on every single short poll forever

## MODIFIED Requirements

### Requirement: The gateway exposes a structured HTTP API on the resolved listener address
The gateway SHALL expose an HTTP API for health inspection, status inspection, gateway-managed request submission, and gateway-owned notifier control on the resolved listener address for that session.

The base gateway HTTP API SHALL expose `GET /health`, `GET /v1/status`, and `POST /v1/requests`.

When the gateway mail notifier capability is implemented, that HTTP API SHALL additionally expose `PUT /v1/mail-notifier`, `GET /v1/mail-notifier`, and `DELETE /v1/mail-notifier`.

`GET /health` SHALL return a structured response suitable for runtime launch-readiness checks and SHALL include gateway protocol-version information.

`GET /health` SHALL reflect gateway-local process and control-plane health, and SHALL NOT fail solely because the managed agent is unavailable, recovering, or awaiting rebind.

`GET /v1/status` SHALL return the same versioned status model that the gateway persists to `state.json`.

`POST /v1/requests` SHALL accept typed request-creation payloads and SHALL return the accepted queued request record.

The notifier control endpoints SHALL be served by the gateway sidecar itself and SHALL use structured request and response payloads rather than requiring callers to read or write gateway SQLite state directly.

That HTTP API SHALL be served by the gateway sidecar itself and SHALL use structured request and response payloads rather than requiring callers to read or write SQLite state directly.

Request-validation failures on `POST /v1/requests` SHALL return HTTP `422`. Explicit gateway policy rejection SHALL return HTTP `403`. Request-state conflicts such as reconciliation-required admission blocking SHALL return HTTP `409`. Managed-agent unavailable or recovery-blocked admission failures SHALL return HTTP `503`.

Notifier validation failures SHALL return HTTP `422`. Attempts to enable notifier behavior for sessions that cannot support it SHALL fail explicitly rather than pretending that notifier polling is active.

Read-oriented HTTP endpoints SHALL NOT consume the terminal-mutation slot solely to report current gateway health, core status, or notifier status.

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

#### Scenario: Invalid request payload is rejected with validation semantics
- **WHEN** a caller submits a malformed `POST /v1/requests` payload
- **THEN** the gateway returns HTTP `422`
- **AND THEN** the malformed request is not accepted into durable queue state

#### Scenario: Notifier control surface is available alongside the base gateway API
- **WHEN** a caller needs to enable, inspect, or disable gateway mail notification for a mailbox-enabled session
- **THEN** the gateway exposes the dedicated `/v1/mail-notifier` control routes on the same resolved listener
- **AND THEN** callers do not need to mutate gateway queue persistence directly to manage notifier behavior

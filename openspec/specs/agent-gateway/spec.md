# agent-gateway Specification

## Purpose
Define the durable per-agent gateway companion, including its storage layout, HTTP surface, execution policy, and recovery behavior.

## Requirements

### Requirement: Per-agent gateway companion introduces no visible operator surface and may attach after session start
The system SHALL support a per-agent gateway companion for gateway-capable tmux-backed sessions.

The gateway companion SHALL NOT require or create a separate visible tmux window or pane for normal operation.

The gateway companion MAY be started immediately after a managed session starts or later by attaching to an already-running tmux-backed session.

The gateway companion SHALL direct its own logs away from the visible operator terminal.

#### Scenario: Attach-later preserves a single visible TUI surface
- **WHEN** a gateway companion attaches to an already-running tmux-backed session
- **THEN** the managed agent TUI remains the only visible operator surface for normal interaction
- **AND THEN** the attach flow does not require creating a visible tmux pane or window for the gateway

#### Scenario: Gateway logging does not paint onto the shared terminal
- **WHEN** the gateway companion emits logs or diagnostics during normal operation
- **THEN** that output is written to gateway-owned log storage rather than the visible tmux terminal
- **AND THEN** normal gateway activity does not inject its own text into the operator-facing TUI surface

### Requirement: The gateway maintains a durable per-agent control root
Each gateway-capable session SHALL have a deterministic per-agent gateway root under the runtime-owned storage hierarchy once attachability is published or a gateway first attaches.

For runtime-owned sessions in v1, the canonical runtime-owned session root SHALL be `<runtime_root>/sessions/<backend>/<session_id>/`, using the runtime-generated session id used for session-manifest storage, and the gateway root SHALL be the nested `gateway/` subdirectory under that session root.

That gateway root SHALL contain at minimum:

- a protocol-version marker
- a read-optimized current state artifact
- a durable queued-request store
- an append-only event log

The gateway SHALL recover pending work and the latest persisted status from that gateway root when the gateway companion process restarts and the managed session still exists.

The current gateway state artifact SHALL be a stable, protocol-versioned local read contract, SHALL use the same schema as `GET /v1/status`, and SHALL be written atomically.

For gateway-capable sessions with no currently running gateway instance, the current gateway state artifact SHALL still exist and SHALL represent an offline or not-attached gateway condition rather than disappearing.

The gateway root SHALL distinguish stable attachability metadata from live gateway-instance metadata.

#### Scenario: Gateway restart recovers queued work from durable state
- **WHEN** the gateway companion process exits unexpectedly while its managed tmux session remains available
- **AND WHEN** durable queued requests exist in the gateway root
- **THEN** a restarted gateway companion recovers those queued requests from durable storage
- **AND THEN** the gateway does not require callers to resubmit already accepted pending work solely because the sidecar process restarted

#### Scenario: External readers can inspect the latest gateway state without replaying the event log
- **WHEN** an operator or local tool needs the latest gateway status for a managed session
- **THEN** the system provides that status through the current gateway state artifact in the gateway root
- **AND THEN** the caller does not need to reconstruct current state solely by replaying the append-only event log

#### Scenario: First attach creates gateway-owned durable state for a running session
- **WHEN** a gateway companion first attaches to a running tmux-backed session that previously had no gateway process
- **THEN** the system creates or materializes the gateway root for that session
- **AND THEN** the initial gateway state is seeded from current observation plus attach metadata rather than requiring pre-attach event history

#### Scenario: Gateway-capable session exposes offline state before first attach
- **WHEN** a runtime-owned tmux-backed session has published gateway capability but no gateway instance has ever attached yet
- **THEN** the gateway root already contains the current gateway state artifact for that session
- **AND THEN** that state artifact reports an offline or not-attached gateway condition

#### Scenario: Runtime-owned gateway root is nested under the session root
- **WHEN** the runtime provisions gateway capability for runtime-owned session `cao_rest-20260312-120000Z-abcd1234`
- **THEN** the runtime-owned session root for that session is `<runtime_root>/sessions/<backend>/<session_id>/`
- **AND THEN** the gateway root for that session is `<session-root>/gateway`
- **AND THEN** gateway-owned durable state stays colocated with the agent session rather than in a separate top-level gateway tree

### Requirement: Stable attachability metadata is distinct from live gateway bindings
The system SHALL publish stable attachability metadata for gateway-capable sessions independently from whether a gateway process is currently running.

Stable attachability metadata SHALL be sufficient for a later attach flow to determine how to attach to the live session.

Live gateway bindings such as active host, port, and state-path pointers SHALL describe only the currently running gateway instance and SHALL be treated as ephemeral.

#### Scenario: Gateway-capable session exists with no running gateway
- **WHEN** a tmux-backed session has published attach metadata but no gateway companion is currently running
- **THEN** the session remains gateway-capable
- **AND THEN** callers can distinguish that state from one where a live gateway instance is currently attached

#### Scenario: Live gateway bindings are cleared on graceful stop
- **WHEN** an attached gateway companion stops gracefully while the managed tmux session remains live
- **THEN** the system preserves stable attachability metadata for later re-attach
- **AND THEN** live gateway host or port bindings are removed or invalidated for that stopped instance

### Requirement: Each running gateway instance binds one resolved host and port
Each running gateway instance SHALL expose its gateway submit or status surface as an HTTP service bound on exactly one resolved listener address before that gateway instance starts accepting work.

Allowed listener hosts in this change are exactly `127.0.0.1` and `0.0.0.0`.

When no explicit all-interface bind host is configured, the gateway companion SHALL default to binding on `127.0.0.1:<resolved-port>`.

The gateway companion SHALL attempt to bind that resolved port during startup and SHALL NOT silently switch to a different port if binding fails.

When no explicit gateway port is configured, the system SHALL request a system-assigned port during gateway bind and SHALL NOT pre-probe a free port in the parent runtime process.

When the resolved port is unavailable because another process already owns it or because the bind otherwise fails, startup of that gateway instance SHALL fail explicitly.

When a gateway instance starts successfully with a system-assigned port, the system SHALL persist that resolved host and port as the desired listener for that gateway root and SHALL reuse them on later restarts unless explicitly overridden.

#### Scenario: Gateway starts on the default loopback listener
- **WHEN** the system starts a gateway companion for a gateway-capable tmux-backed session with resolved gateway port `43123`
- **AND WHEN** no explicit all-interface bind host is configured
- **THEN** the gateway companion binds an HTTP service on `127.0.0.1:43123`
- **AND THEN** live gateway discovery for that instance reflects port `43123` rather than an unrelated substituted port

#### Scenario: Explicit all-interface bind uses 0.0.0.0
- **WHEN** the system starts a gateway companion with resolved gateway host `0.0.0.0` and port `43123`
- **THEN** the gateway companion binds an HTTP service on `0.0.0.0:43123`
- **AND THEN** the service is reachable through any host interface address that maps to that port

#### Scenario: Port conflict fails gateway attach or start
- **WHEN** the system attempts to start a gateway companion whose resolved gateway port is already bound by another process
- **THEN** the system fails that gateway start or attach operation with an explicit gateway-port conflict error
- **AND THEN** it does not silently retry on a different port for that launch attempt

#### Scenario: Successful system-assigned listener is reused on restart
- **WHEN** a gateway companion first starts successfully with a system-assigned port
- **THEN** the system records that resolved host and port as the desired listener for the gateway root
- **AND THEN** a later restart of that same gateway root reuses that listener unless a caller explicitly overrides it

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

### Requirement: Gateway status separates gateway health, upstream-agent state, recovery, admission, surface eligibility, and execution state
The gateway SHALL publish a structured status model that separates gateway health from managed-agent connectivity, recovery state, request-admission state, and terminal-surface readiness.

That published status model SHALL be protocol-versioned and SHALL be shared by both `state.json` and `GET /v1/status`.

At minimum, the published gateway status SHALL distinguish:

- protocol version
- stable session identity
- current managed-agent instance epoch
- gateway health state
- managed-agent connectivity state
- managed-agent recovery state
- request-admission state
- terminal-surface eligibility state
- active execution state
- gateway host
- gateway port
- queue depth

When the gateway cannot safely classify the managed terminal surface, it SHALL publish an explicit unknown-like state rather than inferring readiness.

`gateway health state` SHALL support representing that no gateway instance is currently attached to an otherwise gateway-capable session.

`request-admission state` SHALL support representing that the gateway remains alive while terminal-mutating work is paused or rejected because the managed agent is recovering, unavailable, or requires reconciliation after rebinding.

#### Scenario: Managed-agent crash changes upstream status without corrupting gateway health
- **WHEN** the gateway companion remains alive but the managed agent crashes unexpectedly
- **THEN** the published status keeps gateway health separate from the managed-agent connectivity and recovery states
- **AND THEN** the gateway does not claim that the whole control plane is dead solely because the upstream agent failed

#### Scenario: Replacement upstream instance increments the managed-agent epoch
- **WHEN** bounded recovery rebinds the logical session to a replacement managed-agent instance
- **THEN** the published status reflects a new managed-agent instance epoch for that same stable session identity
- **AND THEN** clients can distinguish "same session, new upstream instance" from "same session, same upstream instance"

#### Scenario: Manual modal interaction changes surface eligibility without corrupting gateway health
- **WHEN** a human operator opens or leaves the managed TUI in a non-submit-ready modal surface
- **THEN** the gateway updates the published terminal-surface eligibility state to reflect that non-ready surface
- **AND THEN** the gateway does not mark itself unhealthy solely because the operator changed the TUI surface

#### Scenario: Uncertain surface classification stays explicit
- **WHEN** the gateway cannot safely determine whether the managed terminal surface is ready for injection
- **THEN** the gateway publishes an explicit non-ready or unknown-like surface state
- **AND THEN** it does not silently treat the surface as submit-ready

### Requirement: The gateway serializes terminal-mutating work and applies admission policy
The gateway SHALL accept structured local requests for gateway-managed work and SHALL apply gateway-owned admission policy before execution.

In v1, the public terminal-mutating request kinds SHALL be exactly `submit_prompt` and `interrupt`.

The HTTP submission contract SHALL expose typed per-kind payloads. Any persisted `payload_json` field remains an internal storage detail rather than part of the public protocol contract.

For accepted terminal-mutating requests, the gateway SHALL persist them durably, SHALL serialize execution through a single active terminal-mutation slot per managed agent, and SHALL order eligible work according to gateway policy such as priority, timing constraints, or coalescing rules.

The gateway SHALL be able to reject requests explicitly when permissions or local policy do not allow them.

The gateway SHALL determine terminal-mutating request admission using the published request-admission state rather than only gateway-process liveness.

Already accepted but not-yet-started terminal-mutating work SHALL remain durable while bounded managed-agent recovery is in progress.

If the managed agent fails while a terminal-mutating request is active, the gateway SHALL record an explicit failed or outcome-unknown result for that request and SHALL NOT silently replay it against a replacement managed-agent instance unless the backend adapter has positively established safe continuity.

When managed-agent recovery or reconciliation state makes safe execution impossible, the gateway SHALL reject new terminal-mutating admission explicitly rather than accepting work that it cannot safely apply.

#### Scenario: Prompt submission is accepted as a typed request
- **WHEN** a caller submits a `submit_prompt` request with a prompt-string payload
- **THEN** the gateway validates and durably enqueues that request
- **AND THEN** the accepted response includes a durable request identifier

#### Scenario: Interrupt submission is accepted as a typed request
- **WHEN** a caller submits an `interrupt` request for a gateway-managed session
- **THEN** the gateway records it as a gateway-managed control action
- **AND THEN** the caller does not need to bypass the gateway with direct concurrent terminal mutation

#### Scenario: Concurrent terminal-mutating requests are serialized
- **WHEN** multiple accepted terminal-mutating requests target the same managed agent concurrently
- **THEN** the gateway allows at most one of those requests to hold the active execution slot at a time
- **AND THEN** later eligible requests remain queued until the active terminal-mutation slot is released

#### Scenario: Disallowed request is rejected before execution
- **WHEN** a submitted gateway request violates configured permission or policy rules
- **THEN** the gateway rejects that request explicitly
- **AND THEN** the rejected request is not executed against the managed terminal surface

#### Scenario: Accepted queued work survives transient upstream outage
- **WHEN** terminal-mutating work has already been accepted durably and the managed agent becomes unavailable before that work begins
- **THEN** the gateway preserves that queued work durably
- **AND THEN** execution remains paused until recovery or reconciliation reopens safe admission

#### Scenario: Active prompt is not replayed blindly after upstream replacement
- **WHEN** a `submit_prompt` request is active and the managed agent fails unexpectedly before the gateway can confirm a terminal outcome
- **AND WHEN** bounded recovery later rebinds the logical session to a replacement managed-agent instance
- **THEN** the gateway records the interrupted request as failed or outcome-unknown
- **AND THEN** the gateway does not silently replay that same prompt against the replacement upstream instance

#### Scenario: New prompt admission is rejected while recovery blocks safe execution
- **WHEN** a caller submits a new `submit_prompt` request while the gateway's request-admission state is paused or closed because the managed agent is unavailable, recovering, or awaiting reconciliation
- **THEN** the gateway rejects that request with explicit unavailable or conflict semantics
- **AND THEN** the gateway does not pretend that queued execution can proceed safely

### Requirement: Gateway-managed operation does not depend on mailbox enablement
The gateway SHALL NOT require mailbox transport configuration, mailbox environment bindings, or mailbox-triggered workflows in order to launch, publish status, accept gateway-managed work, or recover a gateway-managed session.

Future mailbox integration MAY submit work through the same validated gateway request surface in a follow-up change, but this change SHALL NOT make mailbox participation a hidden dependency of gateway operation.

#### Scenario: Gateway-managed session operates without mailbox support
- **WHEN** the system starts or attaches a gateway companion for a tmux-backed session that does not enable any mailbox transport
- **THEN** the gateway companion still launches, publishes gateway state, and accepts gateway-managed work
- **AND THEN** gateway operation does not fail solely because mailbox support is absent

#### Scenario: Missing mailbox bindings do not block gateway recovery
- **WHEN** a gateway-managed session is resumed or recovered without mailbox-specific environment bindings
- **THEN** gateway discovery, status inspection, and recovery continue to rely on gateway-owned state and runtime metadata
- **AND THEN** the system does not require mailbox bindings to continue gateway-managed operation

### Requirement: Direct human TUI interaction is a supported concurrent activity
The gateway SHALL treat direct human interaction with the managed TUI as a supported concurrent activity rather than as protocol corruption.

When human interaction leaves the managed surface in a state that is not safely eligible for gateway injection, the gateway SHALL pause or defer queued terminal-mutating work until eligibility returns.

Direct human interaction SHALL NOT, by itself, invalidate already accepted queued work.

#### Scenario: Human interaction pauses queued injection without discarding queued work
- **WHEN** queued terminal-mutating work exists for a gateway-managed agent
- **AND WHEN** a human operator changes the managed TUI into a non-submit-ready surface before the queued work begins
- **THEN** the gateway defers injection until the surface is safely eligible again
- **AND THEN** the gateway retains the accepted queued work instead of discarding it solely because the human interacted with the TUI

#### Scenario: Human interaction during active work is recorded and reconciled
- **WHEN** a human operator changes the managed TUI while a gateway-owned request is in progress
- **THEN** the gateway records that observation in its state or event history
- **AND THEN** the gateway reevaluates the active request outcome according to its recovery or retry policy instead of assuming the session is irreparably corrupted

### Requirement: The gateway supports timers, heartbeats, bounded local recovery, replacement-instance awareness, and snapshot-based later attach
The gateway SHALL support regular gateway heartbeats, managed-agent liveness observation, timer-driven request creation, and bounded recovery for agent-local failures.

Timer-driven or wakeup-oriented queued work in v1 SHALL remain gateway-owned internal behavior rather than additional externally submitted public request kinds.

When a gateway first attaches to an already-running session, the gateway SHALL initialize from current observation plus attach metadata rather than requiring continuous launch-time observation.

When the managed agent fails or becomes unavailable while the gateway companion remains alive, the gateway SHALL attempt bounded recovery through the runtime-owned backend integration for that session and SHALL record the recovery outcome.

Bounded recovery SHALL distinguish at least:

- reconnecting to the same managed-agent instance
- rebinding the logical session to a replacement managed-agent instance
- exhausting recovery while keeping the gateway alive for inspection and later rebind

When bounded recovery rebinds the logical session to a replacement managed-agent instance, the gateway SHALL preserve the stable session identity, SHALL record a new managed-agent instance epoch, and SHALL require reconciliation before replaying unsafe terminal-mutating work unless the backend adapter can positively establish safe continuity.

If bounded recovery exhausts without restoring safe continuity, the gateway SHALL remain available for `GET /health`, `GET /v1/status`, and local state inspection while publishing a non-open request-admission state.

When the entire tmux session or tmux server hosting the managed agent disappears, the gateway SHALL surface that loss as an offline or degraded condition and SHALL NOT claim full self-recovery of the destroyed tmux container from within the gateway companion itself.

#### Scenario: Agent-local failure triggers bounded gateway recovery
- **WHEN** the gateway remains alive but observes that the managed agent process or terminal surface has failed in a recoverable way
- **THEN** the gateway attempts bounded recovery using the configured backend integration for that managed session
- **AND THEN** the gateway records whether recovery succeeded, retried, or exhausted its retry budget

#### Scenario: Same-instance recovery reopens paused admission
- **WHEN** the gateway pauses admission because the managed agent became temporarily unavailable
- **AND WHEN** bounded recovery reconnects to the same managed-agent instance with safe continuity
- **THEN** the gateway may reopen request admission for that same stable session without changing the managed-agent instance epoch
- **AND THEN** previously paused queued work can resume according to normal scheduling rules

#### Scenario: Replacement-instance recovery requires reconciliation
- **WHEN** bounded recovery succeeds only by rebinding the logical session to a replacement managed-agent instance
- **THEN** the gateway preserves the stable session identity but records a new managed-agent instance epoch
- **AND THEN** the gateway surfaces a reconciliation-required admission state before unsafe automation resumes

#### Scenario: Exhausted recovery keeps the gateway available for inspection
- **WHEN** the gateway exhausts its bounded recovery attempts for a logical session while the gateway process itself remains alive
- **THEN** `GET /health`, `GET /v1/status`, and `state.json` remain available for inspection
- **AND THEN** the gateway publishes an unavailable or awaiting-rebind admission state instead of pretending the whole gateway died

#### Scenario: Whole tmux-session loss is surfaced for outer supervision
- **WHEN** the tmux session hosting the managed TUI is destroyed while a gateway instance had been attached
- **THEN** the gateway contract surfaces that loss as an offline or degraded condition when state is next inspected
- **AND THEN** recovery of the destroyed tmux container is left to an outer launcher or supervisor layer rather than being claimed by the gateway companion alone

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

### Requirement: Gateway notifier wake-up semantics are unread-set based rather than per-message based
When gateway-owned notifier behavior is enabled for a mailbox-backed session, the gateway SHALL treat notification eligibility as a function of whether unread mail exists for that session and whether the session is eligible to receive a reminder prompt.

If a poll cycle finds multiple unread messages, the gateway MAY enqueue a single internal reminder prompt that summarizes the unread set for that cycle, including message metadata such as titles or identifiers.

The gateway SHALL NOT require one internal reminder prompt per unread message in order to satisfy notifier behavior.

If the unread set has not changed since the last successful reminder and the messages remain unread, the gateway MAY skip emitting a duplicate reminder until the unread set changes or the messages are marked read explicitly.

#### Scenario: Multiple unread messages can be summarized in one reminder prompt
- **WHEN** one notifier poll cycle observes more than one unread message for the same mailbox-backed session
- **THEN** the gateway may enqueue one internal reminder prompt that summarizes the unread set observed in that cycle
- **AND THEN** the gateway does not need to enqueue one reminder per unread message

#### Scenario: Unchanged unread set does not force duplicate reminders
- **WHEN** the notifier previously delivered or enqueued a reminder for one unread set
- **AND WHEN** a later poll finds the same unread set still present and still unread
- **THEN** the gateway may treat that later poll as a duplicate and skip enqueueing a second reminder for the unchanged unread set

### Requirement: Gateway notifier records structured per-poll decision auditing for later review
When gateway-owned notifier behavior is enabled, the gateway SHALL record one structured notifier-decision audit record for each enabled poll cycle in a queryable SQLite audit table under the gateway state root.

Each record SHALL capture enough detail to explain what the notifier saw and why it enqueued or skipped work, including at minimum:

- poll time,
- unread-count observation,
- unread-set identity or equivalent deduplication summary,
- request-admission state,
- active-execution state,
- queue depth,
- the notifier decision outcome, and
- enqueue identifiers or skip detail when applicable.

The gateway MAY continue to keep `gateway.log` rate-limited and human-oriented, but that human log SHALL NOT be the only durable source of per-poll notifier decision history.

Detailed per-poll decision history SHALL remain available through that durable audit table even if `GET /v1/mail-notifier` remains a compact status snapshot without last-decision summary fields.

#### Scenario: Busy poll records an explicit skip decision
- **WHEN** a notifier poll cycle finds unread mail while gateway admission is not open, active execution is running, or queue depth is non-zero
- **THEN** the gateway records a structured audit record for that poll cycle
- **AND THEN** that record identifies the decision as a busy or ineligible skip and includes the eligibility inputs that caused the skip

#### Scenario: Enqueue poll records the created reminder request
- **WHEN** a notifier poll cycle finds unread mail and the gateway enqueues an internal reminder prompt
- **THEN** the gateway records a structured audit record for that poll cycle
- **AND THEN** that record includes the reminder decision outcome and the created internal request identifier

#### Scenario: Durable audit history remains the detailed inspection surface
- **WHEN** an operator or demo helper needs the latest detailed notifier decision data
- **THEN** it can inspect the durable SQLite notifier audit history under the gateway root
- **AND THEN** the gateway does not need to expose additional last-decision summary fields on `GET /v1/mail-notifier` in order to satisfy this requirement

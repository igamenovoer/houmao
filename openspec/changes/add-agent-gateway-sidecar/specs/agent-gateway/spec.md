## ADDED Requirements

### Requirement: Per-agent gateway sidecar shares the managed tmux window without adding a visible operator surface
The system SHALL support a per-agent gateway sidecar for gateway-managed tmux-backed sessions.

The gateway sidecar SHALL run as a background process in the same tmux window and terminal lifecycle as the managed agent TUI.

The gateway sidecar SHALL NOT require or create a separate visible tmux window or pane for normal operation.

The gateway sidecar SHALL NOT read interactive stdin from the shared terminal surface and SHALL direct its own logs away from the visible operator terminal.

#### Scenario: Gateway-managed session starts with one visible TUI surface
- **WHEN** the runtime starts a gateway-managed tmux-backed session
- **THEN** the managed agent TUI remains the only visible operator surface in that tmux window
- **AND THEN** the gateway sidecar is running in the background within the same tmux window lifecycle

#### Scenario: Gateway logging does not paint onto the shared terminal
- **WHEN** the gateway sidecar emits logs or diagnostics during normal operation
- **THEN** that output is written to gateway-owned log storage rather than the visible tmux terminal
- **AND THEN** normal gateway activity does not inject its own text into the operator-facing TUI surface

### Requirement: The gateway maintains a durable per-agent control root
Each gateway-managed session SHALL have a deterministic per-agent gateway root under the runtime-owned storage hierarchy.

That gateway root SHALL contain at minimum:

- a protocol-version marker
- a read-optimized current state artifact
- a durable queued-request store
- an append-only event log

The gateway SHALL recover pending work and the latest persisted status from that gateway root when the gateway sidecar process restarts and the managed session still exists.

#### Scenario: Gateway restart recovers queued work from durable state
- **WHEN** the gateway sidecar process exits unexpectedly while its managed tmux session remains available
- **AND WHEN** durable queued requests exist in the gateway root
- **THEN** a restarted gateway sidecar recovers those queued requests from durable storage
- **AND THEN** the gateway does not require callers to resubmit already accepted pending work solely because the sidecar process restarted

#### Scenario: External readers can inspect the latest gateway state without replaying the event log
- **WHEN** an operator or local tool needs the latest gateway status for a managed session
- **THEN** the system provides that status through the current gateway state artifact in the gateway root
- **AND THEN** the caller does not need to reconstruct current state solely by replaying the append-only event log

### Requirement: Gateway status separates health, agent state, surface eligibility, and execution state
The gateway SHALL publish a structured status model that separates gateway health from managed-agent activity and terminal-surface readiness.

At minimum, the published gateway status SHALL distinguish:

- gateway health state
- managed-agent state
- terminal-surface eligibility state
- active execution state
- queue depth

When the gateway cannot safely classify the managed terminal surface, it SHALL publish an explicit unknown-like state rather than inferring readiness.

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

For accepted terminal-mutating requests, the gateway SHALL persist them durably, SHALL serialize execution through a single active terminal-mutation slot per managed agent, and SHALL order eligible work according to gateway policy such as priority, timing constraints, or coalescing rules.

The gateway SHALL be able to reject requests explicitly when permissions or local policy do not allow them.

#### Scenario: Concurrent terminal-mutating requests are serialized
- **WHEN** multiple accepted terminal-mutating requests target the same managed agent concurrently
- **THEN** the gateway allows at most one of those requests to hold the active execution slot at a time
- **AND THEN** later eligible requests remain queued until the active terminal-mutation slot is released

#### Scenario: Disallowed request is rejected before execution
- **WHEN** a submitted gateway request violates configured permission or policy rules
- **THEN** the gateway rejects that request explicitly
- **AND THEN** the rejected request is not executed against the managed terminal surface

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

### Requirement: The gateway supports timers, heartbeats, and bounded local recovery
The gateway SHALL support regular gateway heartbeats, managed-agent liveness observation, timer-driven request creation, and bounded recovery for agent-local failures.

When the managed agent fails or becomes unavailable while the gateway sidecar remains alive, the gateway SHALL attempt bounded recovery through the runtime-owned backend integration for that session and SHALL record the recovery outcome.

When the entire tmux session or tmux server hosting the same-window sidecar disappears, the gateway SHALL surface that loss as an offline or degraded condition and SHALL NOT claim full self-recovery of the destroyed tmux container from within the sidecar itself.

#### Scenario: Agent-local failure triggers bounded gateway recovery
- **WHEN** the gateway remains alive but observes that the managed agent process or terminal surface has failed in a recoverable way
- **THEN** the gateway attempts bounded recovery using the configured backend integration for that managed session
- **AND THEN** the gateway records whether recovery succeeded, retried, or exhausted its retry budget

#### Scenario: Whole tmux-session loss is surfaced for outer supervision
- **WHEN** the tmux session hosting the same-window gateway sidecar and managed TUI is destroyed
- **THEN** the gateway contract surfaces that loss as an offline or degraded condition when state is next inspected
- **AND THEN** recovery of the destroyed tmux container is left to an outer launcher or supervisor layer rather than being claimed by the in-window sidecar alone

## MODIFIED Requirements

### Requirement: Per-agent gateway companion introduces no visible operator surface by default and may attach after session start
The system SHALL support a per-agent gateway companion for gateway-capable tmux-backed sessions.

Outside pair-managed same-session `houmao_server_rest` topology and outside explicit foreground attach mode, the gateway companion SHALL NOT require or create a separate visible tmux window or pane for normal operation.

For pair-managed same-session `houmao_server_rest` sessions and for runtime-owned tmux-backed sessions whose attach flow explicitly requests foreground mode, the gateway companion MAY run in an auxiliary tmux window in the same tmux session so long as that auxiliary window does not redefine the contractual managed-agent surface.

The gateway companion MAY be started immediately after a managed session starts or later by attaching to an already-running tmux-backed session.

The gateway companion SHALL direct its own logs away from the contractual operator-facing agent surface. When foreground mode is active, gateway console output SHALL appear only in the auxiliary gateway window and gateway-owned durable log storage, not on the agent surface in tmux window `0`.

#### Scenario: Attach-later preserves a single visible TUI surface by default
- **WHEN** a gateway companion attaches to an already-running tmux-backed session without explicit foreground mode outside the supported pair-managed same-session `houmao_server_rest` topology
- **THEN** the managed agent TUI remains the only visible operator surface for normal interaction
- **AND THEN** the attach flow does not require creating a visible tmux pane or window for the gateway

#### Scenario: Runtime-owned foreground attach may add an auxiliary window
- **WHEN** a gateway companion attaches to an already-running runtime-owned tmux-backed session with explicit foreground mode enabled
- **THEN** the attach flow creates or reuses an auxiliary tmux window for the gateway companion
- **AND THEN** that auxiliary window does not become the contractual managed-agent surface

#### Scenario: Pair-managed same-session gateway does not redefine the contractual agent surface
- **WHEN** a pair-managed `houmao_server_rest` gateway companion runs in an auxiliary tmux window in the same tmux session
- **THEN** that auxiliary window does not become the contractual managed-agent surface
- **AND THEN** the primary agent surface remains distinct from the gateway window

#### Scenario: Gateway logging does not paint onto the shared terminal
- **WHEN** the gateway companion emits logs or diagnostics during normal operation
- **THEN** that output is written to gateway-owned log storage rather than the contractual operator-facing tmux surface
- **AND THEN** normal gateway activity does not inject its own text into the operator-facing TUI surface

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
- gateway execution mode
- gateway host
- gateway port
- queue depth

When the gateway is running in `tmux_auxiliary_window` mode, the published gateway status SHALL additionally expose the authoritative tmux execution handle for that live gateway surface, including the tmux window index and tmux window identifier. It MAY also expose the tmux pane identifier.

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

#### Scenario: Foreground gateway status exposes the tmux execution handle
- **WHEN** the gateway companion runs in `tmux_auxiliary_window` mode
- **THEN** the published status includes `execution_mode=tmux_auxiliary_window`
- **AND THEN** the published status exposes the authoritative tmux window index and tmux window identifier for that live gateway surface

#### Scenario: Uncertain surface classification stays explicit
- **WHEN** the gateway cannot safely determine whether the managed terminal surface is ready for injection
- **THEN** the gateway publishes an explicit non-ready or unknown-like surface state
- **AND THEN** it does not silently treat the surface as submit-ready

### Requirement: Same-session gateway live state persists an authoritative execution handle
The runtime SHALL persist one authoritative live gateway record under `<session-root>/gateway/run/current-instance.json`.

When the gateway runs in a same-session auxiliary tmux window, that live record SHALL include an explicit execution mode plus the tmux window and pane identifiers for the auxiliary gateway surface, in addition to the listener and managed-agent instance fields needed for live gateway status.

Detach, crash cleanup, and auxiliary-window recreation SHALL resolve the live gateway surface from that runtime-owned record rather than from ad hoc tmux discovery over non-contractual auxiliary windows.

When auxiliary-window recreation replaces the live gateway surface, the runtime SHALL update the authoritative live gateway record before treating the recreated gateway as ready.

When the same-session auxiliary-window mode is active, the recorded tmux window index SHALL NOT be `0`.

#### Scenario: Same-session live gateway record captures the tmux execution handle
- **WHEN** a gateway companion starts in an auxiliary tmux window
- **THEN** the runtime persists one live gateway record under `<session-root>/gateway/run/current-instance.json`
- **AND THEN** that record identifies the same-session execution mode plus the auxiliary tmux window and pane identifiers for the live gateway surface

#### Scenario: Auxiliary-window recreation updates the authoritative live gateway record
- **WHEN** a same-session gateway auxiliary window is replaced during detach, cleanup, or recovery
- **THEN** the runtime updates the authoritative live gateway record to the new tmux window and pane identifiers
- **AND THEN** later detach or cleanup targets the recreated auxiliary gateway surface without rediscovering non-contractual windows heuristically

## ADDED Requirements

### Requirement: Runtime-owned foreground gateway companions may run in an auxiliary tmux window without redefining the agent surface
For runtime-owned tmux-backed managed sessions launched through `houmao-mgr`, the system SHALL allow the gateway companion to run in a separate auxiliary tmux window in the same tmux session when foreground mode is explicitly requested.

When that foreground mode is active, the system SHALL keep tmux window `0` reserved for the managed agent surface and SHALL keep gateway output off that primary agent window.

When that foreground mode is active, the runtime SHALL treat the gateway auxiliary tmux window and pane as the authoritative local execution surface for gateway lifecycle management. It SHALL use tmux-owned pane state for local liveness, SHALL use gateway health responses for readiness, and SHALL target that auxiliary tmux surface for shutdown rather than relying on a detached subprocess handle.

The gateway companion SHALL continue writing its own durable logs to gateway-owned storage even when its console output is visible in an auxiliary tmux window.

#### Scenario: Runtime-owned foreground attach adds an auxiliary window without redefining the agent surface
- **WHEN** a gateway companion attaches later to an already-running runtime-owned tmux-backed session with explicit foreground mode enabled
- **THEN** the attach flow creates or reuses an auxiliary tmux window for the gateway companion
- **AND THEN** tmux window `0` remains the canonical managed agent surface for that session
- **AND THEN** the gateway auxiliary window uses a tmux window index `>=1`

#### Scenario: Runtime-owned foreground gateway logging stays off the primary agent surface
- **WHEN** the gateway companion emits logs or diagnostics while running in an auxiliary tmux window for a runtime-owned session
- **THEN** the gateway output appears only in the auxiliary gateway window and gateway-owned durable log storage
- **AND THEN** normal gateway activity does not inject its own text into the operator-facing agent window `0`

#### Scenario: Runtime-owned foreground gateway lifecycle uses the auxiliary tmux surface
- **WHEN** the gateway companion runs in an auxiliary tmux window for a runtime-owned tmux-backed session
- **THEN** the runtime determines local gateway liveness from the auxiliary tmux pane state for that window
- **AND THEN** the runtime waits for successful gateway health responses before treating the gateway as ready
- **AND THEN** shutdown and crash cleanup target the auxiliary tmux gateway surface rather than a detached subprocess handle

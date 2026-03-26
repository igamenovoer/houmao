## MODIFIED Requirements

### Requirement: Runtime-owned foreground gateway companions may run in an auxiliary tmux window without redefining the agent surface
For runtime-owned tmux-backed managed sessions launched through `houmao-mgr`, the system SHALL allow the gateway companion to run in a separate auxiliary tmux window in the same tmux session when foreground mode is explicitly requested.

When that foreground mode is active, the system SHALL keep tmux window `0` reserved for the managed agent surface and SHALL keep gateway output off that primary agent window.

When that foreground mode is active, the runtime SHALL treat the gateway auxiliary tmux window and pane as the authoritative local execution surface for gateway lifecycle management. It SHALL resolve that surface from the persisted auxiliary pane or window identity through session-wide tmux pane lookup, SHALL use tmux-owned pane state for local liveness, SHALL use gateway health responses for readiness, and SHALL target that auxiliary tmux surface for shutdown rather than relying on a detached subprocess handle.

Same-session foreground gateway liveness SHALL NOT depend on which tmux window is currently active in the session.

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

#### Scenario: Current agent window does not hide the live gateway pane
- **WHEN** tmux window `0` is current for a runtime-owned tmux-backed session
- **AND WHEN** the live gateway companion pane remains in auxiliary window `1`
- **THEN** foreground gateway liveness still resolves that auxiliary pane from the persisted gateway surface identity
- **AND THEN** the runtime does not clear live gateway state solely because the agent window is current

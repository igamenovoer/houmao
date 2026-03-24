## MODIFIED Requirements

### Requirement: Per-agent gateway companion introduces no visible operator surface and may attach after session start
The system SHALL support a per-agent gateway companion for gateway-capable tmux-backed sessions.

For tmux-backed headless sessions and `cao_rest`, the system SHALL allow the gateway companion to run in a separate auxiliary tmux window in the same tmux session for normal operation.

When the gateway companion runs in the same tmux session, the system SHALL keep tmux window `0` reserved for the managed agent surface and SHALL keep gateway output off that primary agent window.

When the gateway companion runs in the same tmux session, the runtime SHALL treat the gateway auxiliary tmux window and pane as the authoritative local execution surface for gateway lifecycle management. It SHALL use tmux-owned pane state for local liveness, SHALL use gateway health responses for readiness, and SHALL target that auxiliary tmux surface for shutdown rather than relying on a detached subprocess handle.

The system SHALL support starting the gateway companion immediately after a managed session starts and also later by attaching to an already-running tmux-backed session.

The gateway companion SHALL continue writing its own durable logs to gateway-owned storage even when its console output is visible in an auxiliary tmux window.

For `houmao_server_rest` and other launcher paths that do not support same-session auxiliary windows, the gateway companion SHALL continue using an out-of-band process topology rather than creating a visible tmux window in the agent session.

#### Scenario: Attach-later adds an auxiliary window without redefining the agent surface
- **WHEN** a gateway companion attaches later to an already-running tmux-backed headless or `cao_rest` session
- **THEN** the attach flow creates or reuses an auxiliary tmux window for the gateway companion
- **AND THEN** tmux window `0` remains the canonical managed agent surface for that session

#### Scenario: Gateway logging stays off the primary agent surface
- **WHEN** the gateway companion emits logs or diagnostics while running in an auxiliary tmux window
- **THEN** the gateway output appears only in the auxiliary process window and gateway-owned durable log storage
- **AND THEN** normal gateway activity does not inject its own text into the operator-facing agent window `0`

#### Scenario: Same-session gateway lifecycle uses the auxiliary tmux surface
- **WHEN** the gateway companion runs in an auxiliary tmux window for a tmux-backed headless or `cao_rest` session
- **THEN** the runtime determines local gateway liveness from the auxiliary tmux pane state for that window
- **AND THEN** the runtime waits for successful gateway health responses before treating the gateway as ready
- **AND THEN** shutdown and crash cleanup target the auxiliary tmux gateway surface rather than a detached subprocess handle

#### Scenario: Detached topology remains valid when same-session windows are unsupported
- **WHEN** a developer attaches a gateway companion for a `houmao_server_rest` session
- **THEN** the gateway companion runs outside the agent's tmux session
- **AND THEN** the attach flow does not require a same-session tmux auxiliary window

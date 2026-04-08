## RENAMED Requirements

### Requirement: Per-agent gateway companion introduces no visible operator surface by default and may attach after session start
FROM: `Per-agent gateway companion introduces no visible operator surface by default and may attach after session start`
TO: `Per-agent gateway companion defaults tmux-backed managed sessions to same-session foreground execution and may attach after session start`

## MODIFIED Requirements

### Requirement: Per-agent gateway companion defaults tmux-backed managed sessions to same-session foreground execution and may attach after session start
The system SHALL support a per-agent gateway companion for gateway-capable tmux-backed sessions.

For tmux-backed managed sessions, managed attach and launch-time auto-attach SHALL default the effective gateway execution mode to same-session foreground auxiliary-window execution unless the operator explicitly requests background mode.

When explicit background mode is requested for a tmux-backed managed session, the gateway companion SHALL use detached execution and SHALL NOT require or create a visible tmux window or pane for normal operation.

When foreground same-session mode is active, the gateway companion MAY run in an auxiliary tmux window in the same tmux session so long as that auxiliary window does not redefine the contractual managed-agent surface.

The gateway companion MAY be started immediately after a managed session starts or later by attaching to an already-running tmux-backed session.

The gateway companion SHALL direct its own logs away from the contractual operator-facing agent surface. When foreground mode is active, gateway console output SHALL appear only in the auxiliary gateway window and gateway-owned durable log storage, not on the agent surface in tmux window `0`.

#### Scenario: Default attach-later uses same-session foreground execution
- **WHEN** a gateway companion attaches to an already-running tmux-backed managed session without an explicit background override
- **THEN** the effective execution mode is same-session foreground auxiliary-window execution
- **AND THEN** the attach flow creates or reuses an auxiliary tmux window for the gateway companion

#### Scenario: Default launch-time auto-attach uses same-session foreground execution
- **WHEN** a tmux-backed managed session starts with launch-time gateway auto-attach enabled
- **AND WHEN** no explicit background override is requested for that launch
- **THEN** the effective gateway execution mode is same-session foreground auxiliary-window execution
- **AND THEN** the live gateway does not reuse tmux window `0`

#### Scenario: Explicit background mode avoids a visible gateway window
- **WHEN** a gateway companion attaches to a tmux-backed managed session with explicit background mode enabled
- **THEN** the effective execution mode is detached background execution
- **AND THEN** the attach flow does not require creating a visible tmux pane or window for the gateway

#### Scenario: Pair-managed same-session gateway does not redefine the contractual agent surface
- **WHEN** a managed gateway companion runs in an auxiliary tmux window in the same tmux session
- **THEN** that auxiliary window does not become the contractual managed-agent surface
- **AND THEN** the primary agent surface remains distinct from the gateway window

#### Scenario: Gateway logging does not paint onto the shared terminal
- **WHEN** the gateway companion emits logs or diagnostics during normal operation
- **THEN** that output is written to gateway-owned log storage rather than the contractual operator-facing tmux surface
- **AND THEN** normal gateway activity does not inject its own text into the operator-facing TUI surface

### Requirement: Pair-managed `houmao_server_rest` gateway companions may run in an auxiliary tmux window without redefining the agent surface
For pair-managed tmux-backed `houmao_server_rest` sessions, the system SHALL default the gateway companion to same-session auxiliary-window execution for normal operation unless explicit background mode is requested.

When explicit background mode is requested for a pair-managed `houmao_server_rest` session, the system SHALL attach or reuse the gateway in detached execution instead of creating or reusing the same-session auxiliary tmux window for that attach.

When the gateway companion runs in the same tmux session, the system SHALL keep tmux window `0` reserved for the managed agent surface and SHALL keep gateway output off that primary agent window.

When the gateway companion runs in the same tmux session, the runtime SHALL treat the gateway auxiliary tmux window and pane as the authoritative local execution surface for gateway lifecycle management. It SHALL use tmux-owned pane state for local liveness, SHALL use gateway health responses for readiness, and SHALL target that auxiliary tmux surface for shutdown rather than relying on a detached subprocess handle.

The gateway companion SHALL continue writing its own durable logs to gateway-owned storage even when its console output is visible in an auxiliary tmux window.

The `houmao-server` process and its internal child-CAO support state SHALL remain outside the agent's tmux session even when the gateway companion runs in the same managed session as the agent.

#### Scenario: Default pair-managed attach adds an auxiliary window without redefining the agent surface
- **WHEN** a gateway companion attaches later to an already-running pair-managed `houmao_server_rest` session without an explicit background override
- **THEN** the attach flow creates or reuses an auxiliary tmux window for the gateway companion
- **AND THEN** tmux window `0` remains the canonical managed agent surface for that session

#### Scenario: Pair-managed explicit background attach skips the auxiliary window
- **WHEN** a gateway companion attaches to a pair-managed `houmao_server_rest` session with explicit background mode enabled
- **THEN** the attach flow uses detached background execution for that attach
- **AND THEN** it does not create or reuse a same-session auxiliary tmux window for the gateway

#### Scenario: Gateway logging stays off the primary agent surface
- **WHEN** the gateway companion emits logs or diagnostics while running in an auxiliary tmux window
- **THEN** the gateway output appears only in the auxiliary process window and gateway-owned durable log storage
- **AND THEN** normal gateway activity does not inject its own text into the operator-facing agent window `0`

#### Scenario: Same-session gateway lifecycle uses the auxiliary tmux surface
- **WHEN** the gateway companion runs in an auxiliary tmux window for a pair-managed `houmao_server_rest` session
- **THEN** the runtime determines local gateway liveness from the auxiliary tmux pane state for that window
- **AND THEN** the runtime waits for successful gateway health responses before treating the gateway as ready
- **AND THEN** shutdown and crash cleanup target the auxiliary tmux gateway surface rather than a detached subprocess handle

### Requirement: Runtime-owned foreground gateway companions may run in an auxiliary tmux window without redefining the agent surface
For runtime-owned tmux-backed managed sessions launched through `houmao-mgr`, the system SHALL allow the gateway companion to run in a separate auxiliary tmux window in the same tmux session whenever foreground mode is the effective execution mode, whether selected by default or by an explicit override.

When that foreground mode is active, the system SHALL keep tmux window `0` reserved for the managed agent surface and SHALL keep gateway output off that primary agent window.

When that foreground mode is active, the runtime SHALL treat the gateway auxiliary tmux window and pane as the authoritative local execution surface for gateway lifecycle management. It SHALL use tmux-owned pane state for local liveness, SHALL use gateway health responses for readiness, and SHALL target that auxiliary tmux surface for shutdown rather than relying on a detached subprocess handle.

The gateway companion SHALL continue writing its own durable logs to gateway-owned storage even when its console output is visible in an auxiliary tmux window.

#### Scenario: Runtime-owned default foreground attach adds an auxiliary window without redefining the agent surface
- **WHEN** a gateway companion attaches later to an already-running runtime-owned tmux-backed session without an explicit background override
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

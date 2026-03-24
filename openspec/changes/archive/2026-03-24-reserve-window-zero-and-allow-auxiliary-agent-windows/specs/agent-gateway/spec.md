## MODIFIED Requirements

### Requirement: Pair-owned gateway attach for managed `houmao_server_rest` sessions supports explicit and current-session targeting
The system SHALL expose `houmao-srv-ctrl agent-gateway attach` as the pair-owned gateway attach surface for pair-managed tmux-backed TUI sessions whose runtime backend is `houmao_server_rest`.

When called with `--agent <agent-ref>`, the command SHALL resolve the target through the Houmao managed-agent identity namespace and SHALL execute attach through the managed-agent gateway attach route rather than through raw `cao` or raw runtime CLI semantics.

When called without `--agent`, the command SHALL require execution inside the target agent's tmux session, SHALL discover the current tmux session as the attach context, SHALL read stable gateway attachability pointers from the current tmux session environment, SHALL require those pointers to resolve to a readable `houmao_server_rest` attach contract, SHALL treat that contract's persisted `api_base_url` and `backend_metadata.session_name` as the authoritative server and managed-agent route target for this mode, and SHALL refuse the attach when those envs are missing, stale, ambiguous, identify a non-`houmao_server_rest` session, or fail to resolve exactly one managed agent on that persisted server.

`houmao-srv-ctrl` SHALL NOT require the user to address raw `cao_rest` or child-CAO topology in order to attach a gateway for pair-managed sessions, and current-session attach SHALL NOT fall back to `terminal_id`, cwd, ambient shell env, or another server target when the persisted contract is invalid or stale.

#### Scenario: Explicit attach resolves through managed-agent identity
- **WHEN** a developer runs `houmao-srv-ctrl agent-gateway attach --agent <agent-ref>` for a pair-managed `houmao_server_rest` session
- **THEN** the command resolves `<agent-ref>` through the managed-agent alias set
- **AND THEN** the attach request is issued through the Houmao managed-agent gateway lifecycle surface

#### Scenario: Current-session attach infers the target from tmux session env
- **WHEN** a developer runs `houmao-srv-ctrl agent-gateway attach` from inside a pair-managed agent tmux session
- **THEN** the command infers the target session from the current tmux session plus stable gateway attachability env pointers
- **AND THEN** the command does not require an explicit agent identity

#### Scenario: Current-session attach uses the persisted server authority and session alias
- **WHEN** a developer runs `houmao-srv-ctrl agent-gateway attach` from inside a pair-managed agent tmux session
- **AND WHEN** the stable attach contract for that session persists `api_base_url=<server>` and `backend_metadata.session_name=<session-name>`
- **THEN** the command issues the managed-agent gateway attach request against `<server>` with `<session-name>` as `{agent_ref}`
- **AND THEN** it does not retarget the request through `terminal_id` or another alias

#### Scenario: Current-session attach fails closed without Houmao gateway env
- **WHEN** a developer runs `houmao-srv-ctrl agent-gateway attach` from a tmux session that does not publish the stable Houmao gateway attachability env pointers
- **THEN** the command fails explicitly
- **AND THEN** it does not guess from cwd, ambient shell env, or raw CAO state

#### Scenario: Current-session attach fails closed when the persisted authority no longer resolves
- **WHEN** a developer runs `houmao-srv-ctrl agent-gateway attach` from inside a pair-managed tmux session
- **AND WHEN** the stable attach contract points at a persisted `api_base_url` plus `session_name` that no longer resolves exactly one managed agent on that server
- **THEN** the command fails explicitly as invalid or stale current-session metadata
- **AND THEN** it does not fall back to `terminal_id` or another server target

### Requirement: Pair-managed `houmao_server_rest` gateway companions may run in an auxiliary tmux window without redefining the agent surface
For pair-managed tmux-backed `houmao_server_rest` sessions, the system SHALL allow the gateway companion to run in a separate auxiliary tmux window in the same tmux session for normal operation.

When the gateway companion runs in the same tmux session, the system SHALL keep tmux window `0` reserved for the managed agent surface and SHALL keep gateway output off that primary agent window.

When the gateway companion runs in the same tmux session, the runtime SHALL treat the gateway auxiliary tmux window and pane as the authoritative local execution surface for gateway lifecycle management. It SHALL use tmux-owned pane state for local liveness, SHALL use gateway health responses for readiness, and SHALL target that auxiliary tmux surface for shutdown rather than relying on a detached subprocess handle.

The gateway companion SHALL continue writing its own durable logs to gateway-owned storage even when its console output is visible in an auxiliary tmux window.

The `houmao-server` process and its internal child-CAO support state SHALL remain outside the agent's tmux session even when the gateway companion runs in the same managed session as the agent.

#### Scenario: Attach-later adds an auxiliary window without redefining the agent surface
- **WHEN** a gateway companion attaches later to an already-running pair-managed `houmao_server_rest` session
- **THEN** the attach flow creates or reuses an auxiliary tmux window for the gateway companion
- **AND THEN** tmux window `0` remains the canonical managed agent surface for that session

#### Scenario: Gateway logging stays off the primary agent surface
- **WHEN** the gateway companion emits logs or diagnostics while running in an auxiliary tmux window
- **THEN** the gateway output appears only in the auxiliary process window and gateway-owned durable log storage
- **AND THEN** normal gateway activity does not inject its own text into the operator-facing agent window `0`

#### Scenario: Same-session gateway lifecycle uses the auxiliary tmux surface
- **WHEN** the gateway companion runs in an auxiliary tmux window for a pair-managed `houmao_server_rest` session
- **THEN** the runtime determines local gateway liveness from the auxiliary tmux pane state for that window
- **AND THEN** the runtime waits for successful gateway health responses before treating the gateway as ready
- **AND THEN** shutdown and crash cleanup target the auxiliary tmux gateway surface rather than a detached subprocess handle

### Requirement: Same-session gateway live state persists an authoritative execution handle
The runtime SHALL persist one authoritative live gateway record under `<session-root>/gateway/run/current-instance.json`.

When the gateway runs in a same-session auxiliary tmux window for `houmao_server_rest`, that live record SHALL include an explicit execution mode plus the tmux window and pane identifiers for the auxiliary gateway surface, in addition to the listener and managed-agent instance fields needed for live gateway status.

Detach, crash cleanup, and auxiliary-window recreation SHALL resolve the live gateway surface from that runtime-owned record rather than from ad hoc tmux discovery over non-contractual auxiliary windows.

When auxiliary-window recreation replaces the live gateway surface, the runtime SHALL update the authoritative live gateway record before treating the recreated gateway as ready.

#### Scenario: Same-session live gateway record captures the tmux execution handle
- **WHEN** a `houmao_server_rest` gateway companion starts in an auxiliary tmux window
- **THEN** the runtime persists one live gateway record under `<session-root>/gateway/run/current-instance.json`
- **AND THEN** that record identifies the same-session execution mode plus the auxiliary tmux window and pane identifiers for the live gateway surface

#### Scenario: Auxiliary-window recreation updates the authoritative live gateway record
- **WHEN** a same-session gateway auxiliary window is replaced during detach, cleanup, or recovery
- **THEN** the runtime updates the authoritative live gateway record to the new tmux window and pane identifiers
- **AND THEN** later detach or cleanup targets the recreated auxiliary gateway surface without rediscovering non-contractual windows heuristically

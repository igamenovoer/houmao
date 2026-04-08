## RENAMED Requirements

### Requirement: `houmao-mgr agents gateway attach` supports explicit foreground tmux-window mode for tmux-backed managed sessions
FROM: ``houmao-mgr agents gateway attach` supports explicit foreground tmux-window mode for tmux-backed managed sessions`
TO: ``houmao-mgr agents gateway attach` defaults tmux-backed managed sessions to foreground tmux-window mode with explicit background opt-out`

## MODIFIED Requirements

### Requirement: `houmao-mgr agents gateway attach` defaults tmux-backed managed sessions to foreground tmux-window mode with explicit background opt-out
`houmao-mgr agents gateway attach` SHALL default tmux-backed managed sessions to same-session foreground tmux-window mode.

`houmao-mgr agents gateway attach` SHALL accept an explicit `--background` option for tmux-backed managed sessions.

When no `--background` override is supplied for a runtime-owned tmux-backed managed session, `houmao-mgr` SHALL attach or reuse the gateway in same-session foreground tmux-window mode rather than detached-process mode.

When no `--background` override is supplied for a pair-managed `houmao_server_rest` session, `houmao-mgr` SHALL treat the attach as the standard same-session auxiliary-window topology for that managed session.

When `--background` is requested for a tmux-backed managed session, `houmao-mgr` SHALL attach or reuse the gateway in detached background execution rather than same-session foreground tmux-window mode.

When foreground tmux-window mode is active, `houmao-mgr agents gateway attach` and `houmao-mgr agents gateway status` SHALL surface the gateway execution mode and the authoritative tmux window index for the live gateway surface so operators can inspect that console directly.

Foreground tmux-window mode SHALL NOT redefine the managed agent attach contract: tmux window `0` remains reserved for the agent surface, and the gateway window SHALL use index `>=1`.

#### Scenario: Default gateway attach uses foreground mode for a runtime-owned tmux-backed session
- **WHEN** an operator runs `houmao-mgr agents gateway attach --agent-id <id>`
- **AND WHEN** the addressed managed session is a runtime-owned tmux-backed session
- **THEN** `houmao-mgr` attaches or reuses the gateway in same-session foreground tmux-window mode
- **AND THEN** the command reports the actual tmux window index for the live gateway surface

#### Scenario: Default gateway attach preserves the pair-managed same-session topology
- **WHEN** an operator runs `houmao-mgr agents gateway attach --agent-id <id>`
- **AND WHEN** the addressed managed session is a pair-managed `houmao_server_rest` session
- **THEN** `houmao-mgr` attaches or reuses the gateway in same-session foreground tmux-window mode
- **AND THEN** the command reports the actual tmux window index for the live gateway surface

#### Scenario: Operator requests background gateway attach
- **WHEN** an operator runs `houmao-mgr agents gateway attach --background --agent-id <id>`
- **AND WHEN** the addressed managed session is tmux-backed and gateway-capable
- **THEN** `houmao-mgr` attaches or reuses the gateway in detached background execution
- **AND THEN** the attach result does not claim a foreground tmux gateway window for that attach

#### Scenario: Operator inspects foreground gateway status through the native CLI
- **WHEN** an operator runs `houmao-mgr agents gateway status --agent-id <id>`
- **AND WHEN** the addressed gateway is running in foreground tmux-window mode
- **THEN** the command reports `execution_mode=tmux_auxiliary_window`
- **AND THEN** the command reports the authoritative tmux window index for the live gateway surface

#### Scenario: Foreground attach preserves the agent surface contract
- **WHEN** a tmux-backed managed session runs with foreground gateway execution active
- **THEN** the gateway attaches in a tmux window whose index is `>=1`
- **AND THEN** tmux window `0` remains the managed agent surface

## ADDED Requirements

### Requirement: `houmao-mgr agents gateway attach` supports explicit foreground tmux-window mode for tmux-backed managed sessions
`houmao-mgr agents gateway attach` SHALL accept an explicit `--foreground` option for tmux-backed managed sessions.

When `--foreground` is requested for a runtime-owned tmux-backed managed session, `houmao-mgr` SHALL attach or reuse the gateway in same-session foreground tmux-window mode rather than detached-process mode.

When `--foreground` is requested for a pair-managed `houmao_server_rest` session that already uses same-session tmux-window gateway execution, `houmao-mgr` MAY treat that request as an explicit idempotent request for the already-supported foreground topology.

When foreground tmux-window mode is active, `houmao-mgr agents gateway attach` and `houmao-mgr agents gateway status` SHALL surface the gateway execution mode and the authoritative tmux window index for the live gateway surface so operators can inspect that console directly.

Foreground tmux-window mode SHALL NOT redefine the managed agent attach contract: tmux window `0` remains reserved for the agent surface, and the gateway window SHALL use index `>=1`.

#### Scenario: Operator requests foreground gateway attach for a runtime-owned tmux-backed session
- **WHEN** an operator runs `houmao-mgr agents gateway attach --foreground --agent-id <id>`
- **AND WHEN** the addressed managed session is a runtime-owned tmux-backed session
- **THEN** `houmao-mgr` attaches or reuses the gateway in same-session foreground tmux-window mode
- **AND THEN** the command reports the actual tmux window index for the live gateway surface

#### Scenario: Operator inspects foreground gateway status through the native CLI
- **WHEN** an operator runs `houmao-mgr agents gateway status --agent-id <id>`
- **AND WHEN** the addressed gateway is running in foreground tmux-window mode
- **THEN** the command reports `execution_mode=tmux_auxiliary_window`
- **AND THEN** the command reports the authoritative tmux window index for the live gateway surface

#### Scenario: Foreground attach preserves the agent surface contract
- **WHEN** an operator requests foreground gateway attach for a tmux-backed managed session
- **THEN** the gateway attaches in a tmux window whose index is `>=1`
- **AND THEN** tmux window `0` remains the managed agent surface

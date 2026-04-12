## ADDED Requirements

### Requirement: `houmao-touring` advises foreground-first gateway posture during guided launch branches
When the packaged `houmao-touring` skill reaches a branch that launches an agent or attaches a gateway, it SHALL advise foreground-first gateway posture for tmux-backed guided-tour flows unless the user explicitly requests background or detached gateway execution.

The touring guidance SHALL explain that the desired visible first-run topology is the managed-agent surface on tmux window `0` and, when a foreground gateway is attached, the gateway sidecar in a non-zero auxiliary tmux window.

The touring guidance SHALL distinguish a non-interactive CLI handoff that prints a `tmux attach-session` command from detached background gateway execution. It SHALL NOT tell agents to use background gateway flags merely because the current caller cannot automatically attach to tmux.

The touring guidance SHALL route detailed specialist-backed launch flag selection through `houmao-specialist-mgr` and detailed gateway lifecycle attach through `houmao-agent-gateway`, while carrying the same foreground-first and explicit-background rule into the tour branch.

#### Scenario: First-run specialist launch tour prefers foreground gateway posture
- **WHEN** the guided tour helps launch a specialist-backed easy instance
- **AND WHEN** the user has not explicitly requested background gateway execution
- **THEN** the touring branch tells the agent to omit background gateway flags
- **AND THEN** it describes the expected foreground tmux topology for an observable tour run

#### Scenario: Non-interactive handoff is not treated as background gateway execution
- **WHEN** a guided launch succeeds from a non-interactive caller and the CLI reports an attach command instead of switching into tmux
- **THEN** the touring guidance treats that as tmux handoff behavior
- **AND THEN** it does not reinterpret the session as having used detached background gateway execution unless gateway status reports that execution mode

#### Scenario: Explicit background request is honored as an override
- **WHEN** the user explicitly asks the tour to launch or attach the gateway in the background
- **THEN** the touring guidance may route to the supported background gateway flag through the owning skill
- **AND THEN** it explains that this is an explicit override from the foreground-first tour posture

#### Scenario: Gateway status clarifies current tour posture
- **WHEN** the guided tour needs to explain whether a launched agent has a foreground gateway window or detached gateway process
- **THEN** the touring guidance tells the agent to inspect supported gateway status fields such as `execution_mode` and `gateway_tmux_window_index`
- **AND THEN** it does not rely on naming conventions or assume background mode from lack of automatic tmux attachment

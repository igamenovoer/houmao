## ADDED Requirements

### Requirement: `houmao-agent-gateway` teaches foreground-first gateway attach posture
The packaged `houmao-agent-gateway` lifecycle guidance SHALL present `houmao-mgr agents gateway attach` without `--background` as the first-choice command shape for tmux-backed managed sessions.

The lifecycle guidance SHALL state that foreground gateway attach uses a same-session auxiliary tmux window when supported, leaving the managed-agent surface on tmux window `0` and using a non-zero gateway tmux window for the live sidecar.

The lifecycle guidance SHALL state that `--background` requests detached gateway process execution and SHALL only be used when the current user prompt or recent conversation explicitly asks for background or detached gateway execution.

The lifecycle guidance SHALL tell agents to report foreground execution metadata returned by status, including `execution_mode` and `gateway_tmux_window_index` when present, instead of inferring gateway topology from tmux window names or ordering.

#### Scenario: Default attach uses foreground command shape
- **WHEN** an agent follows `houmao-agent-gateway` lifecycle guidance to attach a gateway to a tmux-backed managed session
- **AND WHEN** the user has not explicitly requested detached background gateway execution
- **THEN** the guidance directs the agent to use `houmao-mgr agents gateway attach` without `--background`
- **AND THEN** it describes that as the foreground same-session auxiliary-window attach path when supported

#### Scenario: Background attach requires explicit user intent
- **WHEN** an agent follows `houmao-agent-gateway` lifecycle guidance
- **AND WHEN** the user explicitly asks for background gateway execution, detached gateway process execution, or avoiding a gateway tmux window
- **THEN** the guidance may direct the agent to use `houmao-mgr agents gateway attach --background`
- **AND THEN** it does not present `--background` as the default attach posture

#### Scenario: Foreground metadata is reported instead of guessed
- **WHEN** a foreground gateway attach or status command returns `execution_mode` and `gateway_tmux_window_index`
- **THEN** the guidance tells the agent to report those returned fields as the authoritative gateway execution metadata
- **AND THEN** it does not tell the agent to guess gateway topology from tmux window names or ordering

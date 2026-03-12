## ADDED Requirements

### Requirement: Gateway-enabled tmux-backed sessions launch a same-window gateway sidecar
When gateway support is enabled for a tmux-backed session, the runtime SHALL create the gateway bootstrap state needed for that session and SHALL launch the gateway sidecar within the same tmux window lifecycle as the managed agent TUI.

The runtime SHALL NOT satisfy this requirement by creating a separate visible tmux window or pane for the gateway sidecar during normal operator use.

#### Scenario: Session start launches gateway sidecar before foreground TUI takes over
- **WHEN** a developer starts a gateway-enabled tmux-backed session
- **THEN** the runtime prepares the gateway bootstrap state for that session
- **AND THEN** the runtime launches the gateway sidecar in the same tmux window lifecycle as the managed agent TUI before or as the foreground TUI takes over that visible terminal surface

#### Scenario: Gateway launch keeps the operator-visible tmux surface singular
- **WHEN** a developer attaches to a gateway-enabled tmux-backed session after startup
- **THEN** the managed agent TUI remains the only visible operator surface for normal interaction
- **AND THEN** the runtime has not created a separate visible tmux window or pane solely for the gateway sidecar

### Requirement: Gateway-enabled sessions persist and restore gateway bootstrap metadata
For gateway-enabled tmux-backed sessions, the runtime SHALL persist the resolved gateway bootstrap metadata in session state so resumed control paths can restore or validate the same gateway root and protocol context.

#### Scenario: Session start persists gateway metadata for resume
- **WHEN** a developer starts a gateway-enabled tmux-backed session
- **THEN** the runtime persists the gateway metadata needed to rediscover that session's gateway root and bootstrap context later
- **AND THEN** resumed control paths can validate or restore gateway discovery using persisted session state instead of re-deriving an unrelated gateway location

#### Scenario: Resume preserves the same gateway identity for a live session
- **WHEN** a developer resumes control of a gateway-enabled tmux-backed session
- **THEN** the runtime uses the persisted session state to rediscover the expected gateway root and bootstrap context for that live session
- **AND THEN** the resumed control path does not silently attach the session to a different gateway identity

### Requirement: Gateway-enabled tmux sessions publish gateway discovery bindings
When gateway support is enabled for a tmux-backed session, the runtime SHALL publish gateway discovery bindings into the tmux session environment in addition to the existing manifest and agent-definition bindings.

At minimum, the runtime SHALL publish:

- `AGENTSYS_GATEWAY_ROOT`
- `AGENTSYS_GATEWAY_STATE_PATH`
- `AGENTSYS_GATEWAY_PROTOCOL_VERSION`

When resumed runtime control has already determined the effective gateway bindings for the same live session, it SHALL re-publish those bindings into the tmux session environment.

#### Scenario: Session start publishes gateway discovery bindings
- **WHEN** the runtime starts a gateway-enabled tmux-backed session
- **THEN** the tmux session environment contains `AGENTSYS_GATEWAY_ROOT`, `AGENTSYS_GATEWAY_STATE_PATH`, and `AGENTSYS_GATEWAY_PROTOCOL_VERSION`
- **AND THEN** those bindings point to the active gateway root and its current state artifact for that session

#### Scenario: Resume re-publishes gateway discovery bindings
- **WHEN** the runtime resumes control of a gateway-enabled tmux-backed session
- **AND WHEN** the effective gateway bindings for that session have already been determined
- **THEN** the runtime re-publishes `AGENTSYS_GATEWAY_ROOT`, `AGENTSYS_GATEWAY_STATE_PATH`, and `AGENTSYS_GATEWAY_PROTOCOL_VERSION` into the tmux session environment

### Requirement: Gateway-aware runtime control paths submit managed work through the gateway
For gateway-enabled sessions, runtime-owned control paths that submit terminal-mutating managed work SHALL use the session's gateway submission path rather than performing raw concurrent tmux mutation directly from the caller.

Read-oriented status inspection MAY read validated gateway state without entering the mutation queue.

#### Scenario: Runtime submits managed work through the gateway queue
- **WHEN** a runtime-owned control path submits gateway-managed terminal-mutating work for a resumed gateway-enabled session
- **THEN** the runtime writes that work through the session's gateway submission path
- **AND THEN** the runtime does not bypass the gateway by performing raw concurrent terminal mutation directly from the caller for that gateway-managed request

#### Scenario: Runtime reads gateway status without consuming the mutation slot
- **WHEN** an operator or tool asks the runtime for gateway status on a gateway-enabled session
- **THEN** the runtime reads validated gateway state for that session
- **AND THEN** the status read does not require the runtime to consume the gateway's terminal-mutation slot

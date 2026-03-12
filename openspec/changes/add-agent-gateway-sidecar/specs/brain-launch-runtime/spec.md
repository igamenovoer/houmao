## ADDED Requirements

### Requirement: Gateway-enabled tmux-backed sessions launch a same-window gateway sidecar
When gateway support is enabled for a tmux-backed session, the runtime SHALL create the gateway bootstrap state needed for that session and SHALL launch the gateway sidecar within the same tmux window lifecycle as the managed agent TUI.

The runtime SHALL NOT satisfy this requirement by creating a separate visible tmux window or pane for the gateway sidecar during normal operator use.

The launched gateway sidecar SHALL run the session's HTTP service on the resolved gateway host and port for gateway-managed status inspection and request submission.

#### Scenario: Session start launches gateway sidecar before foreground TUI takes over
- **WHEN** a developer starts a gateway-enabled tmux-backed session
- **THEN** the runtime prepares the gateway bootstrap state for that session
- **AND THEN** the runtime launches the gateway sidecar in the same tmux window lifecycle as the managed agent TUI before or as the foreground TUI takes over that visible terminal surface
- **AND THEN** the launched sidecar provides the session's HTTP gateway service on the resolved listener address

#### Scenario: Gateway launch keeps the operator-visible tmux surface singular
- **WHEN** a developer attaches to a gateway-enabled tmux-backed session after startup
- **THEN** the managed agent TUI remains the only visible operator surface for normal interaction
- **AND THEN** the runtime has not created a separate visible tmux window or pane solely for the gateway sidecar

### Requirement: Gateway host and port are resolved before session start with explicit precedence
For gateway-enabled tmux-backed sessions, the runtime SHALL resolve one effective gateway host and one effective gateway port before building the launch plan and starting the session.

The precedence order for the effective gateway host SHALL be:

1. `start-session --gateway-host`
2. caller environment variable `AGENTSYS_AGENT_GATEWAY_HOST`
3. blueprint configuration value `gateway.host`
4. default `127.0.0.1`

Allowed effective gateway host values in this change are exactly `127.0.0.1` and `0.0.0.0`.

The precedence order for the effective gateway port SHALL be:

1. `start-session --gateway-port`
2. caller environment variable `AGENTSYS_AGENT_GATEWAY_PORT`
3. blueprint configuration value `gateway.port`
4. one system-selected free port when none of the above are provided

After resolving that effective gateway host and port, the runtime SHALL use the same listener address for gateway bootstrap metadata, session-manifest persistence, tmux environment publication, and gateway-sidecar startup.

If the resolved gateway listener cannot be bound during startup, the runtime SHALL fail the session launch explicitly and SHALL NOT silently replace it with a different host or port.

#### Scenario: Default host remains loopback when no host override is supplied
- **WHEN** a developer starts a gateway-enabled tmux-backed session without `--gateway-host`
- **AND WHEN** caller environment omits `AGENTSYS_AGENT_GATEWAY_HOST`
- **AND WHEN** the selected blueprint does not declare `gateway.host`
- **THEN** the runtime resolves `127.0.0.1` as the effective gateway host for that session
- **AND THEN** the started session does not expose all-interface binding by default

#### Scenario: Explicit gateway-host override enables all-interface bind
- **WHEN** a developer starts a gateway-enabled tmux-backed session with `--gateway-host 0.0.0.0`
- **THEN** the runtime resolves `0.0.0.0` as the effective gateway host for that session
- **AND THEN** the started session binds the gateway sidecar on all interfaces for the resolved port

#### Scenario: CLI gateway-port override wins over env and blueprint defaults
- **WHEN** a developer starts a gateway-enabled tmux-backed session with `--gateway-port 43123`
- **AND WHEN** caller environment sets `AGENTSYS_AGENT_GATEWAY_PORT=43124`
- **AND WHEN** the selected blueprint declares `gateway.port: 43125`
- **THEN** the runtime resolves `43123` as the effective gateway port for that session
- **AND THEN** the started session records and publishes `43123` as its gateway port

#### Scenario: Env gateway-port override wins over blueprint default
- **WHEN** a developer starts a gateway-enabled tmux-backed session without `--gateway-port`
- **AND WHEN** caller environment sets `AGENTSYS_AGENT_GATEWAY_PORT=43124`
- **AND WHEN** the selected blueprint declares `gateway.port: 43125`
- **THEN** the runtime resolves `43124` as the effective gateway port for that session
- **AND THEN** the started session does not treat the blueprint default as the effective port

#### Scenario: Runtime selects a free port when no explicit gateway port is supplied
- **WHEN** a developer starts a gateway-enabled tmux-backed session without `--gateway-port`
- **AND WHEN** caller environment omits `AGENTSYS_AGENT_GATEWAY_PORT`
- **AND WHEN** the selected blueprint does not declare `gateway.port`
- **THEN** the runtime selects one currently free local port for that session before launch
- **AND THEN** the started session records and publishes that selected port as its effective gateway port

#### Scenario: Resolved port conflict fails launch
- **WHEN** the runtime attempts to start a gateway-enabled tmux-backed session whose resolved gateway port is unavailable at bind time
- **THEN** the runtime fails that session startup with an explicit gateway-port error
- **AND THEN** it does not silently launch the same session on a different port

### Requirement: Gateway enablement is independent from mailbox enablement
The runtime SHALL allow a tmux-backed session to be gateway-enabled without also enabling mailbox transport or projecting mailbox runtime assets.

Gateway bootstrap, discovery publication, and resumed gateway control SHALL NOT depend on mailbox bindings being present for that session.

#### Scenario: Session start enables gateway without mailbox transport
- **WHEN** a developer starts a gateway-enabled tmux-backed session with no mailbox transport configured
- **THEN** the runtime still prepares gateway bootstrap state and launches the same-window gateway sidecar
- **AND THEN** gateway startup does not fail solely because mailbox support is not enabled

#### Scenario: Resume preserves gateway control without mailbox bindings
- **WHEN** a developer resumes control of a gateway-enabled tmux-backed session whose gateway metadata is present
- **AND WHEN** mailbox-specific runtime bindings are absent for that session
- **THEN** the runtime still restores gateway discovery and gateway-aware control behavior for that live session
- **AND THEN** resumed gateway control does not require mailbox bindings to be reintroduced

### Requirement: Gateway-enabled sessions persist and restore gateway bootstrap metadata
For gateway-enabled tmux-backed sessions, the runtime SHALL persist the resolved gateway bootstrap metadata in session state so resumed control paths can restore or validate the same gateway root, gateway host, gateway port, and protocol context.

#### Scenario: Session start persists gateway metadata for resume
- **WHEN** a developer starts a gateway-enabled tmux-backed session
- **THEN** the runtime persists the gateway metadata needed to rediscover that session's gateway root and bootstrap context later
- **AND THEN** resumed control paths can validate or restore gateway discovery using persisted session state instead of re-deriving an unrelated gateway location

#### Scenario: Resume preserves the same gateway identity for a live session
- **WHEN** a developer resumes control of a gateway-enabled tmux-backed session
- **THEN** the runtime uses the persisted session state to rediscover the expected gateway root, gateway host, gateway port, and bootstrap context for that live session
- **AND THEN** the resumed control path does not silently attach the session to a different gateway identity or different gateway listener address

### Requirement: Gateway-enabled tmux sessions publish gateway discovery bindings
When gateway support is enabled for a tmux-backed session, the runtime SHALL publish gateway discovery bindings into the tmux session environment in addition to the existing manifest and agent-definition bindings.

At minimum, the runtime SHALL publish:

- `AGENTSYS_AGENT_GATEWAY_HOST`
- `AGENTSYS_AGENT_GATEWAY_PORT`
- `AGENTSYS_GATEWAY_ROOT`
- `AGENTSYS_GATEWAY_STATE_PATH`
- `AGENTSYS_GATEWAY_PROTOCOL_VERSION`

When resumed runtime control has already determined the effective gateway bindings for the same live session, it SHALL re-publish those bindings into the tmux session environment.

#### Scenario: Session start publishes gateway discovery bindings
- **WHEN** the runtime starts a gateway-enabled tmux-backed session
- **THEN** the tmux session environment contains `AGENTSYS_AGENT_GATEWAY_HOST`, `AGENTSYS_AGENT_GATEWAY_PORT`, `AGENTSYS_GATEWAY_ROOT`, `AGENTSYS_GATEWAY_STATE_PATH`, and `AGENTSYS_GATEWAY_PROTOCOL_VERSION`
- **AND THEN** those bindings point to the active gateway host, gateway port, gateway root, and current state artifact for that session

#### Scenario: Resume re-publishes gateway discovery bindings
- **WHEN** the runtime resumes control of a gateway-enabled tmux-backed session
- **AND WHEN** the effective gateway bindings for that session have already been determined
- **THEN** the runtime re-publishes `AGENTSYS_AGENT_GATEWAY_HOST`, `AGENTSYS_AGENT_GATEWAY_PORT`, `AGENTSYS_GATEWAY_ROOT`, `AGENTSYS_GATEWAY_STATE_PATH`, and `AGENTSYS_GATEWAY_PROTOCOL_VERSION` into the tmux session environment

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

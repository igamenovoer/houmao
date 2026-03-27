## MODIFIED Requirements

### Requirement: Optional CAO backend via REST boundary
The system SHALL optionally support CAO-compatible session control through a REST boundary without requiring the core runtime to depend on CAO internals.

For supported operator workflows after this change, that CAO-compatible control SHALL be reached through the Houmao-owned pair authority rather than through public `houmao-cli` flows that create or control standalone `cao_rest` sessions.

The runtime MAY retain internal CAO-compatible adapter code for parity, debugging, or transition purposes, but public runtime-management CLI entrypoints that would create or control standalone CAO-backed sessions SHALL fail fast with explicit migration guidance to `houmao-server` and `houmao-mgr`.

That public deprecation guard SHALL reject deprecated `backend="cao_rest"` operator selections at the CLI entrypoint layer before standalone runtime-session construction begins.

For supported loopback compatibility authorities (`http://localhost:<port>`,
`http://127.0.0.1:<port>` with explicit ports), runtime-owned HTTP communication SHALL bypass ambient proxy environment variables by default by ensuring loopback entries exist in `NO_PROXY` and `no_proxy`.

When `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`, the runtime SHALL NOT modify `NO_PROXY` or `no_proxy` and will respect caller-provided values.

When the runtime uses a pair-backed compatibility authority internally, it SHALL pass the resolved working directory through to that authority as launch input and SHALL NOT impose a repo-owned validation rule that requires the workdir to live under the user home tree, the tool home, or a deprecated launcher home.

#### Scenario: Deprecated raw CAO-backed runtime start fails with migration guidance
- **WHEN** a developer invokes `houmao-cli` in a way that would start a standalone `cao_rest` session
- **THEN** the command exits non-zero with explicit guidance to use `houmao-server` and `houmao-mgr`
- **AND THEN** it does not create a new standalone CAO-backed session as a supported operator workflow

#### Scenario: CLI rejects deprecated backend selection before runtime construction
- **WHEN** a developer runs `houmao-cli start-session --backend cao_rest ...`
- **THEN** the CLI rejects that request with migration guidance before constructing a standalone `CaoRestSession`

### Requirement: Runtime can start sessions through an optional `houmao-server` REST backend
The runtime SHALL support an optional `houmao-server` REST-backed mode for live interactive sessions.

When that mode is selected, the runtime SHALL:

- create or attach the live session through `houmao-server`
- persist the `houmao-server` base URL plus session and terminal identity in the session manifest
- treat `houmao-server` as the server authority for later control operations
- keep any `houmao-server` upstream-adapter details out of the public runtime backend identity
- treat `houmao-server` as part of the supported `houmao-server + houmao-mgr` pair rather than as a mixed-pair bridge to raw `cao`

For supported loopback `houmao-server` base URLs, runtime-owned HTTP communication SHALL bypass ambient proxy environment variables by default by ensuring loopback entries exist in `NO_PROXY` and `no_proxy`.

When `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`, the runtime SHALL NOT modify `NO_PROXY` or `no_proxy` and will respect caller-provided values.

#### Scenario: Starting a `houmao-server` session persists server identity
- **WHEN** a developer starts a new interactive session using the `houmao-server` REST-backed mode
- **THEN** the runtime persists a session manifest that records the `houmao-server` base URL and terminal identity needed for resume and later control
- **AND THEN** subsequent runtime control does not need a separate CAO base URL override for that session

#### Scenario: Runtime does not promise mixed-pair bridging through `houmao-server`
- **WHEN** a developer uses the `houmao-server` REST-backed mode
- **THEN** the runtime treats that session as part of the `houmao-server` Houmao-managed path
- **AND THEN** it does not claim support for mixing that path with raw `cao` client workflows behind the scenes

#### Scenario: Loopback `houmao-server` communication bypasses ambient proxy env by default
- **WHEN** a developer starts or resumes a `houmao-server`-backed session using loopback base URL `http://127.0.0.1:9890`
- **AND WHEN** caller environment includes `HTTP_PROXY`, `HTTPS_PROXY`, or `ALL_PROXY`
- **THEN** runtime-owned HTTP communication to that loopback `houmao-server` endpoint bypasses those proxy endpoints by default

### Requirement: Pair-managed `houmao_server_rest` sessions are tmux-backed, reserve window 0, and publish stable gateway attachability before live attach
For pair-managed TUI sessions that use `backend = "houmao_server_rest"`, the runtime SHALL create or resume one tmux session per managed agent session.

The runtime SHALL choose and persist one tmux session name per launched session as a stable live-session handle rather than assuming the canonical agent identity is the tmux session name.

The runtime SHALL reserve tmux window `0` as the primary agent surface for that session and SHALL keep the managed agent itself on that primary surface across pair-managed turns.

The runtime SHALL publish `AGENTSYS_MANIFEST_PATH=<absolute manifest path>` into the tmux session environment so that pair-managed discovery can locate the persisted session manifest.

The runtime SHALL reuse the existing runtime-owned gateway capability publication seam to materialize `gateway/attach.json`, `gateway/state.json`, queue/bootstrap assets, and the stable gateway attachability pointers `AGENTSYS_GATEWAY_ATTACH_PATH=<absolute attach path>` and `AGENTSYS_GATEWAY_ROOT=<absolute gateway root>` during pair launch or launch registration, before a live gateway is attached.

A pair-managed session SHALL NOT be treated as current-session attach-ready until both that runtime-owned gateway capability publication and successful managed-agent registration for the same persisted `api_base_url` and `session_name` have completed.

The runtime SHALL allow auxiliary windows to exist later in the same tmux session for gateway or operator diagnostics, but they SHALL NOT displace the agent from window `0` and SHALL NOT redefine the primary pair-managed attach surface.

Runtime-controlled pair-managed turns and pair-managed tmux resolution SHALL continue targeting the agent surface in window `0` even when another tmux window is currently selected in the foreground for observability.

#### Scenario: Pair launch creates a gateway-capable tmux session before live attach
- **WHEN** a developer launches a pair-managed TUI session through `houmao-mgr`
- **THEN** the runtime persists the actual tmux session name for that live session
- **AND THEN** the tmux session environment contains `AGENTSYS_MANIFEST_PATH`
- **AND THEN** the tmux session environment contains `AGENTSYS_GATEWAY_ATTACH_PATH` and `AGENTSYS_GATEWAY_ROOT`
- **AND THEN** the gateway capability artifacts are materialized through the shared runtime-owned gateway publication seam
- **AND THEN** window `0` is reserved as the primary agent surface for that session

#### Scenario: Current-session attach is unavailable before matching registration completes
- **WHEN** a delegated pair launch has already published stable gateway attachability into the tmux session
- **AND WHEN** managed-agent registration for that same persisted `api_base_url` and `session_name` has not yet completed successfully
- **THEN** the session is not yet current-session attach-ready
- **AND THEN** pair-managed current-session gateway attach fails closed rather than guessing another authority or alias

#### Scenario: Foreground auxiliary window does not retarget pair-managed execution
- **WHEN** a pair-managed `houmao_server_rest` session has an auxiliary gateway or diagnostics window selected in the foreground
- **AND WHEN** the runtime starts another controlled turn against that managed session
- **THEN** the controlled work still executes on the agent surface in window `0`
- **AND THEN** the runtime does not need to treat the selected auxiliary window as the authoritative agent surface

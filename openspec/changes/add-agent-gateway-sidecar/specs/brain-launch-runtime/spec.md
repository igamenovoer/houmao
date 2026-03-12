## ADDED Requirements

### Requirement: Runtime-owned tmux sessions may publish gateway attachability independently from a running gateway
The runtime SHALL be able to make a tmux-backed session gateway-capable without requiring a gateway process to already be running.

For runtime-owned tmux-backed sessions, the runtime SHALL publish secret-free gateway attach metadata that later attach flows can use to start a gateway for the live session.

That attachability publication SHALL be additive and SHALL NOT make legacy non-gateway start or resume behavior fail by itself.

Blueprint `gateway.host` and `gateway.port` values SHALL act only as defaults after gateway attach is requested and SHALL NOT make a session gateway-capable or gateway-running by themselves.

In v1, the runtime SHALL publish attach metadata by default for newly started runtime-owned tmux-backed sessions and SHALL support live gateway attach for runtime-owned `backend=cao_rest` sessions first.

Supplying gateway listener overrides without either launch-time auto-attach or an explicit attach lifecycle action SHALL fail with an explicit error.

If a caller requests live gateway attach for any backend whose gateway adapter is not yet implemented, the runtime SHALL fail with an explicit unsupported-backend error rather than silently falling back to implicit direct control.

#### Scenario: Blueprint gateway defaults do not auto-attach the gateway by themselves
- **WHEN** a developer starts a session from a blueprint that declares `gateway.host` or `gateway.port`
- **AND WHEN** the developer does not request launch-time gateway attach
- **THEN** the runtime publishes attachability metadata for that session
- **AND THEN** the blueprint listener defaults do not cause a live gateway instance to start by themselves

#### Scenario: Gateway host or port overrides require an attach action
- **WHEN** a developer supplies gateway host or port overrides without requesting launch-time attach or an explicit attach lifecycle action
- **THEN** the runtime fails with an explicit gateway-lifecycle error
- **AND THEN** the session is not treated as having a live gateway instance implicitly

#### Scenario: Unsupported backend rejects live gateway attach in v1
- **WHEN** a developer requests live gateway attach for a runtime-owned tmux-backed backend other than the currently supported adapter set
- **THEN** the runtime fails that attach request with an explicit unsupported-backend error
- **AND THEN** the runtime does not silently convert that attach request into legacy direct control

### Requirement: Runtime-owned tmux sessions publish a stable gateway attach contract
When the runtime makes a tmux-backed session gateway-capable, it SHALL publish a stable attach contract for that session in a secret-free file and SHALL expose the absolute path to that file through tmux session environment.

The attach contract SHALL be sufficient for a later gateway attach flow to determine how to observe and control the live session.

Runtime-owned attachability publication SHALL coexist with the existing manifest and agent-definition discovery pointers instead of replacing them.

For runtime-owned sessions in v1, the deterministic gateway-root identity SHALL be the runtime-generated session id used for manifest storage, and the attach contract SHALL live at `<AGENTSYS_GATEWAY_ROOT>/attach.json`.

#### Scenario: Session start publishes attach metadata without a live gateway
- **WHEN** a developer starts a runtime-owned tmux-backed session without launch-time gateway attach
- **THEN** the runtime publishes stable gateway attach metadata for that live session
- **AND THEN** the session can remain gateway-capable even though no gateway instance is currently running

#### Scenario: Resume re-publishes attach metadata
- **WHEN** the runtime resumes control of a runtime-owned tmux-backed session
- **AND WHEN** attachability metadata for that session can be determined from persisted session state
- **THEN** the runtime re-publishes the attach-contract pointer for that live session
- **AND THEN** later attach flows do not need to rediscover the session from unrelated state

#### Scenario: Runtime-owned gateway root uses the persisted session id
- **WHEN** the runtime starts a runtime-owned tmux-backed session with generated session id `cao_rest-20260312-120000Z-abcd1234`
- **THEN** the stable gateway root for that session is derived from that persisted session id
- **AND THEN** the attach-contract path for that session is `<gateway-root>/attach.json`

### Requirement: Runtime supports optional launch-time auto-attach for supported backends
When a caller explicitly requests launch-time gateway attach for a supported backend, the runtime SHALL start the agent session, resolve attach metadata for that live session, and then start a gateway instance without restarting the agent.

When launch-time auto-attach fails, the runtime SHALL fail that auto-attach action explicitly.

Whether the already-started agent session is kept running after auto-attach failure SHALL be a defined runtime policy rather than an implicit side effect.

#### Scenario: Launch-time auto-attach starts gateway after session startup
- **WHEN** a developer starts a supported runtime-owned tmux-backed session with launch-time gateway attach requested
- **THEN** the runtime starts the managed session first
- **AND THEN** the runtime starts a gateway instance for that live session using the published attach metadata
- **AND THEN** the managed session does not need to be restarted in order to gain gateway support

#### Scenario: Auto-attach failure reports explicit lifecycle error
- **WHEN** launch-time auto-attach fails after the managed tmux session has already started
- **THEN** the runtime reports an explicit gateway-attach error
- **AND THEN** the outcome for the already-started managed session follows the documented runtime policy for attach failure

### Requirement: Gateway host and port are resolved when a gateway instance is started
For gateway attach or launch-time auto-attach actions, the runtime SHALL resolve one effective gateway host and one effective gateway port before starting that gateway instance.

The precedence order for the effective gateway host SHALL be:

1. lifecycle CLI override for the attach action in progress
2. caller environment variable `AGENTSYS_AGENT_GATEWAY_HOST`
3. blueprint configuration value `gateway.host`
4. default `127.0.0.1`

Allowed effective gateway host values in this change are exactly `127.0.0.1` and `0.0.0.0`.

The precedence order for the effective gateway port SHALL be:

1. lifecycle CLI override for the attach action in progress
2. caller environment variable `AGENTSYS_AGENT_GATEWAY_PORT`
3. blueprint configuration value `gateway.port`
4. one system-selected free port when none of the above are provided

After resolving that effective gateway host and port, the runtime SHALL use the same listener address for the active gateway instance's metadata, tmux environment publication, and gateway startup.

If the resolved gateway listener cannot be bound during gateway start, the runtime SHALL fail that attach or auto-attach action explicitly and SHALL NOT silently replace it with a different host or port.

When a gateway instance starts successfully with a system-selected port, the runtime SHALL persist that resolved host and port as the desired listener for the gateway root and SHALL reuse them on later restarts unless a caller explicitly overrides them.

#### Scenario: Default host remains loopback when no host override is supplied
- **WHEN** a developer starts a gateway attach action without an explicit gateway-host override
- **AND WHEN** caller environment omits `AGENTSYS_AGENT_GATEWAY_HOST`
- **AND WHEN** the selected blueprint does not declare `gateway.host`
- **THEN** the runtime resolves `127.0.0.1` as the effective gateway host for that session
- **AND THEN** the started session does not expose all-interface binding by default

#### Scenario: Explicit gateway-host override enables all-interface bind
- **WHEN** a developer starts a gateway attach action with `--gateway-host 0.0.0.0`
- **THEN** the runtime resolves `0.0.0.0` as the effective gateway host for that session
- **AND THEN** the started gateway instance binds its HTTP listener on all interfaces for the resolved port

#### Scenario: CLI gateway-port override wins over env and blueprint defaults
- **WHEN** a developer starts a gateway attach action with `--gateway-port 43123`
- **AND WHEN** caller environment sets `AGENTSYS_AGENT_GATEWAY_PORT=43124`
- **AND WHEN** the selected blueprint declares `gateway.port: 43125`
- **THEN** the runtime resolves `43123` as the effective gateway port for that session
- **AND THEN** the started session records and publishes `43123` as its gateway port

#### Scenario: Env gateway-port override wins over blueprint default
- **WHEN** a developer starts a gateway attach action without `--gateway-port`
- **AND WHEN** caller environment sets `AGENTSYS_AGENT_GATEWAY_PORT=43124`
- **AND WHEN** the selected blueprint declares `gateway.port: 43125`
- **THEN** the runtime resolves `43124` as the effective gateway port for that session
- **AND THEN** the started session does not treat the blueprint default as the effective port

#### Scenario: Runtime selects a free port when no explicit gateway port is supplied
- **WHEN** a developer starts a gateway attach action without `--gateway-port`
- **AND WHEN** caller environment omits `AGENTSYS_AGENT_GATEWAY_PORT`
- **AND WHEN** the selected blueprint does not declare `gateway.port`
- **THEN** the runtime selects one currently free local port for that session before launch
- **AND THEN** the started session records and publishes that selected port as its effective gateway port

#### Scenario: Successful auto-selected listener becomes the desired listener for restart
- **WHEN** the runtime starts a gateway instance for a session with a system-selected free port and that gateway startup succeeds
- **THEN** the runtime persists that resolved host and port as the desired listener for that gateway root
- **AND THEN** a later restart reuses that same desired listener unless a caller explicitly overrides it

#### Scenario: Resolved port conflict fails attach
- **WHEN** the runtime attempts to start a gateway instance whose resolved gateway port is unavailable at bind time
- **THEN** the runtime fails that attach action with an explicit gateway-port error
- **AND THEN** it does not silently launch that gateway instance on a different port

### Requirement: Gateway capability and live attach are independent from mailbox enablement
The runtime SHALL allow a gateway-capable or gateway-running tmux-backed session to exist without also enabling mailbox transport or projecting mailbox runtime assets.

Gateway bootstrap, discovery publication, and resumed gateway control SHALL NOT depend on mailbox bindings being present for that session.

#### Scenario: Session start enables gateway without mailbox transport
- **WHEN** a developer makes a tmux-backed session gateway-capable or attaches a gateway with no mailbox transport configured
- **THEN** the runtime still prepares gateway attachability or starts the gateway instance as requested
- **AND THEN** gateway startup does not fail solely because mailbox support is not enabled

#### Scenario: Resume preserves gateway control without mailbox bindings
- **WHEN** a developer resumes control of a gateway-capable or gateway-running tmux-backed session whose gateway metadata is present
- **AND WHEN** mailbox-specific runtime bindings are absent for that session
- **THEN** the runtime still restores gateway discovery and gateway-aware control behavior for that live session
- **AND THEN** resumed gateway control does not require mailbox bindings to be reintroduced

### Requirement: Gateway-capable sessions persist and restore stable attach metadata
For gateway-capable runtime-owned tmux sessions, the runtime SHALL persist the stable gateway attach metadata needed to rediscover the same gateway root, attach contract, and protocol context on resume.

#### Scenario: Session start persists gateway metadata for resume
- **WHEN** a developer starts a gateway-capable runtime-owned tmux session
- **THEN** the runtime persists the gateway metadata needed to rediscover that session's gateway root and attach context later
- **AND THEN** resumed control paths can validate or restore gateway discovery using persisted session state instead of re-deriving an unrelated gateway location

#### Scenario: Resume preserves stable attach identity for a live session
- **WHEN** a developer resumes control of a gateway-capable runtime-owned tmux session
- **THEN** the runtime uses the persisted session state to rediscover the expected gateway root and attach contract for that live session
- **AND THEN** the resumed control path does not silently attach the session to a different gateway-capability identity

### Requirement: Runtime seeds stable gateway state when no live gateway is attached
When the runtime publishes gateway capability for a runtime-owned tmux session, it SHALL create or materialize the gateway root and SHALL seed `state.json` with a protocol-versioned offline or not-attached snapshot even if no live gateway instance exists yet.

When a gateway instance is detached gracefully, the runtime or gateway lifecycle SHALL rewrite `state.json` to the offline or not-attached condition and SHALL clear live gateway bindings while preserving stable attachability metadata.

#### Scenario: Session start seeds offline gateway state before first attach
- **WHEN** the runtime starts a gateway-capable runtime-owned tmux session with no launch-time gateway attach requested
- **THEN** the gateway root already contains `state.json`
- **AND THEN** that seeded state artifact reports an offline or not-attached gateway condition rather than requiring a missing-file special case

#### Scenario: Graceful detach restores offline seeded state
- **WHEN** a gateway instance detaches gracefully from a gateway-capable runtime-owned tmux session
- **THEN** the system rewrites `state.json` to reflect that no live gateway instance is currently attached
- **AND THEN** the stable gateway root remains usable for later re-attach

### Requirement: Runtime publishes stable attach pointers and ephemeral live gateway bindings separately
When the runtime makes a tmux-backed session gateway-capable, it SHALL publish stable attach pointers into the tmux session environment in addition to the existing manifest and agent-definition bindings.

When a live gateway instance is currently attached, the runtime or gateway lifecycle SHALL also publish live gateway bindings for that running instance.

At minimum, the runtime SHALL publish:

- `AGENTSYS_GATEWAY_ATTACH_PATH`
- `AGENTSYS_GATEWAY_ROOT`

When a live gateway instance exists, the system SHALL additionally publish:

- `AGENTSYS_AGENT_GATEWAY_HOST`
- `AGENTSYS_AGENT_GATEWAY_PORT`
- `AGENTSYS_GATEWAY_STATE_PATH`
- `AGENTSYS_GATEWAY_PROTOCOL_VERSION`

When resumed runtime control has already determined the effective attach metadata or live gateway bindings for the same live session, it SHALL re-publish the applicable bindings into the tmux session environment.

#### Scenario: Session start publishes stable attach pointers
- **WHEN** the runtime starts a gateway-capable tmux-backed session
- **THEN** the tmux session environment contains `AGENTSYS_GATEWAY_ATTACH_PATH` and `AGENTSYS_GATEWAY_ROOT`
- **AND THEN** those bindings point to the stable attach contract and gateway root for that session even when no gateway instance is running

#### Scenario: Live gateway attach publishes active gateway bindings
- **WHEN** the runtime or lifecycle command attaches a live gateway instance to a gateway-capable tmux-backed session
- **THEN** the tmux session environment contains `AGENTSYS_AGENT_GATEWAY_HOST`, `AGENTSYS_AGENT_GATEWAY_PORT`, `AGENTSYS_GATEWAY_STATE_PATH`, and `AGENTSYS_GATEWAY_PROTOCOL_VERSION`
- **AND THEN** those bindings point to the currently running gateway instance rather than merely to stable attachability

### Requirement: Runtime exposes independent gateway attach and detach lifecycle actions
The runtime SHALL provide explicit lifecycle actions for attaching a gateway to a live gateway-capable session and for stopping a currently running gateway instance without stopping the managed agent session.

Attach lifecycle actions SHALL resolve the live session, read its stable attach metadata, and then attempt to start a gateway instance for that session.

Detach lifecycle actions SHALL stop the current gateway instance and preserve stable attachability metadata for later re-attach.

#### Scenario: Attach action starts gateway for a running session
- **WHEN** a developer requests gateway attach for a running gateway-capable tmux-backed session
- **THEN** the runtime resolves the live session and reads its attach metadata
- **AND THEN** the runtime starts a gateway instance without restarting the managed agent

#### Scenario: Detach action stops gateway without stopping the agent
- **WHEN** a developer requests gateway detach for a session that currently has a running gateway instance
- **THEN** the runtime stops that gateway instance
- **AND THEN** the managed agent session remains running
- **AND THEN** the session stays gateway-capable for later re-attach

### Requirement: Gateway-aware runtime control paths submit managed work through the gateway
For sessions with a currently running gateway instance, gateway-aware runtime control paths that submit terminal-mutating managed work SHALL use the session's gateway submission path rather than performing raw concurrent tmux mutation directly from the caller.

In v1, this requirement applies to runtime-owned prompt-submission and interrupt flows.

Read-oriented status inspection MAY read validated gateway state without entering the mutation queue.

In v1, when a gateway-aware control path targets a gateway-capable session with no live gateway instance attached, the runtime SHALL fail with an explicit no-live-gateway error and SHALL NOT auto-attach a gateway as a side effect of that control request.

#### Scenario: Runtime submits managed work through the gateway queue
- **WHEN** a runtime-owned control path submits gateway-managed terminal-mutating work for a resumed session with a live gateway instance attached
- **THEN** the runtime writes that work through the session's gateway submission path
- **AND THEN** the runtime does not bypass the gateway by performing raw concurrent terminal mutation directly from the caller for that gateway-managed request

#### Scenario: Runtime routes interrupt through the gateway for sessions with a live gateway instance
- **WHEN** an operator or tool requests interrupt for a resumed session with a live gateway instance attached
- **THEN** the runtime submits that interrupt as gateway-managed work
- **AND THEN** the runtime does not bypass the gateway with direct concurrent terminal mutation for that gateway-managed interrupt request

#### Scenario: Legacy direct control remains available when no gateway is attached
- **WHEN** a runtime-owned tmux-backed session is gateway-capable but no live gateway instance is currently attached
- **THEN** existing non-gateway direct control paths may still operate according to their legacy behavior
- **AND THEN** absence of a live gateway instance alone does not make the session uncontrollable

#### Scenario: Gateway-aware control does not auto-attach implicitly
- **WHEN** a gateway-aware control path targets a gateway-capable session with no live gateway instance attached
- **THEN** the runtime fails that request with an explicit no-live-gateway error
- **AND THEN** the runtime does not start a gateway instance implicitly as a side effect of that control request

#### Scenario: Runtime reads gateway status without consuming the mutation slot
- **WHEN** an operator or tool asks the runtime for gateway status on a session with a live gateway instance attached
- **THEN** the runtime reads validated gateway state for that session
- **AND THEN** the status read does not require the runtime to consume the gateway's terminal-mutation slot

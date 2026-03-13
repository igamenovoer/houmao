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

The attach contract SHALL use one strict versioned schema for both runtime-owned sessions in v1 and future manual-session adopters.

That strict schema SHALL require a shared core containing at least:

- `schema_version`
- `attach_identity`
- `backend`
- `tmux_session_name`
- `working_directory`
- `backend_metadata`

That strict schema MAY additionally include runtime-owned-only fields such as:

- `manifest_path`
- `agent_def_dir`
- `runtime_session_id`
- `desired_host`
- `desired_port`

Runtime-owned attach-contract publication SHALL populate the shared core and any runtime-owned fields that are available for that live session.

Runtime-owned attachability publication SHALL coexist with the existing manifest and agent-definition discovery pointers instead of replacing them.

For runtime-owned sessions in v1, the canonical runtime-owned session root SHALL be `<runtime_root>/sessions/<backend>/<session_id>/`, using the runtime-generated session id used for manifest storage. The session manifest SHALL live at `<session-root>/manifest.json`, the gateway root SHALL live at `<session-root>/gateway`, and the attach contract SHALL live at `<session-root>/gateway/attach.json`.

#### Scenario: Session start publishes attach metadata without a live gateway
- **WHEN** a developer starts a runtime-owned tmux-backed session without launch-time gateway attach
- **THEN** the runtime publishes stable gateway attach metadata for that live session
- **AND THEN** the session can remain gateway-capable even though no gateway instance is currently running

#### Scenario: Resume re-publishes attach metadata
- **WHEN** the runtime resumes control of a runtime-owned tmux-backed session
- **AND WHEN** attachability metadata for that session can be determined from persisted session state
- **THEN** the runtime re-publishes the attach-contract pointer for that live session
- **AND THEN** later attach flows do not need to rediscover the session from unrelated state

#### Scenario: Runtime-owned session root and gateway root use the persisted session id
- **WHEN** the runtime starts a runtime-owned tmux-backed session with generated session id `cao_rest-20260312-120000Z-abcd1234`
- **THEN** the stable runtime-owned session root for that session is derived from that persisted session id under `<runtime_root>/sessions/<backend>/<session_id>/`
- **AND THEN** the session manifest path for that session is `<session-root>/manifest.json`
- **AND THEN** the gateway root for that session is `<session-root>/gateway`
- **AND THEN** the attach-contract path for that session is `<session-root>/gateway/attach.json`

#### Scenario: Runtime-owned attach contract publishes required core plus optional runtime fields
- **WHEN** the runtime publishes attach metadata for a gateway-capable runtime-owned tmux session
- **THEN** the attach contract includes the required shared core fields for attach identity, backend kind, tmux session name, working directory, and backend metadata
- **AND THEN** runtime-owned fields such as `manifest_path` and `runtime_session_id` are included when available
- **AND THEN** the contract is validated as one strict versioned schema rather than as an open-ended map

### Requirement: Runtime supports optional launch-time auto-attach for supported backends
When a caller explicitly requests launch-time gateway attach for a supported backend, the runtime SHALL start the agent session, resolve attach metadata for that live session, and then start a gateway instance without restarting the agent.

When launch-time auto-attach fails, the runtime SHALL fail that auto-attach action explicitly.

If the managed agent session has already started successfully when auto-attach fails, the runtime SHALL keep that managed session running and SHALL return a structured partial-start failure rather than tearing the session down implicitly.

#### Scenario: Launch-time auto-attach starts gateway after session startup
- **WHEN** a developer starts a supported runtime-owned tmux-backed session with launch-time gateway attach requested
- **THEN** the runtime starts the managed session first
- **AND THEN** the runtime starts a gateway instance for that live session using the published attach metadata
- **AND THEN** the managed session does not need to be restarted in order to gain gateway support

#### Scenario: Auto-attach failure reports explicit lifecycle error
- **WHEN** launch-time auto-attach fails after the managed tmux session has already started
- **THEN** the runtime reports an explicit gateway-attach error
- **AND THEN** the already-started managed session remains running
- **AND THEN** the failure surface includes the live session manifest path or identity needed for later retry or explicit stop

### Requirement: Gateway host is resolved and gateway port is finalized when a gateway instance is started
For gateway attach or launch-time auto-attach actions, the runtime SHALL resolve one effective gateway host and one effective gateway port request before starting that gateway instance.

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
4. a system-assigned port request during gateway startup when none of the above are provided

When none of the above sources provide a gateway port, the runtime SHALL request a system-assigned port during gateway startup and SHALL NOT pre-probe a free port in the parent runtime process.

After resolving that effective gateway host and effective gateway port request, the runtime SHALL use the resolved host and the actual bound port for the active gateway instance's metadata, tmux environment publication, and gateway startup.

If the resolved gateway listener cannot be bound during gateway start, the runtime SHALL fail that attach or auto-attach action explicitly and SHALL NOT silently replace it with a different host or port.

When a gateway instance starts successfully with a system-assigned port, the runtime SHALL persist that resolved host and port as the desired listener for the gateway root and SHALL reuse them on later restarts unless a caller explicitly overrides them.

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

#### Scenario: Runtime requests a system-assigned port when no explicit gateway port is supplied
- **WHEN** a developer starts a gateway attach action without `--gateway-port`
- **AND WHEN** caller environment omits `AGENTSYS_AGENT_GATEWAY_PORT`
- **AND WHEN** the selected blueprint does not declare `gateway.port`
- **THEN** the runtime starts gateway startup with a system-assigned port request instead of pre-probing a free local port
- **AND THEN** the started session records and publishes the actual bound port as its effective gateway port

#### Scenario: Successful system-assigned listener becomes the desired listener for restart
- **WHEN** the runtime starts a gateway instance for a session with a system-assigned port request and that gateway startup succeeds
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
For gateway-capable runtime-owned tmux sessions, the runtime SHALL persist the stable gateway attach metadata needed to rediscover the same session-owned gateway root, attach contract, and protocol context on resume.

#### Scenario: Session start persists gateway metadata for resume
- **WHEN** a developer starts a gateway-capable runtime-owned tmux session
- **THEN** the runtime persists the gateway metadata needed to rediscover that session's session-owned gateway root and attach context later
- **AND THEN** resumed control paths can validate or restore gateway discovery using persisted session state instead of re-deriving an unrelated gateway location

#### Scenario: Resume preserves stable attach identity for a live session
- **WHEN** a developer resumes control of a gateway-capable runtime-owned tmux session
- **THEN** the runtime uses the persisted session state to rediscover the expected session-owned gateway root and attach contract for that live session
- **AND THEN** the resumed control path does not silently attach the session to a different gateway-capability identity

### Requirement: Runtime-owned recovery preserves stable session identity while allowing managed-agent replacement
For runtime-owned gateway-capable sessions, the runtime SHALL treat the session root, nested gateway root, and stable attach identity as the durable identity of the logical session even if the managed agent process or terminal is restarted or rebound after unexpected failure.

When runtime-owned recovery reconnects to the same managed-agent instance, the runtime SHALL preserve that stable session identity without allocating a new session root or gateway root.

When runtime-owned recovery rebinds the logical session to a replacement managed-agent instance, the runtime SHALL preserve the existing session root, gateway root, and stable attach identity, and SHALL publish a new managed-agent instance epoch or generation for the replacement upstream instance.

Runtime-owned recovery SHALL NOT require allocating a brand-new gateway root solely because the previous managed-agent process died unexpectedly.

#### Scenario: Same logical session survives managed-agent restart
- **WHEN** a runtime-owned gateway-capable session experiences an unexpected managed-agent failure and bounded recovery reconnects or restarts that same logical session
- **THEN** the runtime preserves the original `<session-root>/` and nested `<session-root>/gateway/`
- **AND THEN** the gateway-facing identity of that logical session does not change solely because the managed agent process was restarted

#### Scenario: Replacement managed-agent instance increments the published epoch
- **WHEN** runtime-owned recovery can continue only by binding a replacement managed-agent instance for the same logical session
- **THEN** the runtime keeps the original stable session root and gateway root
- **AND THEN** the runtime publishes a new managed-agent instance epoch or generation for that replacement upstream instance
- **AND THEN** callers can distinguish "same logical session, replacement upstream instance" from "brand-new logical session"

### Requirement: Runtime seeds stable gateway state when no live gateway is attached
When the runtime publishes gateway capability for a runtime-owned tmux session, it SHALL create or materialize the nested gateway directory under that session's runtime root and SHALL seed `state.json` with a protocol-versioned offline or not-attached snapshot even if no live gateway instance exists yet.

When a gateway instance is detached gracefully, the runtime or gateway lifecycle SHALL rewrite `state.json` to the offline or not-attached condition and SHALL clear live gateway bindings while preserving stable attachability metadata.

When runtime-owned recovery observes unexpected managed-agent loss while a gateway remains attached, the runtime or gateway lifecycle SHALL update the shared status contract so that gateway-local health can remain readable while managed-agent connectivity, recovery state, and request-admission state reflect the outage explicitly.

#### Scenario: Session start seeds offline gateway state before first attach
- **WHEN** the runtime starts a gateway-capable runtime-owned tmux session with no launch-time gateway attach requested
- **THEN** the session-owned gateway directory already contains `state.json`
- **AND THEN** that seeded state artifact reports an offline or not-attached gateway condition rather than requiring a missing-file special case

#### Scenario: Graceful detach restores offline seeded state
- **WHEN** a gateway instance detaches gracefully from a gateway-capable runtime-owned tmux session
- **THEN** the system rewrites `state.json` to reflect that no live gateway instance is currently attached
- **AND THEN** the stable gateway root remains usable for later re-attach

#### Scenario: Unexpected managed-agent loss updates shared status without erasing gateway identity
- **WHEN** a gateway instance remains alive but the runtime-owned managed agent becomes unavailable unexpectedly
- **THEN** the shared status contract continues to identify the same logical session and gateway root
- **AND THEN** that status reports managed-agent recovery or unavailability explicitly instead of collapsing immediately to "no gateway attached"

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

When runtime-owned recovery rebinds the same logical session to a replacement managed-agent instance, the runtime or gateway lifecycle SHALL also refresh any published runtime-managed metadata needed to distinguish the new managed-agent instance from the one that failed.

When resumed runtime control has already determined the effective attach metadata or live gateway bindings for the same live session, it SHALL re-publish the applicable bindings into the tmux session environment.

#### Scenario: Session start publishes stable attach pointers
- **WHEN** the runtime starts a gateway-capable tmux-backed session
- **THEN** the tmux session environment contains `AGENTSYS_GATEWAY_ATTACH_PATH` and `AGENTSYS_GATEWAY_ROOT`
- **AND THEN** those bindings point to the stable attach contract and nested session-owned gateway root for that session even when no gateway instance is running

#### Scenario: Live gateway attach publishes active gateway bindings
- **WHEN** the runtime or lifecycle command attaches a live gateway instance to a gateway-capable tmux-backed session
- **THEN** the tmux session environment contains `AGENTSYS_AGENT_GATEWAY_HOST`, `AGENTSYS_AGENT_GATEWAY_PORT`, `AGENTSYS_GATEWAY_STATE_PATH`, and `AGENTSYS_GATEWAY_PROTOCOL_VERSION`
- **AND THEN** those bindings point to the currently running gateway instance rather than merely to stable attachability

#### Scenario: Managed-agent replacement refreshes runtime-managed metadata
- **WHEN** runtime-owned recovery preserves a logical session but binds a replacement managed-agent instance for it
- **THEN** the runtime or gateway lifecycle refreshes the runtime-managed metadata associated with that logical session
- **AND THEN** later gateway-aware readers can distinguish the replacement managed-agent instance from the one that failed without allocating a new gateway root

### Requirement: Runtime-owned stop-session teardown also cleans up a live attached gateway
When the runtime tears down a runtime-owned session through its authoritative `stop-session` path and that session currently has a live attached gateway, the runtime SHALL stop that gateway as part of the same teardown flow.

That runtime-owned teardown SHALL clear live gateway bindings and SHALL rewrite `state.json` to offline or not-attached state while preserving stable attachability metadata.

#### Scenario: Stop-session stops a live attached gateway for a runtime-owned session
- **WHEN** a runtime-owned session still has a live attached gateway and the operator invokes `stop-session`
- **THEN** the runtime stops that gateway as part of the same teardown flow
- **AND THEN** live gateway bindings are removed or invalidated
- **AND THEN** the session-owned `state.json` returns to offline or not-attached state while the stable gateway root remains addressable

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

When the gateway reports that the managed agent is unavailable, recovering, or blocked on reconciliation, gateway-aware runtime control paths SHALL surface those explicit gateway admission results rather than bypassing the gateway with direct concurrent control.

Before a runtime-owned gateway-aware control or status path trusts live gateway bindings, it SHALL validate those bindings structurally against the stable attach metadata and SHALL use `GET /health` as the authoritative liveness check for the live gateway instance.

Supporting files such as `state.json` or run-state metadata MAY be used to improve diagnostics after health failure, but SHALL NOT replace the health endpoint as the primary liveness decision for runtime-owned gateway clients.

#### Scenario: Runtime submits managed work through the gateway queue
- **WHEN** a runtime-owned control path submits gateway-managed terminal-mutating work for a resumed session with a live gateway instance attached
- **THEN** the runtime writes that work through the session's gateway submission path
- **AND THEN** the runtime does not bypass the gateway by performing raw concurrent terminal mutation directly from the caller for that gateway-managed request

#### Scenario: Runtime routes interrupt through the gateway for sessions with a live gateway instance
- **WHEN** an operator or tool requests interrupt for a resumed session with a live gateway instance attached
- **THEN** the runtime submits that interrupt as gateway-managed work
- **AND THEN** the runtime does not bypass the gateway with direct concurrent terminal mutation for that gateway-managed interrupt request

#### Scenario: Runtime preserves gateway admission semantics during upstream recovery
- **WHEN** a resumed session still has a live gateway instance attached but the gateway reports managed-agent recovery or reconciliation blocking
- **THEN** the runtime surfaces the gateway's explicit unavailable or conflict result to the caller
- **AND THEN** the runtime does not fall back to direct raw terminal mutation merely because the upstream agent is temporarily unavailable

#### Scenario: Stale live gateway bindings fail health-first validation
- **WHEN** a runtime-owned gateway-aware control path discovers live gateway env bindings for a session
- **AND WHEN** those bindings are structurally present but `GET /health` does not confirm a live gateway instance
- **THEN** the runtime treats that session as having no live gateway attached for that control path
- **AND THEN** the caller receives the explicit no-live-gateway outcome instead of an arbitrary raw connection failure

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

## MODIFIED Requirements

### Requirement: Persist a session manifest JSON
The system SHALL persist a session manifest JSON (session handle) alongside the brain manifest for audit, resume, stop, gateway attach authority, and tmux-backed relaunch authority.

For tmux-backed sessions, that manifest SHALL persist normalized session authority that includes at minimum:

- runtime-owned session identity and paths
- authoritative `agent_id` and canonical `agent_name`
- persisted tmux session identity
- agent process pid when a live agent worker process currently exists
- secret-free agent relaunch authority needed for later gateway-managed or CLI-managed relaunch
- the backend-specific attach authority needed for later gateway attach
- the backend-specific runtime control authority needed for later resumed control

For native headless tmux-backed sessions, that manifest SHALL additionally persist enough authority for the gateway or resumed controller to relaunch future headless turns from manifest-owned state even when no live worker process currently exists.

For tmux-backed supported surfaces, the manifest SHALL be the stable authority for later gateway attach and runtime control rather than relying on `gateway_manifest.json`, `attach.json`, or duplicated legacy `backend_state` blobs.

#### Scenario: Start session writes a manifest with normalized session authority
- **WHEN** a developer starts a tmux-backed runtime-owned session
- **THEN** the system writes a session manifest JSON that records backend type, canonical session authority, persisted tmux session identity, and the attach or control fields required for later resume and gateway attach
- **AND THEN** that manifest includes secret-free relaunch posture plus the live agent process pid when one exists as part of runtime-owned session truth

#### Scenario: Native headless manifest remains attachable between turns
- **WHEN** a developer starts or resumes a native headless tmux-backed session
- **AND WHEN** no live headless worker process is currently running because the prior turn already completed
- **THEN** the persisted manifest still contains the authority needed for later gateway attach and future turn relaunch
- **AND THEN** a missing live `agent_pid` does not invalidate that manifest

#### Scenario: Resume tmux-backed session uses manifest authority rather than gateway bootstrap publication
- **WHEN** a developer resumes a tmux-backed session from a persisted session manifest
- **THEN** the system uses the manifest's persisted attach or control authority as the source of truth for resumed control
- **AND THEN** it does not require `gateway_manifest.json` or `attach.json` to remain authoritative for the resumed operation

### Requirement: Pair-managed `houmao_server_rest` sessions are tmux-backed, reserve window 0, and publish stable gateway attachability before live attach
For pair-managed TUI sessions that use `backend = "houmao_server_rest"`, the runtime SHALL create or resume one tmux session per managed agent session.

The runtime SHALL choose and persist one tmux session name per launched session as a stable live-session handle rather than assuming the canonical agent identity is the tmux session name.

The runtime SHALL reserve tmux window `0` as the primary agent surface for that session and SHALL keep the managed agent itself on that primary surface across pair-managed turns.

Later relaunch of that tmux-backed pair-managed session SHALL reuse the same window `0` surface and SHALL NOT allocate a replacement tmux window.

The runtime SHALL publish `AGENTSYS_MANIFEST_PATH=<absolute manifest path>` and `AGENTSYS_AGENT_ID=<authoritative agent id>` into the tmux session environment so that pair-managed current-session discovery can locate the persisted session manifest directly and fall back through shared-registry resolution when needed.

The runtime SHALL reuse the existing runtime-owned gateway capability publication seam to materialize derived gateway bookkeeping, `state.json`, queue or bootstrap assets, and related session-owned gateway artifacts during pair launch or launch registration, before a live gateway is attached.

A pair-managed session SHALL NOT be treated as current-session attach-ready until both that runtime-owned manifest-backed gateway publication and successful managed-agent registration for the same persisted attach authority have completed.

The runtime SHALL allow auxiliary windows to exist later in the same tmux session for gateway or operator diagnostics, but they SHALL NOT displace the agent from window `0` and SHALL NOT redefine the primary pair-managed attach surface.

Runtime-controlled pair-managed turns and pair-managed tmux resolution SHALL continue targeting the agent surface in window `0` even when another tmux window is currently selected in the foreground for observability.

#### Scenario: Pair launch creates a gateway-capable tmux session before live attach
- **WHEN** a developer launches a pair-managed TUI session through `houmao-mgr`
- **THEN** the runtime persists the actual tmux session name for that live session
- **AND THEN** the tmux session environment contains `AGENTSYS_MANIFEST_PATH`
- **AND THEN** the tmux session environment contains `AGENTSYS_AGENT_ID`
- **AND THEN** the gateway capability artifacts are materialized through the shared runtime-owned publication seam
- **AND THEN** window `0` is reserved as the primary agent surface for that session

#### Scenario: Current-session attach is unavailable before matching registration completes
- **WHEN** a delegated pair launch has already published the stable manifest-first discovery inputs into the tmux session
- **AND WHEN** managed-agent registration for that same persisted attach authority has not yet completed successfully
- **THEN** the session is not yet current-session attach-ready
- **AND THEN** pair-managed current-session gateway attach fails closed rather than guessing another authority or alias

#### Scenario: Foreground auxiliary window does not retarget pair-managed execution
- **WHEN** a pair-managed `houmao_server_rest` session has an auxiliary gateway or diagnostics window selected in the foreground
- **AND WHEN** the runtime starts another controlled turn against that managed session
- **THEN** the controlled work still executes on the agent surface in window `0`
- **AND THEN** the runtime does not need to treat the selected auxiliary window as the authoritative agent surface

## ADDED Requirements

### Requirement: Tmux-backed sessions support session-local relaunch without rebuilding the brain home
For tmux-backed managed sessions, the system SHALL expose a relaunch surface that reuses the already-built agent home and does not route through build-time `houmao-mgr agents launch` behavior.

The public operator surface SHALL be `houmao-mgr agents relaunch`, and gateway-managed relaunch SHALL use the same internal runtime relaunch primitive rather than shelling out to the build-time launch command.

For tmux-backed relaunchable sessions, the persisted manifest SHALL carry secret-free `agent_launch_authority` sufficient to describe how the managed agent surface is relaunched, while the owning tmux session environment SHALL carry the effective env values needed at relaunch time.

Tmux-backed relaunch SHALL resolve the target session through the same manifest-first discovery contract used by current-session attach.

Tmux-backed relaunch SHALL always target tmux window `0` for the managed agent surface and SHALL NOT allocate a new tmux window.

The system SHALL NOT require per-agent launcher directories, copied launcher scripts, or copied credentials in shared registry in order to relaunch a tmux-backed managed session.

For native headless sessions, relaunch remains valid between turns even when no live `runtime.agent_pid` is published.

#### Scenario: Current-session relaunch uses tmux session env and existing built home
- **WHEN** a developer runs `houmao-mgr agents relaunch` inside a tmux-backed managed session
- **THEN** the system resolves the session through `AGENTSYS_MANIFEST_PATH` or `AGENTSYS_AGENT_ID`
- **AND THEN** it relaunches the managed agent surface from manifest-owned relaunch posture plus the current tmux session env
- **AND THEN** it does not rebuild the brain home

#### Scenario: Gateway-managed relaunch shares the same runtime primitive
- **WHEN** an attached gateway requests relaunch for a tmux-backed managed session
- **THEN** the gateway uses the same manifest-backed runtime relaunch primitive as `houmao-mgr agents relaunch`
- **AND THEN** it does not fall back to build-time `houmao-mgr agents launch`

#### Scenario: Relaunch reuses window 0 rather than allocating a new window
- **WHEN** the runtime relaunches a tmux-backed managed session
- **THEN** it targets the managed agent surface in window `0`
- **AND THEN** it does not create or search for another tmux window when window `0` has been repurposed by the user

### Requirement: Runtime publishes manifest-first stable discovery pointers and live gateway bindings separately
When the runtime makes a tmux-backed session gateway-capable, it SHALL publish stable manifest-first discovery pointers into the tmux session environment in addition to the existing agent-definition binding.

When a live gateway instance is currently attached, the runtime or gateway lifecycle SHALL also publish live gateway bindings for that running instance.

At minimum, the runtime SHALL publish:

- `AGENTSYS_MANIFEST_PATH`
- `AGENTSYS_AGENT_ID`

When a live gateway instance exists, the system SHALL additionally publish:

- `AGENTSYS_AGENT_GATEWAY_HOST`
- `AGENTSYS_AGENT_GATEWAY_PORT`
- `AGENTSYS_GATEWAY_STATE_PATH`
- `AGENTSYS_GATEWAY_PROTOCOL_VERSION`

The stable tmux discovery pointers SHALL also be the current-session entrypoint for tmux-backed relaunch.

#### Scenario: Session start publishes manifest-first stable discovery pointers
- **WHEN** the runtime starts a gateway-capable tmux-backed session
- **THEN** the tmux session environment contains `AGENTSYS_MANIFEST_PATH` and `AGENTSYS_AGENT_ID`
- **AND THEN** those bindings point to the stable manifest authority or authoritative identity for that session even when no gateway instance is running

#### Scenario: Live gateway attach publishes active gateway bindings
- **WHEN** the runtime or lifecycle command attaches a live gateway instance to a gateway-capable tmux-backed session
- **THEN** the tmux session environment contains `AGENTSYS_AGENT_GATEWAY_HOST`, `AGENTSYS_AGENT_GATEWAY_PORT`, `AGENTSYS_GATEWAY_STATE_PATH`, and `AGENTSYS_GATEWAY_PROTOCOL_VERSION`
- **AND THEN** those bindings point to the currently running gateway instance rather than merely to stable attachability

### Requirement: Native headless tmux-backed sessions reserve window 0 for console output and remain gateway-attachable between turns
For runtime-owned native headless sessions that use tmux as the durable terminal container, the runtime SHALL keep window `0` reserved for the headless agent console surface.

The runtime SHALL publish `AGENTSYS_MANIFEST_PATH=<absolute manifest path>` and `AGENTSYS_AGENT_ID=<authoritative agent id>` into that tmux session so current-session gateway attach can resolve the manifest directly and fall back through shared-registry resolution when needed.

Gateway attach SHALL NOT assume a native headless worker process is currently running. Attach targets the logical persisted session, and the manifest SHALL contain enough authority for later headless turn launch even when `runtime.agent_pid` is empty.

If the runtime launches a same-session gateway surface for a native headless session, that surface SHALL live outside window `0` and SHALL NOT displace the headless console from window `0`.

Any native headless relaunch path SHALL reuse window `0` as the headless console surface and SHALL NOT allocate a replacement tmux window.

#### Scenario: Native headless session reserves window 0 and publishes manifest-first discovery
- **WHEN** a developer launches a native headless tmux-backed session
- **THEN** window `0` is reserved for the headless console surface
- **AND THEN** the tmux session environment contains `AGENTSYS_MANIFEST_PATH`
- **AND THEN** the tmux session environment contains `AGENTSYS_AGENT_ID`

#### Scenario: Native headless attach remains valid after a turn exits
- **WHEN** a native headless turn finishes and its worker process exits
- **AND WHEN** the tmux session and manifest remain live
- **THEN** current-session gateway attach remains valid for that logical session
- **AND THEN** a missing `runtime.agent_pid` does not make the session non-attachable

# Brain Launch Runtime Delta

## ADDED Requirements

### Requirement: Retired Manual Adoption Confers No Runtime Authority

A saved manifest identifying a `joined_tmux` origin SHALL yield a distinct retirement result before Houmao reconstructs runtime authority. Registry records, tmux discovery pointers, runtime-root scans, and derived gateway artifacts SHALL confer no active authority for that session. A selected retired runtime SHALL produce guidance to wind down management with the owning release and use a fresh supported launch.

#### Scenario: Both Adopted Modes Are Retired
- **WHEN** Houmao resolves a previously adopted TUI or headless session through a saved manifest, registry pointer, or current tmux discovery pointer
- **THEN** it recognizes the retired origin regardless of the saved relaunch posture
- **AND THEN** it refuses managed control without changing the manifest, republishing discovery, or trying an alternate source of authority for that session

#### Scenario: Derived Attach State Does Not Restore Ownership
- **WHEN** a retired adopted runtime has saved gateway attach metadata or a live-looking registry record
- **THEN** that metadata confers no authority to attach, admit work, or publish an active endpoint

### Requirement: Native v6 Runtime Authority Remains Valid

Houmao SHALL continue to read and write native session manifests under schema v6. The reader SHALL accept explicit null or omitted adoption fields on native records. Supported native relaunch and headless continuation SHALL continue to use verified durable launch and chat authority.

#### Scenario: Previously Written Native v6 Record Is Resumed
- **WHEN** a valid native v6 manifest supplies null values for `session_origin`, `launch_args`, and `launch_env` in `agent_launch_authority`, or omits them
- **THEN** Houmao can load, resume, and persist that native session with its existing execution owner and generation
- **AND THEN** native TUI handoff and gateway attach remain available through the existing authority checks

#### Scenario: Native Headless Relaunch Continues a Saved Chat
- **WHEN** an operator relaunches a supported native headless session with a qualified latest or exact chat selection
- **THEN** Houmao preserves that selection and uses the existing provider-qualified continuation behavior

### Requirement: Retirement Preserves Manual Execution and Data

Rejecting or discovering a retired adoption SHALL leave its process, tmux surface, discovery pointers, native home, workspace, conversations, memory, and artifacts intact. Lifecycle and cleanup paths SHALL distinguish retirement from missing or malformed authority. A retired record SHALL confer no authorization for recovery or purge.

#### Scenario: Selected Lifecycle and Cleanup Refuse Retired Authority
- **WHEN** an operator selects a retired adopted runtime for stop, relaunch, or session cleanup by a supported identity, manifest, or session-root selector
- **THEN** Houmao reports retirement and performs no provider, tmux, registry, or artifact mutation
- **AND THEN** a degraded primary pane, a stale record, and an explicit registry-purge option do not bypass retirement

#### Scenario: Bulk Cleanup Preserves Retired Runtime Artifacts
- **WHEN** bulk runtime cleanup examines a retired adopted envelope, with or without a registry record
- **THEN** dry-run identifies it as preserved and cleanup leaves its artifacts intact
- **AND THEN** other envelopes remain eligible for their ordinary verified cleanup rules

### Requirement: Runtime Resolves Native Managed Memory Before Session Publication
For tmux-backed managed sessions, the runtime SHALL resolve memory root, memo file, and pages directory before publishing the session as live.

That resolved memory state SHALL be preserved for native managed launch and managed relaunch of an existing runtime-owned tmux-backed session.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

When memory state resolves in the default mode, the runtime SHALL derive the memory root from the selected active overlay and authoritative `agent-id` rather than from `session-id` or runtime workdir.

#### Scenario: Native managed launch persists the overlay-local memory root
- **WHEN** a native tmux-backed managed launch selects overlay `/repo/.houmao` for agent id `researcher-id`
- **THEN** the runtime resolves memory root `/repo/.houmao/memory/agents/researcher-id/`
- **AND THEN** it resolves memo file `/repo/.houmao/memory/agents/researcher-id/houmao-memo.md`
- **AND THEN** it resolves pages directory `/repo/.houmao/memory/agents/researcher-id/pages/`
- **AND THEN** it persists that resolved memory state before publishing the live session

#### Scenario: Relaunch preserves the previously resolved memory paths
- **WHEN** managed agent `researcher` already has manifest-persisted memory root `/repo/.houmao/memory/agents/researcher-id/`
- **AND WHEN** an operator relaunches that managed agent through the supported relaunch surface
- **THEN** the relaunched session reuses the manifest-persisted memory root, memo file, and pages directory
- **AND THEN** relaunch does not derive memory paths from the new session id

## MODIFIED Requirements

### Requirement: Tmux-backed sessions support session-local relaunch without rebuilding the brain home

For tmux-backed managed sessions, the system SHALL expose a relaunch surface that reuses the already-built agent home and does not route through build-time `houmao-mgr agents launch` behavior.

The public operator surface SHALL be `houmao-mgr agents relaunch`, and gateway-managed relaunch SHALL use the same internal runtime relaunch primitive rather than shelling out to the build-time launch command.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The persisted manifest SHALL carry secret-free `agent_launch_authority` describing the relaunch posture. Houmao-started sessions SHALL rebuild the provider environment from durable launch inputs.

Tmux-backed relaunch SHALL resolve the target session through the same manifest-first discovery contract used by current-session attach.

Tmux-backed relaunch SHALL always target tmux window `0` for the managed agent surface and SHALL NOT allocate a new tmux window.

The system SHALL NOT require per-agent launcher directories, copied launcher scripts, or copied credentials in shared registry in order to relaunch a tmux-backed managed session.

For native headless sessions, relaunch remains valid between turns even when no live `runtime.agent_pid` is published.

#### Scenario: Current-session relaunch uses tmux session env and existing built home
- **WHEN** a developer runs `houmao-mgr agents relaunch` inside a Houmao-started tmux-backed managed session
- **THEN** the system discovers the session through the `HOUMAO_MANIFEST_PATH` or `HOUMAO_AGENT_ID` locator published to tmux
- **AND THEN** it relaunches the managed agent surface from manifest-owned posture and durable launch inputs
- **AND THEN** it does not rebuild the brain home

#### Scenario: Gateway-managed relaunch shares the same runtime primitive
- **WHEN** an attached gateway requests relaunch for a tmux-backed managed session
- **THEN** the gateway uses the same manifest-backed runtime relaunch primitive as `houmao-mgr agents relaunch`
- **AND THEN** it does not fall back to build-time `houmao-mgr agents launch`

#### Scenario: Relaunch reuses window 0 rather than allocating a new window
- **WHEN** the runtime relaunches a tmux-backed managed session
- **THEN** it targets the managed agent surface in window `0`
- **AND THEN** it does not create or search for another tmux window when window `0` has been repurposed by the user

### Requirement: Shared launch-policy application is used across raw and runtime-managed launches
The system SHALL apply unattended launch policy through one shared Python launch-policy entrypoint across generated raw launch helpers and maintained runtime-managed session backends.

Generated `launch.sh` helpers SHALL remain shell wrappers that invoke that shared Python entrypoint before the final tool `exec`.

#### Scenario: Raw launch helper uses the shared Python launch-policy entrypoint
- **WHEN** a generated brain `launch.sh` helper launches a brain with `operator_prompt_mode = unattended`
- **THEN** the shell helper invokes the shared Python launch-policy entrypoint before the final tool `exec`
- **AND THEN** raw helper launches resolve and apply the same unattended strategy family as runtime-managed launches

#### Scenario: Runtime-managed sessions use the same local launch-policy engine
- **WHEN** a maintained runtime-managed unattended launch starts through a local managed, headless, or passive-server-owned launch flow
- **THEN** the local runtime resolves and applies the same launch-policy engine before provider startup
- **AND THEN** maintained runtime-managed sessions do not bypass version detection, override handling, or fail-closed unattended checks

### Requirement: Session manifests publish effective agent metadata for runtime queries
Managed runtime publication SHALL record the effective agent metadata and observation bindings needed by supported queries in the session manifest. Queries SHALL use those fields for agent metadata. Live observations SHALL use the runtime authorities identified by the manifest.

#### Scenario: Launch publishes query-ready metadata
- **WHEN** Houmao publishes a managed session after launch or relaunch
- **THEN** its manifest supplies the effective identity, mode, backend, native home and surface, execution binding, and applicable observation and control locators
- **AND THEN** publication keeps credentials and raw provider environment values in their private runtime locations

#### Scenario: Runtime observation is unavailable
- **WHEN** a valid session manifest exists and an observation source cannot provide current evidence
- **THEN** the query preserves the manifest-backed agent details and reports the observation as unavailable or unknown according to the command contract

## REMOVED Requirements

### Requirement: Joined tmux-backed sessions materialize the standard runtime session envelope

**Reason**: Local managed authority now begins with a supported Houmao launch.

**Migration**: Wind down existing Houmao management with the owning release before upgrading. Use a fresh supported managed launch for future work.

### Requirement: Joined tmux-backed sessions persist explicit adopted relaunch posture

**Reason**: Adopted launch options no longer confer lifecycle authority.

**Migration**: Use a supported managed launch with explicit durable launch inputs. Existing adopted manifests and provider conversations are preserved without conversion.

### Requirement: Runtime resolves managed memory pages before session publication

**Reason**: This requirement included memory creation during manual adoption. The replacement requirement retains native launch and relaunch memory.

**Migration**: Create future managed sessions through a supported launch. Existing memo and page files remain in place.

## MODIFIED Requirements

### Requirement: Runtime-owned tmux-backed sessions publish shared-registry discovery records
When the runtime starts or resumes control of a tmux-backed session whose registry launch authority is the runtime, it SHALL publish or refresh a shared-registry record for that live session under the effective shared-registry root's `live_agents/` directory.

The runtime SHALL determine whether it is the launch authority for shared-registry creation from explicit runtime-readable launch metadata associated with that live session or authority record, rather than inferring launch authority from the current registry contents alone.

By default, the effective shared-registry root SHALL be `~/.houmao/registry`.

When `AGENTSYS_GLOBAL_REGISTRY_DIR` is set, the runtime SHALL publish and refresh shared-registry records under that override path instead.

For tmux-backed sessions whose launch authority is the runtime, the published shared-registry record SHALL persist the canonical `AGENTSYS-...` agent identity together with the authoritative `agent_id` and the actual tmux session name for that live session.

When runtime publication code receives an agent name in namespace-free form, it SHALL canonicalize that name to the exact `AGENTSYS-...` form before publishing the shared-registry record.

For a given live tmux-backed session whose launch authority is the runtime, the runtime SHALL persist and reuse the same shared-registry `generation_id` across later refreshes and resume-driven republishes of that same session.

That shared-registry record SHALL coexist with existing tmux session environment discovery pointers and SHALL NOT replace `AGENTSYS_MANIFEST_PATH`, `AGENTSYS_AGENT_DEF_DIR`, or the stable gateway attach pointers already published by the runtime.

The published record SHALL include the secret-free runtime-owned pointers available for that session, including the manifest path, runtime session root, authoritative `agent_id`, actual tmux session name, and any gateway or mailbox pointers that the runtime has already materialized.

For sessions created by another launcher such as `houmao-server`, the runtime SHALL continue publishing the stable tmux, manifest, session-root, and gateway-capability pointers needed for later discovery and attach flows, but it SHALL NOT create or refresh the shared-registry record for that session unless the runtime was also the launcher.

#### Scenario: Direct runtime-owned session start publishes a shared-registry record alongside tmux pointers
- **WHEN** the runtime starts a direct runtime-owned tmux-backed session with canonical identity `AGENTSYS-gpu`
- **THEN** the runtime publishes the normal tmux session environment discovery pointers for that session
- **AND THEN** the runtime also publishes a shared-registry record under `~/.houmao/registry/live_agents/<agent-id>/record.json` for that direct runtime-owned session

#### Scenario: Runtime publication canonicalizes namespace-free agent input
- **WHEN** runtime publication logic receives agent input `gpu` for a tmux-backed session whose launch authority is the runtime
- **THEN** it canonicalizes that input to `AGENTSYS-gpu` before publishing the shared-registry record
- **AND THEN** the published record stores canonical agent name `AGENTSYS-gpu`

#### Scenario: Externally launched session continues pointer publication while deferring registry publication
- **WHEN** the runtime starts or resumes a tmux-backed session that was launched by another authority such as `houmao-server`
- **AND WHEN** the session's launch metadata marks registry creation as external to the runtime
- **THEN** the runtime still publishes the stable manifest, session-root, tmux, and gateway-capability pointers for that session
- **AND THEN** shared-registry publication for that session remains with the external launcher rather than being duplicated by the runtime

### Requirement: Runtime refreshes shared-registry records when runtime-owned publication state changes
When the runtime materializes or refreshes stable gateway capability for a session, attaches or detaches a live gateway, refreshes mailbox bindings, or persists updated runtime-owned session state after prompt or control actions, it SHALL refresh the corresponding shared-registry record for that same logical session when the runtime is the launch authority for registry creation for that session.

When no live gateway is attached, the shared-registry record SHALL continue to publish stable gateway pointers when they exist, but SHALL omit live gateway connect metadata.

When mailbox bindings are available, the shared-registry record SHALL reflect the active mailbox principal id and full mailbox address for that session.

These refreshes SHALL keep the same `generation_id` for the same live session rather than manufacturing a replacement generation on each publication event.

For sessions whose registry launch authority is external to the runtime, the runtime SHALL still materialize or refresh the stable session-root, gateway, and mailbox pointers needed for later publication, but it SHALL NOT independently refresh the shared-registry record for that externally launched session.

#### Scenario: Direct runtime-owned live gateway attach refreshes the shared-registry record
- **WHEN** the runtime attaches a live gateway to a gateway-capable direct runtime-owned session whose launch authority is the runtime
- **THEN** the runtime refreshes the shared-registry record for that session
- **AND THEN** the record publishes the exact live gateway connect metadata for the running listener

#### Scenario: Externally launched gateway attach refreshes pointers for later external publication
- **WHEN** the runtime or gateway layer materializes updated live gateway metadata for a session whose registry launch authority is external to the runtime
- **THEN** the runtime refreshes the stable gateway pointers and other publication inputs for that session
- **AND THEN** the external launcher may consume those refreshed pointers to refresh the shared-registry record for that session without the runtime duplicating publication

#### Scenario: Direct runtime-owned prompt or control action refreshes the registry lease
- **WHEN** the runtime sends a prompt or persists updated state after another runtime-owned control action for a tmux-backed session whose launch authority is the runtime
- **THEN** the runtime refreshes that session's shared-registry record
- **AND THEN** the refreshed record keeps the same `generation_id` while extending the lease for that still-live session

### Requirement: Runtime teardown clears shared-registry discoverability when the runtime performs termination
When the runtime completes authoritative `stop-session` teardown for a tmux-backed session and that session still has a matching shared-registry record, the runtime SHALL remove that record or rewrite it so that shared-registry readers treat it as expired.

Unexpected failure MAY leave stale `live_agents/` directories behind, but runtime-owned graceful teardown SHALL clear discoverability for a session when the runtime is the actor that performed authoritative termination.

Launch authority does not exempt runtime-owned termination from cleanup. If another launcher created the record but the runtime later performs authoritative stop for that same matching session, the runtime SHALL clear or expire the record rather than leaving a live entry behind.

#### Scenario: Direct runtime-owned stop clears runtime-published registry discoverability
- **WHEN** an operator stops a direct runtime-owned tmux-backed session whose registry launch authority is the runtime
- **THEN** the runtime removes or expires that session's shared-registry record
- **AND THEN** later shared-registry readers do not treat that stopped direct runtime-owned session as live

#### Scenario: Runtime stop clears an externally launched record when the runtime performs termination
- **WHEN** an externally launched session is later stopped through runtime-owned authority
- **THEN** the runtime clears the local session and gateway publication pointers it owns for that stopped session
- **AND THEN** shared-registry discoverability for that stopped agent is also cleared by the runtime because the runtime performed the authoritative termination

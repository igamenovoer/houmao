## MODIFIED Requirements

### Requirement: Runtime-owned tmux-backed sessions publish shared-registry discovery records
When the runtime starts or resumes control of a runtime-owned tmux-backed session whose shared-registry publisher is the runtime, it SHALL publish or refresh a shared-registry record for that live session under the effective shared-registry root's `live_agents/` directory.

By default, the effective shared-registry root SHALL be `~/.houmao/registry`.

When `AGENTSYS_GLOBAL_REGISTRY_DIR` is set, the runtime SHALL publish and refresh shared-registry records under that override path instead.

For runtime-owned tmux-backed sessions whose publisher is the runtime, the published shared-registry record SHALL persist the canonical `AGENTSYS-...` agent identity together with the authoritative `agent_id` and the actual tmux session name for that live session.

When runtime publication code receives an agent name in namespace-free form, it SHALL canonicalize that name to the exact `AGENTSYS-...` form before publishing the shared-registry record.

For a given live runtime-owned tmux-backed session whose publisher is the runtime, the runtime SHALL persist and reuse the same shared-registry `generation_id` across later refreshes and resume-driven republishes of that same session.

That shared-registry record SHALL coexist with existing tmux session environment discovery pointers and SHALL NOT replace `AGENTSYS_MANIFEST_PATH`, `AGENTSYS_AGENT_DEF_DIR`, or the stable gateway attach pointers already published by the runtime.

The published record SHALL include the secret-free runtime-owned pointers available for that session, including the manifest path, runtime session root, authoritative `agent_id`, actual tmux session name, and any gateway or mailbox pointers that the runtime has already materialized.

For sessions created or admitted through `houmao-server`-owned authority, the runtime SHALL continue publishing the stable tmux, manifest, session-root, and gateway-capability pointers needed for later discovery and attach flows, but it SHALL NOT be required to remain the shared-registry publisher for that session.

#### Scenario: Direct runtime-owned session start publishes a shared-registry record alongside tmux pointers
- **WHEN** the runtime starts a direct runtime-owned tmux-backed session with canonical identity `AGENTSYS-gpu`
- **THEN** the runtime publishes the normal tmux session environment discovery pointers for that session
- **AND THEN** the runtime also publishes a shared-registry record under `~/.houmao/registry/live_agents/<agent-id>/record.json` for that direct runtime-owned session

#### Scenario: Runtime publication canonicalizes namespace-free agent input
- **WHEN** runtime publication logic receives agent input `gpu` for a tmux-backed session whose publisher is the runtime
- **THEN** it canonicalizes that input to `AGENTSYS-gpu` before publishing the shared-registry record
- **AND THEN** the published record stores canonical agent name `AGENTSYS-gpu`

#### Scenario: Server-managed session continues pointer publication while deferring registry publication
- **WHEN** the runtime starts or resumes a tmux-backed session that has been created or admitted through `houmao-server`-owned authority
- **THEN** the runtime still publishes the stable manifest, session-root, tmux, and gateway-capability pointers for that session
- **AND THEN** shared-registry publication for that session is allowed to be delegated to `houmao-server` rather than remaining owned by the runtime

### Requirement: Runtime refreshes shared-registry records when runtime-owned publication state changes
When the runtime materializes or refreshes stable gateway capability for a session, attaches or detaches a live gateway, refreshes mailbox bindings, or persists updated runtime-owned session state after prompt or control actions, it SHALL refresh the corresponding shared-registry record for that same logical session when the runtime is the selected shared-registry publisher for that session.

When no live gateway is attached, the shared-registry record SHALL continue to publish stable gateway pointers when they exist, but SHALL omit live gateway connect metadata.

When mailbox bindings are available, the shared-registry record SHALL reflect the active mailbox principal id and full mailbox address for that session.

These refreshes SHALL keep the same `generation_id` for the same live session rather than manufacturing a replacement generation on each publication event.

For sessions whose shared-registry publisher is `houmao-server`, the runtime SHALL still materialize or refresh the stable session-root, gateway, and mailbox pointers needed for later publication, but it SHALL NOT be required to independently refresh the shared-registry record for that server-managed session.

#### Scenario: Direct runtime-owned live gateway attach refreshes the shared-registry record
- **WHEN** the runtime attaches a live gateway to a gateway-capable direct runtime-owned session whose publisher is the runtime
- **THEN** the runtime refreshes the shared-registry record for that session
- **AND THEN** the record publishes the exact live gateway connect metadata for the running listener

#### Scenario: Server-managed gateway attach refreshes pointers for later server publication
- **WHEN** the runtime or gateway layer materializes updated live gateway metadata for a session whose shared-registry publisher is `houmao-server`
- **THEN** the runtime refreshes the stable gateway pointers and other publication inputs for that session
- **AND THEN** `houmao-server` may consume those refreshed pointers to republish the shared-registry record for that server-managed session

#### Scenario: Direct runtime-owned prompt or control action refreshes the registry lease
- **WHEN** the runtime sends a prompt or persists updated state after another runtime-owned control action for a tmux-backed session whose publisher is the runtime
- **THEN** the runtime refreshes that session's shared-registry record
- **AND THEN** the refreshed record keeps the same `generation_id` while extending the lease for that still-live session

### Requirement: Runtime-owned teardown clears shared-registry discoverability for stopped sessions
When the runtime completes authoritative `stop-session` teardown for a runtime-owned tmux-backed session whose shared-registry publisher is the runtime and that session has a shared-registry record, the runtime SHALL remove that record or rewrite it so that shared-registry readers treat it as expired.

Unexpected failure MAY leave stale `live_agents/` directories behind, but runtime-owned graceful teardown SHALL clear discoverability for a session when the runtime is the selected shared-registry publisher for that session.

When the stopped session's shared-registry publisher is `houmao-server`, the runtime SHALL clear its local session and gateway publication state for that stopped session but SHALL leave shared-registry removal or expiry to the server-owned stop authority for that server-managed agent.

#### Scenario: Direct runtime-owned stop clears runtime-published registry discoverability
- **WHEN** an operator stops a direct runtime-owned tmux-backed session whose shared-registry publisher is the runtime
- **THEN** the runtime removes or expires that session's shared-registry record
- **AND THEN** later shared-registry readers do not treat that stopped direct runtime-owned session as live

#### Scenario: Server-managed stop leaves registry removal to `houmao-server`
- **WHEN** a server-managed session is stopped through server-owned authority and the runtime participates only in local teardown for that session
- **THEN** the runtime clears the local session and gateway publication pointers it owns for that stopped session
- **AND THEN** shared-registry discoverability for that server-managed agent is cleared by `houmao-server` rather than by a competing runtime publisher

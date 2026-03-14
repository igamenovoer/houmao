## ADDED Requirements

### Requirement: Runtime-owned tmux-backed sessions publish shared-registry discovery records
When the runtime starts or resumes control of a runtime-owned tmux-backed session, it SHALL publish or refresh a shared-registry record for that live session under the effective shared-registry root's `live_agents/` directory.

By default, the effective shared-registry root SHALL be `~/.houmao/registry`.

When `AGENTSYS_GLOBAL_REGISTRY_DIR` is set, the runtime SHALL publish and refresh shared-registry records under that override path instead.

For runtime-owned tmux-backed sessions in v1, the published shared-registry agent name SHALL default to the canonical `AGENTSYS-...` agent identity used for the tmux session.

When runtime publication code receives an agent name in namespace-free form, it SHALL canonicalize that name to the exact `AGENTSYS-...` form before publishing the shared-registry record.

For a given live runtime-owned tmux-backed session, the runtime SHALL persist and reuse the same shared-registry `generation_id` across later refreshes and resume-driven republishes of that same session.

That shared-registry record SHALL coexist with existing tmux session environment discovery pointers and SHALL NOT replace `AGENTSYS_MANIFEST_PATH`, `AGENTSYS_AGENT_DEF_DIR`, or the stable gateway attach pointers already published by the runtime.

The published record SHALL include the secret-free runtime-owned pointers available for that session, including the manifest path, runtime session root, tmux session name, and any gateway or mailbox pointers that the runtime has already materialized.

#### Scenario: Session start publishes a shared-registry record alongside tmux pointers
- **WHEN** the runtime starts a runtime-owned tmux-backed session with canonical identity `AGENTSYS-gpu`
- **THEN** the runtime publishes the normal tmux session environment discovery pointers for that session
- **AND THEN** the runtime also publishes a shared-registry record under `~/.houmao/registry/live_agents/` keyed by `AGENTSYS-gpu`

#### Scenario: Runtime publication canonicalizes namespace-free agent input
- **WHEN** runtime publication logic receives agent input `gpu` for a tmux-backed session
- **THEN** it canonicalizes that input to `AGENTSYS-gpu` before deriving the shared-registry key
- **AND THEN** the published record stores canonical agent name `AGENTSYS-gpu`

#### Scenario: CI override redirects runtime publication
- **WHEN** the runtime starts a runtime-owned tmux-backed session
- **AND WHEN** `AGENTSYS_GLOBAL_REGISTRY_DIR` is set for that process
- **THEN** the runtime publishes the shared-registry record for that session under the override path
- **AND THEN** the runtime does not publish that record under the default home-relative root for that process

#### Scenario: Resume refreshes the shared-registry record from persisted session state
- **WHEN** the runtime resumes control of a runtime-owned tmux-backed session whose manifest and gateway metadata can be determined
- **THEN** the runtime refreshes that session's shared-registry record
- **AND THEN** later discovery flows can locate the same live session without depending on a shared runtime-root layout

#### Scenario: Resume reuses the same shared-registry generation for the same live session
- **WHEN** the runtime resumes control of a runtime-owned tmux-backed session that already published a shared-registry record generation
- **THEN** the resumed publication reuses that same `generation_id`
- **AND THEN** resume does not create a replacement generation for the same still-live session

### Requirement: Runtime refreshes shared-registry records when runtime-owned publication state changes
When the runtime materializes or refreshes stable gateway capability for a session, attaches or detaches a live gateway, refreshes mailbox bindings, or persists updated runtime-owned session state after prompt or control actions, it SHALL refresh the corresponding shared-registry record for that same logical session.

When no live gateway is attached, the shared-registry record SHALL continue to publish stable gateway pointers when they exist, but SHALL omit live gateway connect metadata.

When mailbox bindings are available, the shared-registry record SHALL reflect the active mailbox principal id and full mailbox address for that session.

These refreshes SHALL keep the same `generation_id` for the same live session rather than manufacturing a replacement generation on each publication event.

#### Scenario: Live gateway attach adds connect metadata to the shared-registry record
- **WHEN** the runtime attaches a live gateway to a gateway-capable runtime-owned session
- **THEN** the runtime refreshes the shared-registry record for that session
- **AND THEN** the record publishes the exact live gateway connect metadata for the running listener

#### Scenario: Gateway detach preserves stable pointers but removes live connect metadata
- **WHEN** the runtime detaches a live gateway from a gateway-capable runtime-owned session
- **THEN** the runtime refreshes the shared-registry record for that session
- **AND THEN** the record keeps stable gateway pointers such as the attach-contract path when available
- **AND THEN** the record no longer advertises live gateway connect metadata

#### Scenario: Mailbox binding refresh updates mailbox identity in the shared-registry record
- **WHEN** the runtime refreshes mailbox bindings for a mailbox-enabled session
- **THEN** the runtime refreshes the shared-registry record for that session
- **AND THEN** the record reflects the active mailbox principal id and full mailbox address for the refreshed binding

#### Scenario: Prompt or control action refreshes the shared-registry lease for the same live session
- **WHEN** the runtime sends a prompt or persists updated state after another runtime-owned control action for a tmux-backed session that already published a shared-registry record
- **THEN** the runtime refreshes that session's shared-registry record
- **AND THEN** the refreshed record keeps the same `generation_id` while extending the lease for that still-live session

### Requirement: Runtime-owned teardown clears shared-registry discoverability for stopped sessions
When the runtime completes authoritative `stop-session` teardown for a runtime-owned tmux-backed session that has a shared-registry record, the runtime SHALL remove that record or rewrite it so that shared-registry readers treat it as expired.

Unexpected failure MAY leave stale `live_agents/` directories behind, but runtime-owned graceful teardown SHALL clear discoverability for the stopped session.

#### Scenario: Stop-session clears shared-registry discoverability
- **WHEN** an operator stops a runtime-owned tmux-backed session that previously published a shared-registry record
- **THEN** the runtime removes the record or expires it as part of teardown
- **AND THEN** later shared-registry readers do not treat that stopped session as live

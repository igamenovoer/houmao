## ADDED Requirements

### Requirement: Retired joined-session records convey no live presence
A record for a retired `joined_tmux` manifest SHALL confer no active discovery, live gateway coordinates, or runtime control even while its lease is fresh. Known address and durable mail membership MAY remain available through their independent read and delivery contracts.

#### Scenario: A retired record is still published
- **WHEN** a fresh registry record points to a retired joined-session manifest
- **THEN** the active manager list and passive live discovery omit that runtime
- **AND THEN** selected runtime control refuses the retired authority without substituting another target
- **AND THEN** discovery does not modify the record or the runtime's files

#### Scenario: A known address outlives retired presence
- **WHEN** a caller resolves a known address or uses a valid durable mail membership for a retired joined session
- **THEN** known-address resolution may identify the agent without live gateway coordinates
- **AND THEN** mail delivery continues under the mailbox authority's existing rules

### Requirement: Supported managed presence identifies the run mode and native surface

A current local managed presence record SHALL identify the selected tool, run mode, concrete backend, managed generation, and optional native human surface consistently with the current manifest. Public Web location metadata SHALL contain only a token-free origin and the bound session identity. A service control socket, stdio handle, or supervisor pane SHALL confer no human interface.

#### Scenario: Web presence survives gateway detach

- **WHEN** an operator detaches the gateway from a live owned Web host
- **THEN** the record retains its safe browser reference and mode and omits any discarded gateway endpoint

#### Scenario: A managed terminal publishes its identity

- **WHEN** a supported Houmao launch starts a managed TUI with verified terminal authority
- **THEN** its new record reports tui and the verified terminal surface

#### Scenario: A record disagrees with the manifest

- **WHEN** a service record claims a terminal UI or names a backend belonging to another mode
- **THEN** the reader reports unusable authority before routing an operation

## MODIFIED Requirements

### Requirement: Shared registry publication is atomic and lease-based

The system SHALL publish shared-registry updates by writing a temporary file in the target live-agent directory and atomically replacing `record.json`.

Published records whose publication path uses a bounded lease SHALL continue to be treated as stale after their lease expires.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Published records for currently supported tmux-backed live agents SHALL use a dedicated long finite sentinel lease window so their discoverability does not expire at the ordinary 24-hour or 30-day boundary.

This change SHALL NOT introduce a new non-tmux registry publication contract.

Readers SHALL treat lease freshness rather than directory existence as the liveness signal for a published live agent.

If a publisher stops unexpectedly, the system MAY leave the live-agent directory behind, but readers SHALL treat records whose lease has expired as stale.

For tmux-backed live agents, stale removal SHALL rely on explicit teardown or cleanup-time local tmux liveness classification rather than on the ordinary 24-hour lease boundary.

Passive server discovery SHALL remain a probe-backed index that includes tmux-backed records only when they are lease-fresh and the owning tmux session is live on the local host.

If a publisher attempts to refresh or replace a live record for the same authoritative `agent_id` but a different fresh `generation_id`, the system SHALL reject that publication or otherwise prevent both generations from being treated as the same live identity concurrently.

The registry SHALL allow different fresh live records to share the same `agent_name` so long as they carry different authoritative `agent_id` values.

V1 SHALL tolerate the narrow compare-then-replace race window created by lock-free filesystem publication, but a publisher that later observes a different fresh `generation_id` owning the same authoritative `agent_id` SHALL surface that conflict and stand down from claiming shared-registry ownership for that id.

#### Scenario: Readers ignore an expired bounded-lease record

- **WHEN** a shared-registry record that uses bounded lease semantics still exists on disk
- **AND WHEN** its lease has expired
- **THEN** shared-registry resolution treats that record as stale rather than live
- **AND THEN** the lingering live-agent directory does not by itself make the agent discoverable

#### Scenario: Tmux-backed record remains discoverable past the old lease boundaries

- **WHEN** a tmux-backed live agent remains bound to a still-live owning tmux session
- **AND WHEN** more than 24 hours and more than 30 days have elapsed since the last registry publication
- **THEN** the published record still remains lease-fresh for ordinary discovery
- **AND THEN** local list and resolve flows continue to treat that tmux-backed agent as discoverable

#### Scenario: Passive discovery preserves its tmux liveness filter
- **WHEN** a tmux-backed live-agent record remains lease-fresh under the sentinel tmux-backed lease rule
- **AND WHEN** passive server discovery scans the shared registry
- **AND WHEN** the owning tmux session is absent on the local host
- **THEN** passive discovery excludes that record from its probe-backed index
- **AND THEN** ordinary local registry lookup semantics are unchanged by that passive-discovery exclusion

#### Scenario: Cleanup still removes a dead tmux-backed record despite the sentinel lease

- **WHEN** a tmux-backed live-agent directory exists under `live_agents/`
- **AND WHEN** its `record.json` remains lease-fresh under the sentinel tmux-backed lease rule
- **AND WHEN** the owning tmux session is absent on the local host during stale-registry cleanup
- **THEN** the cleanup tool classifies that directory as stale
- **AND THEN** the tmux-backed record is removable even though the ordinary lease window has not expired

#### Scenario: Same friendly name may appear on different live identities

- **WHEN** two fresh live registry records share `agent_name = "gpu"`
- **AND WHEN** those records carry different authoritative ids such as `abc123` and `def456`
- **THEN** the registry allows both records to remain published concurrently
- **AND THEN** callers must disambiguate by `agent_id` or another explicit metadata surface

#### Scenario: Fresh duplicate publication for one authoritative agent id is rejected

- **WHEN** one publisher attempts to publish `agent_id=abc123`
- **AND WHEN** a different fresh registry record already exists for `agent_id=abc123` with a different `generation_id`
- **THEN** the system rejects the second publication or forces that publisher to stand down
- **AND THEN** readers are not presented with two simultaneously live records for the same authoritative identity

### Requirement: Remote descriptors grant no credentials or lifecycle rights

Discovery SHALL treat endpoint metadata as a locator. Protected credential selection, execution delegation, and lifecycle control SHALL require their own authority. Communication-only imports SHALL retain their existing scope. Foreign paths and loopback addresses SHALL remain owner-context metadata. Changed advertised target or endpoint bindings SHALL require explicit client rebinding before credential-bearing access.

#### Scenario: Communication import contains an authenticated gateway URL

- **WHEN** a communication-only import references a gateway with public input enabled
- **THEN** it can locate and call the available public operations
- **AND** each protected operation requires a current grant for the selected domain, resource, and action, and execution delegation requires its existing authority

#### Scenario: Registry descriptor is replaced with another origin

- **WHEN** discovery returns a different origin or base path for an existing credential-bearing client binding
- **THEN** the existing credential is not automatically attached to that replacement endpoint

#### Scenario: Owner loopback port also exists on the caller host

- **WHEN** a remote execution record contains owner-local loopback listener coordinates
- **THEN** remote discovery does not authorize connecting to the same port on the caller host as a substitute

## REMOVED Requirements

### Requirement: Managed presence identifies the run mode and native surface

**Reason:** The joined terminal publication scenario is retired.

**Migration:** Supported Houmao launches publish the verified mode and native surface under the replacement requirement.

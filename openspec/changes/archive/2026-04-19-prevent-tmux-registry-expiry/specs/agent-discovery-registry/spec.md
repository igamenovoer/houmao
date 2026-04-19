## MODIFIED Requirements

### Requirement: Shared registry publication is atomic and lease-based

The system SHALL publish shared-registry updates by writing a temporary file in the target live-agent directory and atomically replacing `record.json`.

Published records whose publication path uses a bounded lease SHALL continue to be treated as stale after their lease expires.

Published records for currently supported tmux-backed live agents SHALL use a dedicated long finite sentinel lease window so their discoverability does not expire at the ordinary 24-hour boundary or the existing 30-day joined-session boundary.

The tmux-backed sentinel lease SHALL apply to all current tmux-backed registry publications, including joined tmux sessions.

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

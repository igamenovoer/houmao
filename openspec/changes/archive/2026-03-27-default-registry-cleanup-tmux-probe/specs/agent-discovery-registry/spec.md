## MODIFIED Requirements

### Requirement: The system provides a minimal operator-facing cleanup entrypoint for stale `live_agents/` directories
The system SHALL provide a local operator-facing cleanup entrypoint at `houmao-mgr admin cleanup registry` that classifies stale directories under `~/.houmao/registry/live_agents/` or the effective override root.

That tooling SHALL remove directories whose `record.json` is missing, malformed, or expired beyond a bounded grace period.

For tmux-backed records, that tooling SHALL perform a local tmux liveness probe by default. When a record is still lease-fresh but its tmux authority is absent on the local host, the cleanup tool SHALL classify that record as stale.

That tooling SHALL accept `--no-tmux-check`. When tmux checking is disabled, lease-fresh records SHALL remain preserved unless they are otherwise removable by malformed-state or expiry classification.

That tooling SHALL accept `--dry-run`. In dry-run mode, it SHALL classify removable, preserved, and blocked directories using the same rules as ordinary execution, but it SHALL NOT delete anything.

#### Scenario: Cleanup tool removes an expired live-agent directory
- **WHEN** a directory exists under `live_agents/`
- **AND WHEN** its `record.json` lease is expired beyond the cleanup grace period
- **AND WHEN** an operator invokes the cleanup entrypoint
- **THEN** the cleanup tool removes that directory
- **AND THEN** later directory listings better reflect only currently live published agents

#### Scenario: Default tmux probing removes a lease-fresh dead tmux-backed record
- **WHEN** a directory exists under `live_agents/`
- **AND WHEN** its `record.json` is valid and lease-fresh
- **AND WHEN** the record identifies a tmux-backed live authority whose tmux session is absent on the local host
- **AND WHEN** an operator invokes the cleanup entrypoint without `--no-tmux-check`
- **THEN** the cleanup tool classifies that directory as stale
- **AND THEN** the cleanup result reports local tmux liveness failure rather than lease expiry as the removal reason

#### Scenario: Default tmux probing preserves a lease-fresh live tmux-backed record
- **WHEN** a directory exists under `live_agents/`
- **AND WHEN** its `record.json` is valid and lease-fresh
- **AND WHEN** the record identifies a tmux-backed live authority whose tmux session exists on the local host
- **AND WHEN** an operator invokes the cleanup entrypoint without `--no-tmux-check`
- **THEN** the cleanup tool leaves that directory in place
- **AND THEN** the cleanup result reports that local tmux probing confirmed the owning session

#### Scenario: No-tmux-check flag preserves a lease-fresh live-agent directory without tmux probing
- **WHEN** a directory exists under `live_agents/`
- **AND WHEN** its `record.json` is valid and lease-fresh
- **AND WHEN** the operator invokes the cleanup entrypoint with `--no-tmux-check`
- **THEN** the cleanup tool leaves that directory in place unless another stale classification applies
- **AND THEN** the cleanup result distinguishes skipped tmux checking from probe-confirmed liveness

#### Scenario: Dry-run reports tmux-probe stale registry candidates without deleting them
- **WHEN** a directory exists under `live_agents/`
- **AND WHEN** its `record.json` is valid and lease-fresh
- **AND WHEN** the record identifies a tmux-backed live authority whose tmux session is absent on the local host
- **AND WHEN** an operator runs `houmao-mgr admin cleanup registry --dry-run`
- **THEN** the cleanup result reports that directory as removable
- **AND THEN** the directory still exists after the dry-run finishes

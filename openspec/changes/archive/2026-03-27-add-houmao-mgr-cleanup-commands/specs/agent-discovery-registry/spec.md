## MODIFIED Requirements

### Requirement: The system provides a minimal operator-facing cleanup entrypoint for stale `live_agents/` directories
The system SHALL provide a local operator-facing cleanup entrypoint at `houmao-mgr admin cleanup registry` that classifies stale directories under `~/.houmao/registry/live_agents/` or the effective override root.

That tooling SHALL remove directories whose `record.json` is missing, malformed, or expired beyond a bounded grace period.

That tooling SHALL accept `--dry-run`. In dry-run mode, it SHALL classify removable, preserved, and blocked directories using the same rules as ordinary execution, but it SHALL NOT delete anything.

That tooling MAY also accept an explicit local liveness-probing mode for tmux-backed records. When liveness probing is not requested, lease-fresh records SHALL remain preserved even if they may later prove locally dead. When liveness probing is requested and the record's tmux authority is absent on the local host, the cleanup tool MAY classify that record as stale even if its lease has not yet expired.

#### Scenario: Cleanup tool removes an expired live-agent directory
- **WHEN** a directory exists under `live_agents/`
- **AND WHEN** its `record.json` lease is expired beyond the cleanup grace period
- **AND WHEN** an operator invokes the cleanup entrypoint
- **THEN** the cleanup tool removes that directory
- **AND THEN** later directory listings better reflect only currently live published agents

#### Scenario: Cleanup tool preserves a lease-fresh live-agent directory without liveness probing
- **WHEN** a directory exists under `live_agents/`
- **AND WHEN** its `record.json` is valid and lease-fresh
- **AND WHEN** the operator does not request local liveness probing
- **THEN** the cleanup tool leaves that directory in place
- **AND THEN** the currently running published agent remains discoverable

#### Scenario: Dry-run reports stale registry candidates without deleting them
- **WHEN** a directory exists under `live_agents/`
- **AND WHEN** its `record.json` is missing, malformed, or expired beyond the cleanup grace period
- **AND WHEN** an operator runs `houmao-mgr admin cleanup registry --dry-run`
- **THEN** the cleanup result reports that directory as removable
- **AND THEN** the directory still exists after the dry-run finishes

#### Scenario: Optional liveness probing can classify a fresh dead tmux-backed record as stale
- **WHEN** a directory exists under `live_agents/`
- **AND WHEN** its `record.json` is still lease-fresh
- **AND WHEN** the record identifies a tmux-backed live authority whose tmux session is absent on the local host
- **AND WHEN** an operator invokes the cleanup entrypoint with local liveness probing enabled
- **THEN** the cleanup tool may classify that directory as stale
- **AND THEN** the cleanup result distinguishes that dead-session classification from the lease-only preserved case

## ADDED Requirements

### Requirement: Live tracked TUI sessions retain bounded recent snapshot history
For supported tmux-backed TUI sessions whose active control plane uses the shared TUI tracking core, the system SHALL retain recent tracked snapshots in memory in addition to the current-state snapshot and any recent transition summaries.

That snapshot-history buffer SHALL be bounded to the most recent 1000 snapshots per tracked session.

The snapshot-history buffer SHALL be implementation-owned live state rather than a durable artifact and SHALL disappear when the active tracking owner forgets or loses that session.

#### Scenario: Tracker records recent snapshots for a live tracked session
- **WHEN** the active control plane for a supported tracked TUI session publishes successive tracked snapshots
- **THEN** the shared tracking core retains those recent snapshots in memory for that session
- **AND THEN** later gateway-owned history reads can inspect that recent snapshot buffer without replaying durable artifacts

#### Scenario: Snapshot buffer evicts the oldest entries at the retention cap
- **WHEN** more than 1000 tracked snapshots have been published for one tracked TUI session
- **THEN** the shared tracking core retains only the 1000 most recent snapshots for that session
- **AND THEN** the oldest snapshots are evicted from the in-memory buffer

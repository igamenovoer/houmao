## MODIFIED Requirements

### Requirement: Passive server discovers agents by scanning the shared registry with tmux liveness verification
The passive server SHALL maintain a `RegistryDiscoveryService` that periodically scans the shared managed-agent registry under the configured `PassiveServerConfig.registry_root`.

On each scan cycle, the discovery service SHALL:
1. Enumerate all `record.json` files under `{registry_root}/live_agents/*/`.
2. Load and validate each record against the managed-agent registry record schema.
3. Discard records that are malformed, schema-invalid, or lease-expired.
4. For each fresh record with `terminal.kind == "tmux"`, verify that the tmux session identified by `terminal.session_name` exists as a live tmux session.
5. Evict agents whose tmux session no longer exists, even if the registry record's lease is still fresh.
6. Build an in-memory `DiscoveredAgentIndex` from the remaining validated, fresh, tmux-live records.

The scan cycle SHALL run at a configurable interval (default 5 seconds).

The discovery service SHALL start during server startup and stop during server shutdown.

The discovery service SHALL NOT require a Houmao project overlay to resolve its registry root.

#### Scenario: Discovery finds a fresh agent with a live tmux session
- **WHEN** the configured shared registry contains a fresh `record.json` for agent_id `abc123`
- **AND WHEN** the record's `terminal.session_name` identifies a live tmux session
- **THEN** the agent appears in the discovered agent index

#### Scenario: Discovery excludes an agent with an expired lease
- **WHEN** the configured shared registry contains a `record.json` for agent_id `abc123` whose lease has expired
- **THEN** the agent does not appear in the discovered agent index

#### Scenario: Discovery excludes an agent whose tmux session is dead
- **WHEN** the configured shared registry contains a fresh `record.json` for agent_id `abc123`
- **AND WHEN** the record's `terminal.session_name` does not match any live tmux session
- **THEN** the agent does not appear in the discovered agent index

#### Scenario: Discovery excludes malformed registry records
- **WHEN** the configured shared registry contains a `record.json` that fails schema validation
- **THEN** the agent does not appear in the discovered agent index
- **AND THEN** the discovery service does not crash

#### Scenario: Discovery rebuilds the index on server startup
- **WHEN** the passive server starts
- **AND WHEN** the configured shared registry contains fresh records with live tmux sessions
- **THEN** the agents appear in the discovered agent index after the first scan cycle completes

#### Scenario: Discovery uses configured registry root
- **WHEN** the passive server is configured with a custom `registry_root`
- **AND WHEN** that registry root contains a fresh record for a live tmux-backed agent
- **THEN** the agent appears in the discovered agent index
- **AND THEN** records in the default registry root do not affect that server's discovery index

#### Scenario: Later agents appear without server registration
- **WHEN** the passive server is already running
- **AND WHEN** a Houmao-managed agent later publishes a fresh record into the configured shared registry
- **AND WHEN** the record's tmux session is live
- **THEN** the agent appears in the discovered agent index after a subsequent scan cycle

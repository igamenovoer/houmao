# Capability: Passive Server Agent Discovery

## Purpose

Defines how the passive server discovers running agents by scanning the shared registry with tmux liveness verification, and exposes them through REST API endpoints for listing and resolution.
## Requirements
### Requirement: Passive server discovers agents by scanning the shared registry with tmux liveness verification
The passive server SHALL maintain a `RegistryDiscoveryService` that periodically scans the shared `LiveAgentRegistryRecordV2` registry under the configured registry root.

On each scan cycle, the discovery service SHALL:
1. Enumerate all `record.json` files under `{registry_root}/live_agents/*/`.
2. Load and validate each record against the `LiveAgentRegistryRecordV2` schema.
3. Discard records that are malformed, schema-invalid, or lease-expired.
4. For each fresh record with `terminal.kind == "tmux"`, verify that the tmux session identified by `terminal.session_name` exists as a live tmux session.
5. Evict agents whose tmux session no longer exists, even if the registry record's lease is still fresh.
6. Build an in-memory `DiscoveredAgentIndex` from the remaining validated, fresh, tmux-live records.

The scan cycle SHALL run at a configurable interval (default 5 seconds).

The discovery service SHALL start during server startup and stop during server shutdown.

#### Scenario: Discovery finds a fresh agent with a live tmux session
- **WHEN** the shared registry contains a fresh `record.json` for agent_id `abc123`
- **AND WHEN** the record's `terminal.session_name` identifies a live tmux session
- **THEN** the agent appears in the discovered agent index

#### Scenario: Discovery excludes an agent with an expired lease
- **WHEN** the shared registry contains a `record.json` for agent_id `abc123` whose lease has expired
- **THEN** the agent does not appear in the discovered agent index

#### Scenario: Discovery excludes an agent whose tmux session is dead
- **WHEN** the shared registry contains a fresh `record.json` for agent_id `abc123`
- **AND WHEN** the record's `terminal.session_name` does not match any live tmux session
- **THEN** the agent does not appear in the discovered agent index

#### Scenario: Discovery excludes malformed registry records
- **WHEN** the shared registry contains a `record.json` that fails schema validation
- **THEN** the agent does not appear in the discovered agent index
- **AND THEN** the discovery service does not crash

#### Scenario: Discovery rebuilds the index on server startup
- **WHEN** the passive server starts
- **AND WHEN** the shared registry contains fresh records with live tmux sessions
- **THEN** the agents appear in the discovered agent index after the first scan cycle completes

### Requirement: Passive server does not modify registry records during discovery
The passive server SHALL treat the shared registry as read-only for the purpose of agent discovery.

The discovery service SHALL NOT publish, refresh, or remove registry records. It SHALL NOT perform stale-record cleanup.

Registry publication and cleanup remain the responsibility of the launching authority and `houmao-mgr` respectively.

#### Scenario: Discovery does not remove a stale registry record
- **WHEN** the shared registry contains an expired `record.json` for agent_id `abc123`
- **AND WHEN** the passive server's discovery service runs a scan cycle
- **THEN** the `record.json` file still exists on disk after the scan
- **AND THEN** the agent is simply excluded from the in-memory index

### Requirement: Passive server provides an agent listing endpoint
The passive server SHALL expose `GET /houmao/agents` returning a JSON payload with a list of discovered agents.

Each agent entry SHALL include at minimum:
- `agent_id` — the authoritative agent identity
- `agent_name` — the canonical agent name
- `generation_id` — the stable-per-session generation identifier
- `tool` — the agent's tool (from the registry record's `identity.tool`)
- `backend` — the agent's backend (from the registry record's `identity.backend`)
- `tmux_session_name` — the live tmux session handle (from `terminal.session_name`)
- `manifest_path` — path to the session manifest (from `runtime.manifest_path`)
- `session_root` — the session root directory (from `runtime.session_root`)
- `has_gateway` — boolean indicating whether a live gateway is attached
- `has_mailbox` — boolean indicating whether mailbox bindings are present
- `published_at` — the record's publication timestamp
- `lease_expires_at` — the record's lease expiry timestamp

The response SHALL NOT include CAO-era fields such as `tracked_agent_id`, `terminal_id`, or `transport`.

The list SHALL be sorted by `agent_name` (ascending).

#### Scenario: Agent listing returns all discovered agents
- **WHEN** the discovery index contains agents `abc123` (name `AGENTSYS-alpha`) and `def456` (name `AGENTSYS-beta`)
- **AND WHEN** a caller sends `GET /houmao/agents`
- **THEN** the response status code is 200
- **AND THEN** the response body contains two agent entries sorted by agent_name

#### Scenario: Agent listing returns an empty list when no agents are discovered
- **WHEN** the discovery index is empty
- **AND WHEN** a caller sends `GET /houmao/agents`
- **THEN** the response status code is 200
- **AND THEN** the response body contains an empty agents list

### Requirement: Passive server provides a single-agent resolution endpoint
The passive server SHALL expose `GET /houmao/agents/{agent_ref}` that resolves one agent by `agent_id` or `agent_name`.

The `{agent_ref}` path parameter SHALL be interpreted as follows:
1. First, attempt direct lookup by `agent_id` in the discovery index.
2. If no match, canonicalize the input as an agent name by applying `HOUMAO-` prefix normalization and search the index for agents matching that canonical name.
3. If exactly one match is found, return it.
4. If no match is found, return 404.
5. If the name matches multiple agents, return 409 Conflict with a diagnostic message listing the ambiguous agent IDs.

#### Scenario: Resolution by agent_name returns a unique HOUMAO match
- **WHEN** the discovery index contains exactly one agent with name `HOUMAO-alpha`
- **AND WHEN** a caller sends `GET /houmao/agents/alpha`
- **THEN** the response status code is 200
- **AND THEN** the response body contains the agent summary for the matching agent

#### Scenario: Resolution by canonical HOUMAO agent_name is accepted
- **WHEN** the discovery index contains exactly one agent with name `HOUMAO-alpha`
- **AND WHEN** a caller sends `GET /houmao/agents/HOUMAO-alpha`
- **THEN** the response status code is 200
- **AND THEN** the response body contains the agent summary for the matching agent

### Requirement: Discovery service configuration is part of PassiveServerConfig
The `PassiveServerConfig` model SHALL include a `discovery_poll_interval_seconds` field (float, default 5.0) that controls the interval between registry scan cycles.

The configuration field SHALL be validated to be a positive number.

#### Scenario: Default poll interval is 5 seconds
- **WHEN** a `PassiveServerConfig` is created with no explicit poll interval
- **THEN** `discovery_poll_interval_seconds` is 5.0

#### Scenario: Custom poll interval is accepted
- **WHEN** a `PassiveServerConfig` is created with `discovery_poll_interval_seconds=2.0`
- **THEN** `discovery_poll_interval_seconds` is 2.0

#### Scenario: Non-positive poll interval is rejected
- **WHEN** a `PassiveServerConfig` is created with `discovery_poll_interval_seconds=0.0`
- **THEN** validation fails

### Requirement: Discovery service tolerates tmux server unavailability
When the tmux server is not running or not reachable, the discovery service SHALL treat all tmux liveness checks as failed (no live sessions).

The discovery service SHALL log a warning when the tmux server is unreachable rather than crashing or stopping the polling loop.

#### Scenario: Tmux server unavailable results in empty index
- **WHEN** the tmux server is not running
- **AND WHEN** the shared registry contains fresh records
- **THEN** no agents appear in the discovered agent index
- **AND THEN** the discovery service continues polling

#### Scenario: Tmux server becomes available after startup
- **WHEN** the tmux server was not running during initial scan cycles
- **AND WHEN** the tmux server starts and agents have live tmux sessions
- **THEN** the discovery service picks up those agents on the next scan cycle


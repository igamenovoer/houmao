## MODIFIED Requirements

### Requirement: Shared agent registry uses a fixed per-user root with isolated live-agent directories
The system SHALL store shared agent registry state under the fixed per-user root `~/.houmao/registry`.

Implementation SHALL resolve that root as `.houmao/registry` beneath the current user's home directory, and SHALL obtain that home directory through `platformdirs`-aware path handling rather than a hardcoded Linux-specific home prefix.

When `AGENTSYS_GLOBAL_REGISTRY_DIR` is set, the system SHALL use that environment variable as the effective registry root instead of the home-relative default. The override SHALL support CI, tests, and similarly controlled environments.

Published live-agent directories SHALL live under `~/.houmao/registry/live_agents/<agent-id>/`, where `agent-id` is the authoritative globally unique agent id for that published agent.

That authoritative `agent_id` SHALL replace registry-specific `agent_key` as the registry's stable live-agent identity key.

When no explicit `agent_id` is supplied by the publishing runtime and no previously persisted `agent_id` exists for that same built or resumed agent, the initial `agent_id` SHALL be bootstrapped as the full lowercase `md5(canonical agent name).hexdigest()`.

When a previously persisted `agent_id` already exists for that same built or resumed agent, the publishing runtime SHALL reuse that persisted `agent_id` rather than recomputing it from the current canonical agent name.

Each published live agent SHALL own exactly one authoritative `record.json` file inside its directory.

Each published live-agent record SHALL persist both the canonical agent name and the authoritative `agent_id`.

The registry root SHALL remain a discovery-oriented locator layer. Mutable runtime session state, launcher-managed CAO home state, task-specific logs or outputs, and mailbox content MUST NOT be stored under the registry root as part of this capability.

The runtime directory associated with a published agent MAY live anywhere on the filesystem and SHALL NOT be required to live under `~/.houmao/registry`.

#### Scenario: Published agent uses a runtime directory outside the registry root
- **WHEN** a runtime-managed agent publishes shared-registry state for agent name `AGENTSYS-gpu`
- **AND WHEN** the authoritative `agent_id` for that publication is `deadbeef`
- **AND WHEN** that agent's runtime session root lives outside `~/.houmao/registry`
- **THEN** the shared registry stores only `live_agents/deadbeef/record.json` under `~/.houmao/registry`
- **AND THEN** the published runtime pointers continue to reference the external runtime-owned session directory

#### Scenario: Home-relative registry root is not derived from a hardcoded Linux path
- **WHEN** the system derives the effective filesystem path for `~/.houmao/registry`
- **THEN** it resolves the current user's home directory through `platformdirs`-aware path handling
- **AND THEN** it does not assume a hardcoded Linux home-directory prefix such as `/home/<user>`

#### Scenario: CI override redirects the registry root
- **WHEN** `AGENTSYS_GLOBAL_REGISTRY_DIR` is set to an absolute directory path
- **THEN** the system uses that path as the effective shared-registry root
- **AND THEN** it does not publish under the default home-relative `~/.houmao/registry` for that process

#### Scenario: Different agent ids do not share writable registry files
- **WHEN** two different agents publish records for two different authoritative `agent_id` values
- **THEN** each agent writes only inside its own `~/.houmao/registry/live_agents/<agent-id>/` directory
- **AND THEN** the registry does not require a shared writable `index.json` or shared SQLite file for publication

#### Scenario: Initial default agent id uses the full MD5 hex digest of the canonical agent name
- **WHEN** the system bootstraps the initial `agent_id` for canonical agent name `AGENTSYS-gpu`
- **AND WHEN** no explicit or previously persisted `agent_id` exists for that same built or resumed agent
- **THEN** it uses the full lowercase `md5("AGENTSYS-gpu").hexdigest()` value as the authoritative identity
- **AND THEN** it does not truncate that digest before path derivation

#### Scenario: Persisted agent id wins over later name-derived recomputation during publication
- **WHEN** a publishing runtime already has persisted agent metadata with `agent_id=abc123`
- **AND WHEN** that same agent is later republished under a canonical agent name that could otherwise produce a different bootstrap id
- **THEN** the registry publication reuses `agent_id=abc123`
- **AND THEN** it does not silently replace that authoritative identity by recomputing from the current canonical agent name

#### Scenario: Different names sharing one explicit agent id trigger a warning and one registry directory
- **WHEN** the shared registry already contains `live_agents/abc123/record.json` for canonical agent name `AGENTSYS-gpu`
- **AND WHEN** a later publication explicitly reuses `agent_id=abc123` with canonical agent name `AGENTSYS-editor`
- **THEN** the system emits a warning that different canonical names are sharing one authoritative `agent_id`
- **AND THEN** it continues to publish into `~/.houmao/registry/live_agents/abc123/record.json`

### Requirement: Shared-registry records persist authoritative agent identity rather than registry-specific agent keys
Each shared-registry `record.json` SHALL persist both the canonical agent name and the authoritative `agent_id`.

The registry record schema for this change SHALL replace the registry-specific `agent_key` field with authoritative `agent_id`.

The registry record SHALL continue to include the live terminal session metadata needed to locate the running session, but that terminal session name SHALL NOT be treated as the canonical agent name by contract.

#### Scenario: Shared-registry record persists both human-facing and authoritative identity fields
- **WHEN** the system publishes a live shared-registry record for one agent
- **THEN** that `record.json` persists both canonical `agent_name` and authoritative `agent_id`
- **AND THEN** consumers can answer both “what is this agent called?” and “which exact agent identity is up?” from the same record

#### Scenario: Shared-registry terminal session metadata is not the source of truth for agent identity
- **WHEN** a published live record includes terminal session name `houmao-session-abc123`
- **AND WHEN** that same record persists canonical agent name `AGENTSYS-gpu`
- **THEN** consumers treat `AGENTSYS-gpu` and the record's `agent_id` as the authoritative agent identity metadata
- **AND THEN** they do not assume `houmao-session-abc123` itself is the canonical agent name

### Requirement: Shared registry resolves live agents primarily by authoritative agent id
The system SHALL support direct resolution of a published live agent by authoritative `agent_id`.

When a caller resolves a live agent by canonical agent name instead of `agent_id`, the system SHALL consult persisted registry metadata rather than deriving the lookup path from canonical name alone.

When more than one fresh live registry record shares the same canonical agent name but carries different authoritative `agent_id` values, canonical-name lookup SHALL report ambiguity rather than silently choosing one record.

#### Scenario: Direct agent-id resolution returns the published record for that exact identity
- **WHEN** a caller resolves authoritative `agent_id=abc123`
- **AND WHEN** `live_agents/abc123/record.json` is valid and lease-fresh
- **THEN** the system returns the validated record for that exact authoritative identity
- **AND THEN** that result answers whether agent `abc123` is currently up

#### Scenario: Canonical-name lookup scans registry metadata rather than hashing name to path
- **WHEN** a caller resolves canonical agent name `AGENTSYS-gpu`
- **AND WHEN** exactly one fresh live registry record persists canonical agent name `AGENTSYS-gpu`
- **THEN** the system returns that one validated record
- **AND THEN** it does not require canonical-name lookup to derive the filesystem path by hashing the name directly

#### Scenario: Canonical-name lookup reports ambiguity when more than one live identity shares the same name
- **WHEN** a caller resolves canonical agent name `AGENTSYS-gpu`
- **AND WHEN** more than one fresh live registry record persists canonical agent name `AGENTSYS-gpu`
- **AND WHEN** those records carry different authoritative ids such as `abc123` and `def456`
- **THEN** the system reports canonical-name lookup as ambiguous
- **AND THEN** it requires the caller to disambiguate by `agent_id` or another explicit metadata surface

#### Scenario: Registry root is not repurposed as mutable CAO home storage
- **WHEN** the system starts a launcher-managed CAO server while also using the shared registry for live-agent discovery
- **THEN** the shared registry root continues to contain registry-owned discovery state only
- **AND THEN** launcher-managed CAO home state and runtime task artifacts are stored elsewhere

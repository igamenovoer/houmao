## MODIFIED Requirements

### Requirement: Shared agent registry uses a fixed per-user root with isolated live-agent directories
The system SHALL store shared agent registry state under the fixed per-user root `~/.houmao/registry`.

Implementation SHALL resolve that root as `.houmao/registry` beneath the current user's home directory, and SHALL obtain that home directory through `platformdirs`-aware path handling rather than a hardcoded Linux-specific home prefix.

When `AGENTSYS_GLOBAL_REGISTRY_DIR` is set, the system SHALL use that environment variable as the effective registry root instead of the home-relative default. The override SHALL support CI, tests, and similarly controlled environments.

Published live-agent directories SHALL live under `~/.houmao/registry/live_agents/<agent-key>/`, where `agent-key` is the full lowercase SHA-256 hex digest of the canonical globally unique published agent name rather than the raw name itself.

Each published live agent SHALL own exactly one authoritative `record.json` file inside its directory.

The registry root SHALL remain a discovery-oriented locator layer. Mutable runtime session state, launcher-managed CAO home state, task-specific logs or outputs, and mailbox content MUST NOT be stored under the registry root as part of this capability.

The runtime directory associated with a published agent MAY live anywhere on the filesystem and SHALL NOT be required to live under `~/.houmao/registry`.

#### Scenario: Published agent uses a runtime directory outside the registry root
- **WHEN** a runtime-managed agent publishes shared-registry state for agent name `AGENTSYS-gpu`
- **AND WHEN** that agent's runtime session root lives outside `~/.houmao/registry`
- **THEN** the shared registry stores only the hashed live-agent directory and `record.json` under `~/.houmao/registry/live_agents/`
- **AND THEN** the published runtime pointers continue to reference the external runtime-owned session directory

#### Scenario: Home-relative registry root is not derived from a hardcoded Linux path
- **WHEN** the system derives the effective filesystem path for `~/.houmao/registry`
- **THEN** it resolves the current user's home directory through `platformdirs`-aware path handling
- **AND THEN** it does not assume a hardcoded Linux home-directory prefix such as `/home/<user>`

#### Scenario: CI override redirects the registry root
- **WHEN** `AGENTSYS_GLOBAL_REGISTRY_DIR` is set to an absolute directory path
- **THEN** the system uses that path as the effective shared-registry root
- **AND THEN** it does not publish under the default home-relative `~/.houmao/registry` for that process

#### Scenario: Different agent names do not share writable registry files
- **WHEN** two different agents publish records for two different globally unique agent names
- **THEN** each agent writes only inside its own `~/.houmao/registry/live_agents/<agent-key>/` directory
- **AND THEN** the registry does not require a shared writable `index.json` or shared SQLite file for publication

#### Scenario: Canonical agent key uses the full SHA-256 hex digest
- **WHEN** the system derives `agent-key` for canonical agent name `AGENTSYS-gpu`
- **THEN** it uses the full lowercase `sha256("AGENTSYS-gpu").hexdigest()` value as the live-agent directory name
- **AND THEN** it does not truncate that digest before path derivation

#### Scenario: Registry root is not repurposed as mutable CAO home storage
- **WHEN** the system starts a launcher-managed CAO server while also using the shared registry for live-agent discovery
- **THEN** the shared registry root continues to contain registry-owned discovery state only
- **AND THEN** launcher-managed CAO home state and runtime task artifacts are stored elsewhere
